import django_tables2 as tables
from django.template.backends.utils import csrf_input
from django.urls import reverse
from django.utils.html import format_html
from .models import Row, Column


class DynamicTable(tables.Table):
    class Meta:
        model = Row
        attrs = {
            'class': 'table table-bordered table-hover',
            'thead': {
                'class': 'table-light'
            }
        }
        fields = ()  # Будем заполнять динамически

    def __init__(self, *args, table_obj=None, editable_rows=None, request=None, **kwargs):
        self.base_columns.clear()
        self.table_obj = table_obj
        self.request = request
        self.editable_rows = editable_rows
        if table_obj:
            for column in table_obj.columns.all():
                self._add_column(column)

            self.base_columns['delete'] = tables.Column(
                verbose_name='',
                orderable=False,
                empty_values=(),
                attrs={
                    'td': {'class': 'text-end',
                           'width': '50px'}
                }
            )
            self.base_columns['actions'] = tables.Column(
                empty_values=(),
                orderable=False,
                verbose_name='',
                attrs={
                    'td': {'class': 'text-end',
                           'width': '50px'}
                }
            )
        super().__init__(*args, **kwargs)

    def _add_column(self, column):
        col_name = f'col_{column.id}'
        accessor = f'cell_values.{column.id}'

        # Выбираем соответствующий тип столбца
        if column.data_type == Column.ColumnType.INTEGER:
            self.base_columns[col_name] = tables.Column(
                verbose_name=self.get_column_header(column),
                accessor=accessor,
                attrs={'td': {'class': 'text-end'}}
            )
        if column.data_type == Column.ColumnType.FLOAT:
            self.base_columns[col_name] = tables.Column(
                verbose_name=self.get_column_header(column),
                accessor=accessor,
                attrs={'td': {'class': 'text-end'}}
            )
        elif column.data_type == Column.ColumnType.BOOLEAN:
            self.base_columns[col_name] = tables.BooleanColumn(
                verbose_name=self.get_column_header(column),
                accessor=accessor,
                attrs={'td': {'class': 'text-center'}}
            )
        elif column.data_type == Column.ColumnType.DATE:
            self.base_columns[col_name] = tables.DateColumn(
                verbose_name=self.get_column_header(column),
                accessor=accessor,
            )
        else:  # TEXT по умолчанию
            self.base_columns[col_name] = tables.Column(
                verbose_name=self.get_column_header(column),
                accessor=accessor
            )

    def render_delete(self, record):
        if self.table_obj.owner == self.request.user:
            delete_url = reverse('delete_row',
                                 kwargs={'table_pk': self.table_obj.pk,
                                         'row_pk': record.id
                                         })
            return format_html(
                '<form method="post" action="{}" style="display:inline;">{}'
                '<button type="submit" '
                'class="btn btn-sm btn-danger" '
                'onclick="return confirm(\'Удалить строку?\');">'
                '×</button>'
                '</form>',
                delete_url,
                csrf_input(self.request)
            )

    def render_actions(self, record):
        if record.id in self.editable_rows:
            return format_html(
                '<button class="btn btn-sm btn-outline-primary edit-row-btn" '
                'data-row-id="{}" data-table-id="{}">✏️</button>',
                record.id,
                self.table_obj.pk
            )
        return ''

    def get_column_header(self, column):
        if self.table_obj.owner == self.request.user:
            delete_url = reverse('delete_column',
                                 kwargs={'table_pk': self.table_obj.pk,
                                         'column_pk': column.id
                                         })
            return format_html(
                '{} <form method="post" action="{}" style="display:inline;">{}'
                '<button type="submit" '
                'class="btn btn-sm btn-danger ms-1" '
                'onclick="return confirm(\'Удалить столбец?\');">'
                '×</button>'
                '</form>',
                column.name,
                delete_url,
                csrf_input(self.request)
            )
        return column.name
