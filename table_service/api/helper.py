import io
from datetime import date, datetime
from pickle import FALSE

from django.db import transaction
from django.db.models.aggregates import Max
from django.utils.safestring import mark_safe
from openpyxl.styles import Font
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import BrowsableAPIRenderer
from asgiref.sync import sync_to_async
from rest_framework.response import Response

from api.utils import send_table_create
from tables.models import TablePermission, TableFilialPermission, Profile, RowPermission, RowFilialPermission, Table, \
    Row, Cell, Column, CellLock, User

import openpyxl
from io import BytesIO

def get_table_ids_permissions(user):
    #TODO УДАЛИТЬ НАХУЙ CAN_VIEW
    permissions_user = set(TablePermission.objects.filter(user=user).values_list('table__id', flat=True))
    filial_id = (Profile.objects
                 .filter(user=user)
                 .select_related('employee')
                 .values_list('employee__id_filial', flat=True)
                 .first())
    permissions_filial = set(
        TableFilialPermission.objects.filter(filial__id=filial_id).values_list('table__id', flat=True))
    all_permissions = permissions_user | permissions_filial
    return all_permissions

def get_row_ids_permissions(user):
    permissions_user = set(RowPermission.objects.filter(user=user).values_list('row_id', flat=True))
    filial_id = (Profile.objects
                 .filter(user=user)
                 .select_related('employee')
                 .values_list('employee__id_filial', flat=True)
                 .first())
    permissions_filial = set(RowFilialPermission.objects.filter(filial__id=filial_id).values_list('row_id', flat=True))
    all_permissions = permissions_user | permissions_filial
    return all_permissions

class FileUploadBrowsableRenderer(BrowsableAPIRenderer):
    def get_rendered_html_form(self, data, view, method, request):
        if method == 'POST':
            html = '''
            <div class="form-wrapper">
                <form enctype="multipart/form-data" method="post">
                    <div class="form-group">
                        <label for="file">Выберите файл:</label>
                        <input type="file" id="file" name="file" required>
                    </div>
                    <input type='text' id='table_name' name="table_name" required/>
                    <button type="submit" class="btn btn-primary">Загрузить</button>
                </form>
            </div>
            <style>
                .form-wrapper { margin: 20px; }
                .form-group { margin-bottom: 15px; }
                input[type="file"] { display: block; margin-top: 5px; }
                .btn { padding: 8px 15px; background: #007bff; color: white; border: none; border-radius: 4px; }
            </style>
            '''
            return mark_safe(html)  # Помечаем HTML как безопасный
        return super().get_rendered_html_form(data, view, method, request)

def determine_column_types(rows_sample):
    """Определяем тип данных для каждой колонки на основе первых 10 строк"""
    if not rows_sample:
        return []

    # sample_size = min(10, len(rows_sample))
    column_types = []

    for col_idx in range(len(rows_sample[0])):
        # values = [row[col_idx] for row in rows_sample[:sample_size] if row[col_idx] is not None]
        col_type = Column.ColumnType.TEXT
        # if not values:
        #     column_types.append(Column.ColumnType.TEXT)
        #     continue
        #
        # # Проверяем типы данных
        # if all(isinstance(v, bool) for v in values):
        #     col_type = Column.ColumnType.BOOLEAN
        # elif all(isinstance(v, int) for v in values) and not any(isinstance(v, bool) for v in values):
        #     col_type = Column.ColumnType.INTEGER
        # elif all(isinstance(v, (int, float)) for v in values) and not any(isinstance(v, bool) for v in values):
        #     col_type = Column.ColumnType.FLOAT
        # elif all(isinstance(v, date) for v in values):
        #     col_type = Column.ColumnType.DATE
        # else:
        #     col_type = Column.ColumnType.TEXT

        column_types.append(col_type)

    return column_types

def prepare_cell(row, column, value):
    """Создает объект Cell с правильным полем в зависимости от типа колонки"""
    if value is None:
        return None

    cell = Cell(row=row, column=column)

    if column.data_type == Column.ColumnType.TEXT:
        cell.text_value = str(value)
    elif column.data_type == Column.ColumnType.INTEGER:
        cell.integer_value = int(value) if value is not None else None
    elif column.data_type == Column.ColumnType.FLOAT:
        cell.float_value = float(value) if value is not None else None
    elif column.data_type == Column.ColumnType.BOOLEAN:
        cell.boolean_value = bool(value)
    elif column.data_type == Column.ColumnType.DATE:
        cell.date_value = value if isinstance(value, date) else None

    return cell



def import_table(file, name, user):
    try:
        with transaction.atomic():  # Всё выполняется в одной транзакции
            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active

            # Создаём таблицу
            table = Table.objects.create(title=name, owner=user)

            TablePermission.objects.create(
                table=table,
                user=user,
                can_view=True,
            )

            # Читаем данные из Excel
            rows_data = list(ws.iter_rows(values_only=True))
            if not rows_data:
                return table

            # Определяем заголовки и типы колонок
            headers = [str(header).strip() for header in rows_data[0]]
            column_types = determine_column_types(rows_data[1:])

            # Создаём колонки
            columns = []
            for order, (header, data_type) in enumerate(zip(headers, column_types), start=1):
                column = Column(
                    table=table,
                    name=header,
                    order=order,
                    data_type=data_type
                )
                columns.append(column)

            Column.objects.bulk_create(columns)

            # Подготавливаем строки
            rows = []
            for row_order, _ in enumerate(rows_data[1:], start=1):
                row = Row(
                    table=table,
                    order=row_order,
                    created_by=user
                )
                rows.append(row)

            Row.objects.bulk_create(rows)

            # Получаем созданные строки (с актуальными ID)
            created_rows = list(Row.objects.filter(table=table).order_by('order'))

            # Подготавливаем ячейки
            cells = []
            row_permissions = []
            for row_obj, row_values in zip(created_rows, rows_data[1:]):
                row_permissions.append(
                    RowPermission(
                        row = row_obj,
                        user = user,
                        can_edit=True,
                        can_delete=True
                    )
                )
                for column, value in zip(columns, row_values):
                    cell = prepare_cell(row_obj, column, value)
                    if cell:
                        cells.append(cell)

            RowPermission.objects.bulk_create(row_permissions)
            Cell.objects.bulk_create(cells)

            return table

    except Exception as e:
        # Логируем ошибку (можно использовать logging.exception(e))
        raise  #


def import_to_existing_table(file, table_id, user):
    try:
        with transaction.atomic():
            # Получаем таблицу и проверяем права
            table = Table.objects.get(id=table_id)
            if not table.permissions.filter(user=user, can_view=True).exists():
                raise PermissionDenied("У вас нет прав на редактирование этой таблицы")

            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active
            rows_data = list(ws.iter_rows(values_only=True))

            if not rows_data:
                return table

            # Получаем существующие колонки
            existing_columns = list(table.columns.all().order_by('order'))
            if len(rows_data[0]) != len(existing_columns):
                raise ValueError("Количество колонок в файле не совпадает с таблицей")

            # Определяем порядковый номер для новых строк
            last_order = Row.objects.filter(table=table).aggregate(Max('order'))['order__max'] or 0

            # Подготавливаем новые строки
            new_rows = []
            for row_order, row_values in enumerate(rows_data[1:], start=last_order + 1):
                row = Row(
                    table=table,
                    order=row_order,
                    created_by=user
                )
                new_rows.append(row)

            Row.objects.bulk_create(new_rows)

            # Получаем ID созданных строк
            created_rows = list(Row.objects.filter(table=table, order__gt=last_order).order_by('order'))

            # Подготавливаем ячейки и права
            cells = []
            row_permissions = []

            for row_obj, row_values in zip(created_rows, rows_data[1:]):
                row_permissions.append(
                    RowPermission(
                        row=row_obj,
                        user=user,
                        can_edit=True,
                        can_delete=True
                    )
                )

                for column, value in zip(existing_columns, row_values):
                    cell = prepare_cell(row_obj, column, value)
                    if cell:
                        cells.append(cell)

            # Массовое создание
            RowPermission.objects.bulk_create(row_permissions)
            Cell.objects.bulk_create(cells)
            send_table_create(table)
            return table
    except Exception as e:
    # Логируем ошибку (можно использовать logging.exception(e))
        raise  #


@sync_to_async(thread_sensitive=False)
def get_cell_by_id(cell_id):
    cell = get_object_or_404(Cell, pk=cell_id)
    return cell

@sync_to_async(thread_sensitive=False)
def create_cell_lock(cell,user):
    cell_lock = CellLock.objects.create(cell=cell, user=user)
    return cell_lock

@sync_to_async(thread_sensitive=False)
def get_cell_lock_by_cell(cell):
    cell_lock = CellLock.objects.get(cell=cell)
    return cell_lock

@sync_to_async(thread_sensitive=False)
def remove_cell_lock(cell_lock):
    cell_ids = Cell.objects.all().values_list('cell_id', flat=True)
    cell_locks = CellLock.objects.filter(cell_ids__in=cell_ids).values_list('cell_id','user_id', flat=True)
    return cell_locks

@sync_to_async(thread_sensitive=False)
def get_user(user_id):
    user = User.objects.get(id=user_id)
    return user

def export_to_xlsx(self, table_obj):
    # Создаем новую книгу Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = table_obj.title[:31]  # Ограничение длины названия листа в Excel

    # Получаем данные таблицы
    columns = table_obj.columns.all().order_by('order')
    rows = table_obj.rows.all().order_by('order')

    # Заголовки столбцов
    headers = [column.name for column in columns]
    ws.append(headers)

    # Стиль для заголовков
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Данные ячеек
    for row in rows:
        row_data = []
        for column in columns:
            cell = row.cells.filter(column=column).first()
            if cell:
                # Получаем значение в зависимости от типа данных
                if column.data_type == Column.ColumnType.TEXT:
                    row_data.append(cell.text_value)
                elif column.data_type == Column.ColumnType.INTEGER:
                    row_data.append(cell.integer_value)
                elif column.data_type == Column.ColumnType.FLOAT:
                    row_data.append(cell.float_value)
                elif column.data_type == Column.ColumnType.BOOLEAN:
                    row_data.append(cell.boolean_value)
                elif column.data_type == Column.ColumnType.DATE:
                    row_data.append(cell.date_value.strftime('%Y-%m-%d') if cell.date_value else None)
            else:
                row_data.append(None)
        ws.append(row_data)

    # Сохраняем в буфер
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Формируем имя файла
    filename = f"{table_obj.title}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return Response(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )




