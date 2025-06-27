from datetime import date

from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string

from .models import Table, Column, Row, Cell, RowPermission
from .forms import TableForm, ColumnForm, RowEditForm, AddRowForm
from django.contrib import messages
from django_tables2 import RequestConfig
from .tables import DynamicTable
from django.views.decorators.http import require_POST, require_http_methods


def save_row_data(table, row, form):
    """Сохраняет данные строки из формы"""
    for column in table.columns.all():
        field_name = f'col_{column.id}'
        value = form.cleaned_data[field_name]

        Cell.objects.update_or_create(
            row=row,
            column=column,
            defaults={'value': value}
        )


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
def manage_row_permissions(request, table_pk, row_pk):
    table = get_object_or_404(Table, pk=table_pk)
    row = get_object_or_404(Row, pk=row_pk, table=table)

    if not row.has_manage_permission(request.user):
        return HttpResponseForbidden("Только владелец таблицы может управлять правами")

    if request.method == 'POST':
        if 'update_submit' in request.POST:
            # Обработка существующих пользователей
            for perm in row.permissions.all():
                user_id = str(perm.user.id)
                perm.can_edit = f'can_edit_{user_id}' in request.POST
                perm.can_delete = f'can_delete_{user_id}' in request.POST
                perm.save()

        # Обработка новых пользователей
        if 'add_users_submit' in request.POST:
            new_users = request.POST.getlist('new_users')
            if new_users:
                can_edit = 'new_can_edit' in request.POST
                can_delete = 'new_can_delete' in request.POST
                for user_id in new_users:
                    user = get_object_or_404(User, pk=user_id)
                    RowPermission.objects.update_or_create(
                        row=row,
                        user=user,
                        defaults={
                            'can_edit': can_edit,
                            'can_delete': can_delete,
                        }
                    )
        messages.success(request, 'Обновление прав успешно!')
        return redirect('manage_row_permissions', table_pk=table.pk, row_pk=row.pk)

    # Получаем текущие разрешения для строки
    permissions = row.permissions.filter()
    all_users = User.objects.exclude(pk=table.owner.pk)

    return render(request, 'tables/manage_permissions.html', {
        'table': table,
        'row': row,
        'permissions': permissions,
        'all_users': all_users
    })


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
    if not row.has_delete_permission(request.user):
        return JsonResponse({'status': 'error', 'message': 'Нет прав на удаление'}, status=403)

    row.delete()
    messages.success(request, 'Строка успешно удалена')
    return redirect('table_detail', pk=table.pk)


@login_required
def edit_row(request, table_pk, row_pk):
    table = get_object_or_404(Table, pk=table_pk)
    row = get_object_or_404(Row, pk=row_pk, table=table)
    if not row.has_edit_permission(request.user):
        return JsonResponse({'status': 'error', 'message': 'Нет прав на редактирование'}, status=403)

    if request.method == 'POST':
        form = RowEditForm(request.POST, row=row)
        if form.is_valid():
            save_row_data(table, row, form)
            messages.success(request, 'Строка успешно отредактирована!')
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
def add_row(request, pk):
    table = get_object_or_404(Table, pk=pk)

    # Проверка прав


    if request.method == 'POST':
        form = AddRowForm(request.POST, table=table)
        if form.is_valid():

            # Создаем новую строку
            row = Row.objects.create(
                table=table,
                order=table.rows.count(),  # Порядковый номер новой строки
                created_by=request.user
            )

            RowPermission.objects.create(
                row=row,
                user=request.user,
                can_edit=True,
                can_delete=True,
            )

            # Заполняем ячейки данными из формы
            for column in table.columns.all():
                field_name = f'col_{column.id}'
                value = form.cleaned_data.get(field_name)

                Cell.objects.create(
                    row=row,
                    column=column,
                    value=value
                )

            messages.success(request, 'Новая строка успешно добавлена')
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    # GET запрос - возвращаем форму
    form = AddRowForm(table=table)
    html = render_to_string('tables/add_row/add_row.html', {
        'form': form,
        'table': table  # Передаем сам объект таблицы
    }, request=request)
    return JsonResponse({'status': 'success', 'html': html})


@login_required
def shared_tables_list(request):
    # Получаем все таблицы, к которым у пользователя есть доступ
    shared_tables = Table.get_shared_tables(request.user)

    # Добавляем информацию о правах для каждой таблицы
    tables_with_access = []
    for table in shared_tables:
        if table.owner == request.user:
            is_owner = True
        else:
            is_owner = False

        can_edit = is_owner or RowPermission.objects.filter(
            row__table=table,
            user=request.user,
            can_edit=True
        ).exists()
        can_delete = is_owner or RowPermission.objects.filter(
            row__table=table,
            user=request.user,
            can_delete=True
        ).exists()

        tables_with_access.append({
            'table': table,
            'is_owner': is_owner,
            'can_edit': can_edit,
            'can_delete': can_delete,
            'shared_by': table.owner.username
        })

    return render(request, 'tables/shared_tables_list.html', {
        'tables': tables_with_access
    })


@login_required
@require_POST
def revoke_access(request, pk):
    table = get_object_or_404(Table, pk=pk)
    if table.owner != request.user:
        return HttpResponseForbidden("Только владелец таблицы может отозвать доступ")

    user = get_object_or_404(User, pk=request.POST.get('user_id'))
    table.remove_user_access(user)
    messages.success(request, f"Доступ для {user.email} отозван!")
    return redirect('share_table', pk=table.pk)


@login_required
def table_detail(request, pk):
    table_obj = get_object_or_404(Table, pk=pk)
    # Проверка прав доступа
    if table_obj.owner != request.user:
        return HttpResponseForbidden("You don't have permission to access this table.")

    queryset = table_obj.rows.all().prefetch_related('cells', 'cells__column')
    # Добавляем аннотации для каждого столбца
    queryset = sort_func(queryset, table_obj)

    table = DynamicTable(data=queryset, table_obj=table_obj, request=request)
    RequestConfig(request).configure(table)
    return render(request, 'tables/table_detail.html', {
        'table_obj': table_obj,
        'table': table,
    })


@login_required()
def shared_table_view(request, share_token):
    table = get_object_or_404(Table, share_token=share_token)

    # Получаем строки, которые пользователь может видеть
    rows = Row.get_visible_rows(request.user, table)
    queryset = sort_func(rows, table)
    table_view = DynamicTable(data=queryset, table_obj=table, request=request)
    RequestConfig(request).configure(table_view)

    return render(request, 'tables/shared_table.html', {
        'table_obj': table,
        'table': table_view,
        'is_owner': table.owner == request.user,
    })


def sort_func(queryset, table_obj):
    for column in table_obj.columns.all():
        queryset = Row.annotate_for_sorting(queryset, column.id, column.data_type)
    return queryset
