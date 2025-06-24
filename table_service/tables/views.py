from datetime import date

from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string

from .models import Table, Column, Row, Cell, RowPermission
from .forms import TableForm, ColumnForm, ShareTableForm, RowEditForm
from django.contrib import messages
from django_tables2 import RequestConfig
from .tables import DynamicTable
from django.views.decorators.http import require_POST


# Проверка прав на редактирование конкретной строки
def has_row_edit_permission(user, row):
    return (row.table.owner == user or
            RowPermission.objects.filter(row=row, user=user, can_edit=True).exists())


@login_required
def table_list(request):
    tables = Table.objects.filter(owner=request.user)
    return render(request, 'tables/table_list.html', {'tables': tables})


@login_required
def create_table(request):
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            table = form.save(commit=False)
            table.owner = request.user
            table.save()
            return redirect('table_detail', pk=table.pk)
    else:
        form = TableForm()
    return render(request, 'tables/create_table.html', {'form': form})


@login_required
def delete_table(request, pk):
    table = get_object_or_404(Table, pk=pk)

    # Проверка прав
    if table.owner != request.user:
        return HttpResponseForbidden("Вы не можете удалять таблицы")

    table.delete()

    messages.success(request, f'Таблица "{table.title}" успешно удалена')
    return redirect('table_list')


@login_required
def add_column(request, pk):
    table = get_object_or_404(Table, pk=pk)

    # Проверка прав (только владелец может добавлять колонки)
    if table.owner != request.user:
        return HttpResponseForbidden("Вы не можете добавлять колонки в эту таблицу")

    if request.method == 'POST':
        form = ColumnForm(request.POST)
        if form.is_valid():
            column = form.save(commit=False)
            column.table = table
            column.order = table.columns.count()
            column.save()
            messages.success(request, f'Колонка "{column.name}" успешно добавлена')
            return redirect('table_detail', pk=table.pk)
    else:
        form = ColumnForm()
    return render(request, 'tables/add_column/add_column.html', {'form': form, 'table': table})


@login_required
def add_row(request, pk):
    table = get_object_or_404(Table, pk=pk)

    # Проверка прав
    if table.owner != request.user:
        return HttpResponseForbidden("Вы не можете добавлять строки в эту таблицу")

    # Создаем новую строку
    row = Row.objects.create(
        table=table,
        order=table.rows.count()  # Порядковый номер новой строки
    )

    # Создаем пустые ячейки для всех колонок
    for column in table.columns.all():
        defaults = {
            'text_value': None,
            'integer_value': None,
            'float_value': None,
            'boolean_value': None,
            'date_value': None
        }

        # Устанавливаем пустое значение в зависимости от типа колонки
        if column.data_type == Column.ColumnType.INTEGER:
            defaults['integer_value'] = 0
        elif column.data_type == Column.ColumnType.FLOAT:
            defaults['float_value'] = 0.0
        elif column.data_type == Column.ColumnType.BOOLEAN:
            defaults['boolean_value'] = False
        elif column.data_type == Column.ColumnType.DATE:
            defaults['date_value'] = date.today()
        else:  # TEXT
            defaults['text_value'] = ''

        Cell.objects.create(
            row=row,
            column=column,
            **defaults
        )

    messages.success(request, 'Новая строка успешно добавлена')
    return redirect('table_detail', pk=table.pk)


@login_required
def delete_column(request, table_pk, column_pk):
    table = get_object_or_404(Table, pk=table_pk)
    column = get_object_or_404(Column, pk=column_pk, table=table)

    # Проверка прав
    if table.owner != request.user:
        return HttpResponseForbidden("Вы не можете удалять колонки из этой таблицы")

    Cell.objects.filter(column=column).delete()
    column.delete()

    messages.success(request, f'Колонка "{column.name}" успешно удалена')
    return redirect('table_detail', pk=table.pk)


@login_required
def delete_row(request, table_pk, row_pk):
    table = get_object_or_404(Table, pk=table_pk)
    row = get_object_or_404(Row, pk=row_pk, table=table)

    # Проверка прав
    if table.owner != request.user:
        return HttpResponseForbidden("Вы не можете удалять строки из этой таблицы")

    row.delete()
    messages.success(request, 'Строка успешно удалена')
    return redirect('table_detail', pk=table.pk)


@login_required
def edit_row(request, table_pk, row_pk):
    table = get_object_or_404(Table, pk=table_pk)
    row = get_object_or_404(Row, pk=row_pk, table=table)
    if not has_row_edit_permission(request.user, row):
        return JsonResponse({'status': 'error', 'message': 'Нет прав на редактирование'}, status=403)

    if request.method == 'POST':
        form = RowEditForm(request.POST, row=row)
        if form.is_valid():
            for column in table.columns.all():
                field_name = f'col_{column.id}'
                value = form.cleaned_data[field_name]

                Cell.objects.update_or_create(
                    row=row,
                    column=column,
                    defaults={'value': value}
                )
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    # GET запрос - возвращаем форму
    form = RowEditForm(row=row)
    html = render_to_string('tables/row_edit_form/row_edit_form.html', {
        'form': form,
        'table': table,
        'row': row
    }, request=request)
    return JsonResponse({'status': 'success', 'html': html})


@login_required
def table_detail(request, pk):
    table_obj = get_object_or_404(Table, pk=pk)
    # Проверка прав доступа
    if table_obj.owner != request.user and not table_obj.rowpermission_set.filter(user=request.user).exists():
        return HttpResponseForbidden("You don't have permission to access this table.")

    if table_obj.owner == request.user:
        editable_rows = [row.id for row in table_obj.rows.all()]
    else:
        editable_rows = [perm.row.id for perm in RowPermission.objects.filter(
            user=request.user,
            can_edit=True,
            row__in=table_obj.rows.all()
        )]

    queryset = table_obj.rows.all().prefetch_related('cells', 'cells__column')
    table = DynamicTable(data=queryset, table_obj=table_obj, editable_rows=editable_rows, request=request)
    RequestConfig(request).configure(table)
    return render(request, 'tables/table_detail.html', {
        'table_obj': table_obj,
        'table': table,
    })
