import datetime

from django.db import transaction
from django.db.models import F, Value, TextField, Subquery, OuterRef
from django.db.models.functions import Concat
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string

from .models import Table, Column, Row, Cell, RowPermission, Filial, Employee, RowFilialPermission, TablePermission, TableFilialPermission
from .forms import TableForm, ColumnForm, RowEditForm, AddRowForm
from .service import unlock_row, lock_row
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
            table.created_at = datetime.datetime.now()
            table.save()

            TablePermission.objects.update_or_create(
                table=table,
                user=request.user,
                can_view=True
            )

            administration = User.objects.filter(
                profile__employee__id_filial=1910,
            ).exclude(id=request.user.id)

            # Создаем права для всей администрации
            for admin in administration:
                TablePermission.objects.update_or_create(
                    table=table,
                    user=admin,
                    can_view=True
                )

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
        return HttpResponseForbidden("Только владелец строки может управлять правами")

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

        if 'update_submit_fil' in request.POST:
            # Обработка существующих филиалов
            for f_perm in row.filial_permissions.all():
                filial_id = str(f_perm.filial.id)
                f_perm.can_edit = f'filial_can_edit_{filial_id}' in request.POST
                f_perm.can_delete = f'filial_can_delete_{filial_id}' in request.POST

                users_from_filial = User.objects.filter(
                    profile__employee__id_filial=filial_id
                )

                for user in users_from_filial:
                    # Обработка добавления пользователей для филиалов
                    RowPermission.objects.update_or_create(
                        row=row,
                        user=user,
                        defaults={
                            'can_edit': f_perm.can_edit,
                            'can_delete': f_perm.can_delete,
                        }
                    )

                f_perm.save()

        if 'add_filials_submit' in request.POST:
            new_filials = request.POST.getlist('new_filials')
            if new_filials:
                filial_can_edit = 'new_filial_can_edit' in request.POST
                filial_can_delete = 'new_filial_can_delete' in request.POST
                for filial_id in new_filials:
                    filial = get_object_or_404(Filial, pk=filial_id)
                    RowFilialPermission.objects.update_or_create(
                        row=row,
                        filial=filial,
                        defaults={
                            'can_edit': filial_can_edit,
                            'can_delete': filial_can_delete,
                        }
                    )
                    # Применяем права ко всем пользователям филиала
                    users = User.objects.filter(
                        profile__employee__id_filial=filial.id
                    ).exclude(
                        pk__in=row.permissions.values_list('user__id', flat=True)
                    )

                    for user in users:
                        RowPermission.objects.update_or_create(
                            row=row,
                            user=user,
                            defaults={
                                'can_edit': filial_can_edit,
                                'can_delete': filial_can_delete,
                            }
                        )

        messages.success(request, 'Обновление прав успешно!')
        return redirect('manage_row_permissions', table_pk=table.pk, row_pk=row.pk)

    # Получаем текущие разрешения для строки
    permissions = row.permissions.all()
    filial_permissions = row.filial_permissions.all()

    all_users = User.objects.exclude(pk=table.owner.pk)
    all_filials = Filial.objects.exclude(id=1910)

    return render(request, 'tables/manage_permissions.html', {
        'table': table,
        'row': row,
        'permissions': permissions,
        'filial_permissions': filial_permissions,
        'all_users': all_users,
        'all_filials': all_filials
    })


@login_required
def manage_table_permissions(request, table_pk):
    table = get_object_or_404(Table, pk=table_pk)

    if table.owner != request.user:
        return HttpResponseForbidden("Только владелец таблицы может редактировать права на таблицу")

    if request.method == 'POST':
        if 'update_submit' in request.POST:
            # Обработка существующих пользователей
            for perm in table.permissions.all():
                user_id = str(perm.user.id)
                perm.can_view = f'can_view_{user_id}' in request.POST
                perm.save()

        # Обработка новых пользователей
        if 'add_users_submit' in request.POST:
            new_users = request.POST.getlist('new_users')
            if new_users:
                can_view = 'new_can_view' in request.POST
                for user_id in new_users:
                    user = get_object_or_404(User, pk=user_id)
                    TablePermission.objects.update_or_create(
                        table=table,
                        user=user,
                        defaults={
                            'can_view': can_view,
                        }
                    )

        if 'update_submit_fil' in request.POST:
            # Обработка существующих филиалов
            for f_perm in table.filial_permissions.all():
                filial_id = str(f_perm.filial.id)
                f_perm.can_view = f'filial_can_view_{filial_id}' in request.POST

                users_from_filial = User.objects.filter(
                    profile__employee__id_filial=filial_id
                )

                for user in users_from_filial:
                    # Обработка добавления пользователей для филиалов
                    TablePermission.objects.update_or_create(
                        table=table,
                        user=user,
                        defaults={
                            'can_view': f_perm.can_view,
                        }
                    )

                f_perm.save()

        if 'add_filials_submit' in request.POST:
            new_filials = request.POST.getlist('new_filials')
            if new_filials:
                filial_can_view = 'new_filial_can_view' in request.POST
                for filial_id in new_filials:
                    filial = get_object_or_404(Filial, pk=filial_id)
                    TableFilialPermission.objects.update_or_create(
                        table=table,
                        filial=filial,
                        defaults={
                            'can_view': filial_can_view,
                        }
                    )
                    # Применяем права ко всем пользователям филиала
                    users = User.objects.filter(
                        profile__employee__id_filial=filial.id
                    ).exclude(
                        pk__in=table.permissions.values_list('user__id', flat=True)
                    )

                    for user in users:
                        TablePermission.objects.update_or_create(
                            table=table,
                            user=user,
                            defaults={
                                'can_view': filial_can_view,
                            }
                        )

        messages.success(request, 'Обновление прав успешно!')
        return redirect('manage_table_permissions', table_pk=table.pk)

    # Получаем текущие разрешения для таблицы
    permissions = table.permissions.all()
    filial_permissions = table.filial_permissions.all()

    all_users = User.objects.exclude(pk=table.owner.pk)
    all_filials = Filial.objects.exclude(id=1910)

    return render(request, 'tables/manage_table_permissions.html', {
        'table': table,
        'permissions': permissions,
        'filial_permissions': filial_permissions,
        'all_users': all_users,
        'all_filials': all_filials
    })


@login_required
def revoke_redact_rows(request, share_token):
    table = get_object_or_404(Table, share_token=share_token)

    if not table.has_view_permission(request.user):
        return HttpResponseForbidden("У вас нет прав на завершение редактирования этой таблицы")

    try:
        # Применяем права ко всем пользователям филиала
        filial_id = request.user.profile.employee.id_filial
        filial = Filial.objects.get(id=filial_id)
        users = User.objects.filter(
            profile__employee__id_filial=filial_id
        )

        rows = table.rows.all()

        with transaction.atomic():
            RowFilialPermission.objects.filter(
                row__table=table,
                filial=filial
            ).update(
                can_edit=False,
                can_delete=False
            )

            for row in rows:
                for user in users:
                    RowPermission.objects.filter(
                        row=row,
                        user=user
                    ).update(
                        can_edit=False,
                        can_delete=False
                    )
        messages.success(request, f'Права редактирования для филиала {filial.name} сняты со всех строк')
        return redirect('shared_table_view', share_token=table.share_token)

    except Exception as e:
        messages.error(request, f'Ошибка при снятии прав: {str(e)}')
        return redirect('shared_table_view', share_token=table.share_token)


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

    if request.user == table.owner:
        return redirect('table_detail', pk=table.pk)
    else:
        return redirect('shared_table_view', share_token=table.share_token)


@require_POST
@login_required
def unlock_row_api(request, row_pk):
    row = get_object_or_404(Row, pk=row_pk)
    if unlock_row(row, request.user):
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def edit_row(request, table_pk, row_pk):
    table = get_object_or_404(Table, pk=table_pk)
    row = get_object_or_404(Row, pk=row_pk, table=table)
    if not row.has_edit_permission(request.user):
        return JsonResponse({'status': 'error', 'message': 'Нет прав на редактирование'}, status=403)

    if request.method == 'POST':
        form = RowEditForm(request.POST, row=row)
        if form.is_valid():
            # Снимаем блокировку после успешного редактирования
            unlock_row(row, request.user)

            save_row_data(table, row, form)
            messages.success(request, 'Строка успешно отредактирована!')
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)

    lock, lock_user = lock_row(row, request.user)
    if not lock:
        return JsonResponse({
            'status': 'error',
            'message': f'Строка сейчас редактируется другим пользователем: {lock_user}'
        }, status=423)  # 423 - Locked

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

            user_filial = request.user.profile.employee.id_filial

            if user_filial:
                if user_filial != 1910:
                    # Добавляем права для филиала создателя
                    filial = get_object_or_404(Filial, pk=user_filial)
                    RowFilialPermission.objects.update_or_create(
                        row=row,
                        filial=filial,
                        defaults={
                            'can_edit': True,
                            'can_delete': True,
                        }
                    )

                    colleagues = User.objects.filter(
                        profile__employee__id_filial=user_filial,
                    ).exclude(id=request.user.id)

                    # Создаем права для всех коллег
                    for colleague in colleagues:
                        RowPermission.objects.update_or_create(
                            row=row,
                            user=colleague,
                            can_edit=True,  # Могут редактировать
                            can_delete=True  # Могут удалять
                        )

                administration = User.objects.filter(
                    profile__employee__id_filial=1910,
                ).exclude(id=request.user.id)

                # Создаем права для всей администрации
                for admin in administration:
                    RowPermission.objects.update_or_create(
                        row=row,
                        user=admin,
                        can_edit=True,
                        can_delete=True
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

#НУЖНО ПОЛНОСТЬЮ ПЕРЕДЕЛАТЬ
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

    if not table.has_view_permission(request.user):
        return HttpResponseForbidden("У вас нет прав на просмотр этой таблицы")

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
    queryset = queryset.annotate(
        user_full_name=Concat(
            F('created_by__profile__employee__secondname'),
            Value(' '),
            F('created_by__profile__employee__firstname'),
            Value(' '),
            F('created_by__profile__employee__lastname'),
            output_field=TextField()
        ),
    )

    queryset = queryset.annotate(
        filial_name=Subquery(
            Filial.objects.filter(
                id=OuterRef('created_by__profile__employee__id_filial')
            ).values('name')[:1],
            output_field=TextField()  # Указываем тип поля явно
        )
    )

    for column in table_obj.columns.all():
        queryset = Row.annotate_for_sorting(queryset, column.id, column.data_type)
    return queryset
