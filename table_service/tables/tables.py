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

    def __init__(self, *args, table_obj=None, request=None, **kwargs):
        self.base_columns.clear()
        self.table_obj = table_obj
        self.request = request
        if table_obj:
            for column in table_obj.columns.all():
                self._add_column(column)

            self.base_columns['actions'] = tables.Column(
                empty_values=(),
                orderable=False,
                verbose_name='',
                attrs={
                    'td': {'class': 'text-end',
                           'width': '125px'}
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
                attrs={'td': {'class': 'text-end'}},
                order_by=f'sort_value_{column.id}'
            )
        if column.data_type == Column.ColumnType.FLOAT:
            self.base_columns[col_name] = tables.Column(
                verbose_name=self.get_column_header(column),
                accessor=accessor,
                attrs={'td': {'class': 'text-end'}},
                order_by=f'sort_value_{column.id}'
            )
        elif column.data_type == Column.ColumnType.BOOLEAN:
            self.base_columns[col_name] = tables.BooleanColumn(
                verbose_name=self.get_column_header(column),
                accessor=accessor,
                attrs={'td': {'class': 'text-center'}},
                order_by=f'sort_value_{column.id}'
            )
        elif column.data_type == Column.ColumnType.DATE:
            self.base_columns[col_name] = tables.DateColumn(
                verbose_name=self.get_column_header(column),
                accessor=accessor,
                order_by=f'sort_value_{column.id}'
            )
        else:  # TEXT по умолчанию
            self.base_columns[col_name] = tables.Column(
                verbose_name=self.get_column_header(column),
                accessor=accessor,
                order_by=f'sort_value_{column.id}'
            )

    def render_delete(self, record):
        if (self.table_obj.owner == self.request.user) or (record.has_delete_permission(self.request.user)):
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
        return ''

    def render_actions(self, record):
        edit = format_html('')
        if record.has_edit_permission(self.request.user):
            edit += format_html(
                '<a class="btn btn-sm btn-outline-primary edit-row-btn" '
                'title="Редактировать строку"'
                'data-row-id="{}" data-table-id="{}"><i class="bi bi-pen"></i>'
                '</a>',
                record.id,
                self.table_obj.pk
            )
        if record.has_delete_permission(self.request.user):
            delete_url = reverse('delete_row',
                                 kwargs={'table_pk': self.table_obj.pk,
                                         'row_pk': record.id
                                         })
            edit += format_html(
                '<form method="post" action="{}" style="display:inline;">{}'
                '<button type="submit" '
                'class="btn btn-sm btn-danger" '
                'onclick="return confirm(\'Удалить строку?\');">'
                '×</button>'
                '</form>',
                delete_url,
                csrf_input(self.request)
            )

        if record.has_manage_permission(self.request.user):
            edit += format_html(
                '<a href="{}" class="btn btn-sm btn-outline-secondary" title="Настроить разрешения">'
                '<i class="bi bi-people-fill"></i></a>',
                reverse('manage_row_permissions', kwargs={
                    'table_pk': self.table_obj.pk,
                    'row_pk': record.id
                })
            )
        return edit

    def get_column_header(self, column):
        if self.table_obj.owner == self.request.user:
            delete_url = reverse('delete_column',
                                 kwargs={'table_pk': self.table_obj.pk,
                                         'column_pk': column.id
                                         })
            column_name = format_html(
                '<div class="d-flex justify-content-between align-items-center">'
                '<div>{}</div>'
                '<div>'
                '<form method="post" action="{}" style="display:inline;">{}'
                '<button type="submit" '
                'class="btn btn-sm btn-danger ms-3" '
                'onclick="return confirm(\'Удалить столбец?\');">'
                '<i class="bi bi-x-lg"></i></button>'
                '</form>'
                '</div>'
                '</div>',
                column.name,
                delete_url,
                csrf_input(self.request)
            )
        else:
            column_name = format_html(
                '<div>{}</div>',
                column.name
            )
        # Добавляем иконки сортировки
        sort_param = self.request.GET.get('sort', '')
        current_sort = f"col_{column.id}"

        if sort_param.lstrip('-') == current_sort:
            if sort_param.startswith('-'):
                # Сортировка по убыванию
                return format_html(
                    '{} <i class="bi bi-sort-down-alt text-primary"></i>',
                    column_name
                )
            else:
                # Сортировка по возрастанию
                return format_html(
                    '{} <i class="bi bi-sort-up text-primary"></i>',
                    column_name
                )
        else:
            # Нет сортировки
            return format_html(
                '{} <i class="bi bi-filter text-muted"></i>',
                column_name
            )
