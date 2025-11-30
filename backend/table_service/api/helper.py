from datetime import date, datetime
from io import BytesIO
import re

import pandas as pd
from django.http import HttpResponse
from django.db import transaction
from django.db.models.aggregates import Max
from django.utils.safestring import mark_safe
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import BrowsableAPIRenderer
from asgiref.sync import sync_to_async

from api.formulas import calculate_formula
from api.utils import send_table_create, send_cell_lock_remove, send_cell_update, send_to_demon
from tables.models import TablePermission, TableFilialPermission, Profile, RowPermission, RowFilialPermission, Table, \
    Row, Cell, Column, CellLock, User, ColumnFilialPermission, ColumnPermission, CellEditLog

from django.db.models.signals import post_save
from django.dispatch import receiver

from tables.models import Cell

import openpyxl

from api.serializers import update_auto_column


def get_table_ids_permissions(user):
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
    permissions_user = set(RowPermission.objects.filter(user=user.id).values_list('row', flat=True))
    filial_id = (Profile.objects
                 .filter(user=user)
                 .select_related('employee')
                 .values_list('employee__id_filial', flat=True)
                 .first())
    permissions_filial = set(RowFilialPermission.objects.filter(filial=filial_id).values_list('row', flat=True))
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

def prepare_cell(row, column, table, value):
    #if value is None:
    #    return None

    cell = Cell(row=row.id, column=column.id,table_id=table.id, value=value)

    return cell


def import_table(file, name, user):
    try:
        with transaction.atomic():
            wb = openpyxl.load_workbook(file, data_only=True)
            ws = wb.active

            table = Table.objects.create(title=name, owner=user)

            TablePermission.objects.create(
                table=table,
                user=user,
                can_view=True,
            )

            rows_data = list(ws.iter_rows(values_only=True))
            if not rows_data:
                return table

            headers = [str(header).strip() for header in rows_data[0]]
            column_types = determine_column_types(rows_data[1:])


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

            columns_permissions = []
            for column in columns:
                column_permission = ColumnPermission(column=column, user=user)
                columns_permissions.append(column_permission)

            ColumnPermission.objects.abulk_create(columns_permissions)


            rows = []
            for row_order, _ in enumerate(rows_data[1:], start=1):
                row = Row(
                    table=table,
                    order=row_order,
                    created_by=user
                )
                rows.append(row)
            Row.objects.bulk_create(rows)

            created_rows = sorted(rows, key=lambda obj: obj.order)


            cells = []
            row_permissions = []
            for row_obj, row_values in zip(created_rows, rows_data[1:]):
                row_permissions.append(
                    RowPermission(
                        row = row_obj.id,
                        user = user.id,
                        table = table.id,
                        can_edit=True,
                        can_delete=True
                    )
                )
                for column, value in zip(columns, row_values):
                    cell = prepare_cell(row_obj, column,table, value)
                    if cell:
                        cells.append(cell)
            Cell.objects.bulk_create(cells)
            RowPermission.objects.bulk_create(row_permissions)

            # Определение типа колонок
            date_pattern = [r'\d{1,2}\.\d{1,2}\.\d{4}', r'\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}']
            for column in columns:
                cells_by_column = [cell for cell in cells if cell.column == column.id]
                has_float = False
                has_date = False
                for cell in cells_by_column:
                    if cell.value is None:
                        continue
                    clean_value = str(cell.value).strip()
                    if clean_value == "":
                        continue
                    try:
                        float(clean_value)
                        has_float = True
                        continue
                    except ValueError:
                        pass
                    for pattern in date_pattern:
                        if re.fullmatch(pattern, clean_value):
                            has_date = True
                            break
                    else:
                        continue
                if has_float:
                    column.data_type = 'float'
                if has_date:
                    column.data_type = 'date'
                else:
                    column.data_type = 'text'
                column.save()

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
                        row=row_obj.id,
                        user=user.id,
                        can_edit=True,
                        can_delete=True,
                        table=table.id
                    )
                )

                for column, value in zip(existing_columns, row_values):
                    cell = prepare_cell(row_obj, column,table, value)
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
def update_cell_by_id(cell_id, value, user_id):
    cell = get_object_or_404(Cell, pk=cell_id)

    # Логируем изменения
    if cell.value != value and user_id is not None:
        cell_edit_log_record = CellEditLog(cell_id=cell_id, user_id=user_id, old_value=cell.value, new_value=value, row_id=cell.row)
        cell_edit_log_record.save()
    # -----

    cell.value = value
    cell.formula_value = ''
    cell.save()

    if cell.value is not None:
        v = str(cell.value)
        if len(v) > 0:
            if v[0] == '=':
                calculate_formula(cell)

    send_cell_update(cell)
    recalculate_formulas(cell.table_id)
    cells = update_auto_column(cell.table_id)
    for cell in cells:
        send_cell_update(cell)
    return cell

def recalculate_formulas(table_id):
    cells_with_formulas = Cell.objects.filter(table_id=table_id, value__istartswith="=")
    for cell in cells_with_formulas:
        calculate_formula(cell)
        send_cell_update(cell)



@sync_to_async(thread_sensitive=False)
def create_cell_lock(cell,user):
    CellLock.objects.filter(user=user).delete()
    if CellLock.objects.filter(cell=cell, user=user).count() > 0:
        return CellLock.objects.filter(cell=cell, user=user)[0]
    cell_lock = CellLock.objects.create(cell=cell, user=user)

    return cell_lock

@sync_to_async(thread_sensitive=False)
def get_cell_lock_by_cell(cell):
    try:
        cell_lock = CellLock.objects.get(cell=cell)
        return cell_lock
    except:
        return None

@sync_to_async(thread_sensitive=False)
def remove_cell_lock(cell_lock):
    cell_lock.delete()
    cell_ids = Cell.objects.all().values_list('id', flat=True)
    cell_locks = CellLock.objects.filter(cell_id__in=cell_ids)
    result = [{'cell_id':lock.cell_id,'user_id':lock.user_id} for lock in cell_locks]
    return result

@sync_to_async(thread_sensitive=False)
def get_user(user_id):
    user = User.objects.get(id=user_id)
    return user


def export_table(request, table_id, format_type):
    table = get_object_or_404(Table, pk=table_id)

    columns = table.columns.all().order_by('order')
    rows = table.rows.all().order_by('order')

    data = {col.name: [] for col in columns}
    for row in rows:
        cells_dict = {}
        for cell in Cell.objects.filter(row=row.id):
            cells_dict[cell.column] = cell
        for col in columns:
            cell = cells_dict.get(col.id)
            value = cell.value
            data[col.name].append(value)
    df = pd.DataFrame(data)
    filename = 'unknown'
    if format_type == 'csv':
        response = HttpResponse(df.to_csv(index=False), content_type='text/csv')
        filename = f"{table.title}.csv"

    elif format_type == 'xls':
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='xlwt')
        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.ms-excel')
        filename = f"{table.title}.xls"

    elif format_type == 'xlsx':
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        response = HttpResponse(buffer.getvalue(),
                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"{table.title}.xlsx"

    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@sync_to_async(thread_sensitive=False)
def reorder_columns(table_id, old_index, new_index):
    table = Table.objects.get(id=table_id)
    column_a = Column.objects.get(table=table, order=old_index)
    column_b = Column.objects.get(table=table, order=new_index)
    column_a.order = new_index
    column_b.order = old_index
    column_a.save()
    column_b.save()

@sync_to_async(thread_sensitive=False)
def send_to_demon_proxy(username, path):
    send_to_demon(username, path)

@receiver(post_save, sender=Cell)
def notify_listeners(sender, instance, created, **kwargs):
    if instance:
        pass
        #send_cell_update(instance)
