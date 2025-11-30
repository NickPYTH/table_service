import json
import os
from io import BytesIO

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Max, OuterRef, Subquery, CharField
from django.http import Http404
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from tables.models import CellEditLog, Filial, Department, Employee, Profile, Admin, Table, Cell, Column, Row, RowPermission, \
    TablePermission, TableFilialPermission, RowFilialPermission, CellLock, ColumnPermission, SelectType
from .helper import get_table_ids_permissions, FileUploadBrowsableRenderer, import_table, import_to_existing_table, \
    export_table, update_cell_by_id
from .serializers import (
    UserSerializer,
    FilialSerializer,
    DepartmentSerializer,
    EmployeeSerializer,
    ProfileSerializer,
    AdminSerializer,
    ProfileCreateUpdateSerializer,
    TableListSerializer, TableDetailSerializer, CellSerializer, ColumnSerializer, RowSerializer,
    RowPermissionSerializer, TablePermissionsSerializer, TableFilialPermissionsSerializer,
    RowFilialPermissionSerializer, SelectTypeSerializer, CellEditLogSerializer, update_auto_column,
    ColumnPermissionSerializer
)
from .utils import send_table_update, send_cell_update


class CellPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'limit'
    max_page_size = 10000

    def get_paginated_response(self, data):
        search_value = self.request.query_params.get('search', '')

        response_data = {
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'search_info': {
                'value': search_value,
                'has_search': bool(search_value)
            },
            'results': data
        }

        return Response(response_data)

    def paginate_queryset(self, queryset, request, view=None):
        return super().paginate_queryset(queryset, request, view)


class RowPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'limit'
    max_page_size = 10000

    def get_paginated_response(self, data):
        search_value = self.request.query_params.get('search', '')

        response_data = {
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'search_info': {
                'value': search_value,
                'has_search': bool(search_value)
            },
            'results': data
        }

        return Response(response_data)

    def paginate_queryset(self, queryset, request, view=None):
        return super().paginate_queryset(queryset, request, view)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        table_id = self.request.query_params.get('table_id', None)
        row_id = self.request.query_params.get('row_id', None)
        column_id = self.request.query_params.get('column_id', None)
        if row_id and table_id:
            user_ids_table = TablePermission.objects.filter(table_id=table_id).values_list('user_id', flat=True)
            user_ids_row = RowPermission.objects.filter(table=table_id, row=row_id).values_list('user', flat=True)
            user_ids = set(user_ids_table).difference(set(user_ids_row))
            queryset = queryset.filter(id__in=user_ids)
        elif column_id and table_id:
            user_ids_table = TablePermission.objects.filter(table_id=table_id).values_list('user_id', flat=True)
            user_ids_column = ColumnPermission.objects.filter(table=table_id, column=column_id).values_list('user', flat=True)
            user_ids = set(user_ids_table).difference(set(user_ids_column))
            queryset = queryset.filter(id__in=user_ids)
        elif table_id:
            user_ids = TablePermission.objects.filter(table_id=table_id).values_list('user__id', flat=True)
            queryset = queryset.exclude(id__in=user_ids)
        return queryset


class FilialViewSet(viewsets.ModelViewSet):
    queryset = Filial.objects.all()
    serializer_class = FilialSerializer

    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self):
        queryset = super().get_queryset()
        row_id = self.request.query_params.get('row_id')
        table_id = self.request.query_params.get('table_id')
        if row_id:
            row = get_object_or_404(Row, pk=row_id)
            if row:
                filial_ids = RowFilialPermission.objects.filter(row=row).values_list('filial__id', flat=True)
                queryset = queryset.exclude(id__in=filial_ids)
            else:
                return queryset.none()
        if table_id:
            table = get_object_or_404(Table, pk=table_id)
            if table:
                filial_ids = TableFilialPermission.objects.filter(table=table).values_list('filial__id', flat=True)
                queryset = queryset.exclude(id__in=filial_ids)
            else:
                return queryset.none()
        return queryset


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer

    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_queryset(self):
        queryset = super().get_queryset()
        filial_id = self.request.query_params.get('filial_id')
        if filial_id:
            queryset = queryset.filter(id_filial=filial_id)
        return queryset


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()

    # permission_classes = [permissions.IsAuthenticated]
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProfileCreateUpdateSerializer
        return ProfileSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Profile.objects.all()
        return Profile.objects.filter(user=self.request.user)


class AdminViewSet(viewsets.ModelViewSet):
    queryset = Admin.objects.all()
    serializer_class = AdminSerializer
    # permission_classes = [permissions.IsAdminUser]


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    # permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        profile = Profile.objects.filter(user_id=user.id).prefetch_related('employee').first()
        if profile:
            return {"id": user.id, "username": user.username, "email": user.email, "first_name": profile.employee.firstname, "last_name": profile.employee.lastname,
                    "second_name": profile.employee.secondname}
        return user


class TableListViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableListSerializer

    # ПОПРОБОВАТЬ ЗАСУНУТЬ ОПРЕДЕЛНИЕ В СТАНДАРТНЫЕ ОГРАНИЧЕНИЯ Permissions
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        all_permissions = get_table_ids_permissions(user)
        if all_permissions:
            queryset = queryset.filter(id__in=all_permissions)
        else:
            queryset = queryset.none()
        return queryset


class TableDetailViewSet(viewsets.ModelViewSet):
    serializer_class = TableDetailSerializer
    queryset = Table.objects.all()

    @action(detail=True, methods=['get'], url_path='locks')
    def cell_lock(self, request, pk=None):
        columns_ids = Column.objects.filter(table_id=pk).values_list('id', flat=True)
        cells_ids = Cell.objects.filter(column__in=columns_ids).values_list('id', flat=True)
        cells_lock = CellLock.objects.filter(cell_id__in=cells_ids).select_related('cell')
        locks = [{'cell_id': lock.cell_id, 'user_id': lock.user_id} for lock in cells_lock]
        return Response(locks)

    @action(detail=True, methods=['get'], url_path='not_locked')
    def not_locked(self, request, pk=None):
        columns_ids = Column.objects.filter(table_id=pk).values_list('id', flat=True)
        cells_ids = Cell.objects.filter(column__in=columns_ids).values_list('id', flat=True)
        cells_locked = CellLock.objects.filter(cell_id__in=cells_ids).select_related('cell').values_list('cell_id', 'user_id', flat=True)
        cells_not_locked = set(cells_ids) - set(cells_locked)
        return Response(cells_not_locked)

    @action(detail=True, methods=['get'], url_path='remove_locks')
    def remove_locks(self, request, pk=None):
        user = self.request.user
        columns_ids = Column.objects.filter(table_id=pk).values_list('id', flat=True)
        cells_ids = Cell.objects.filter(column__in=columns_ids).values_list('id', flat=True)
        try:
            CellLock.objects.filter(cell_id__in=cells_ids, user=user).delete()
            return Response({"success": True})
        except:
            return Response({"success": False})

    @action(detail=True, methods=['get'], url_path='export/(?P<format_type>[a-z]+)')
    def export(self, request, pk=None, format_type='xlsx'):
        if format_type not in ['csv', 'xls', 'xlsx']:
            return Response({'error': 'Invalid format'}, status=400)
        try:
            response = export_table(request, pk, format_type)
            return response
        except:
            return Response({'error': 'Ошибка экспорта'}, status=400)

    @action(detail=True, methods=['post'])
    def set_permission(self, request, pk=None):
        with transaction.atomic():
            user_id = request.query_params.get('user_id')
            if user_id:
                # TODO Сюда добавить потом создание колонок
                if not TablePermission.objects.filter(table_id=pk, user_id=user_id).exists():
                    TablePermission.objects.create(table_id=pk, user_id=user_id)
                row_ids = Row.objects.filter(table_id=pk).values_list('id', flat=True)
                columns_ids = Column.objects.filter(table_id=pk).values_list('id', flat=True)
                column_permissions = []
                row_permissions = []
                for column_id in columns_ids:
                    columnpermission = ColumnPermission(table_id=pk, column=column_id)
                    column_permissions.append(columnpermission)
                else:
                    ColumnPermission.objects.bulk_create(column_permissions, ignore_conflicts=True)
                for row_id in row_ids:
                    rowpermission = RowPermission(row_id=row_id, user_id=user_id)  # TODO
                    row_permissions.append(rowpermission)
                else:
                    RowPermission.objects.bulk_create(row_permissions, ignore_conflicts=True)
                return Response({"success": True})
            return Response({"success": False})

    @action(detail=True, methods=['post'])
    def set_filial_permission(self, request, pk=None):
        with transaction.atomic():
            filial_id = request.query_params.get('filial_id')
            if filial_id:
                if not TableFilialPermission.objects.filter(filial_id=filial_id, table_id=pk).exists():
                    TableFilialPermission.objects.create(filial_id=filial_id, table_id=pk)
                row_ids = Row.objects.filter(table_id=pk).values_list('id', flat=True)
                columns_ids = Column.objects.filter(table_id=pk).values_list('id', flat=True)
                column_permissions = []
                row_permissions = []
                for column_id in columns_ids:
                    columnpermission = ColumnPermission(table_id=pk, column_id=column_id)
                    column_permissions.append(columnpermission)
                else:
                    ColumnPermission.objects.bulk_create(column_permissions, ignore_conflicts=True)

                for row_id in row_ids:
                    rowpermission = RowPermission(row_id=row_id, user_id=filial_id)
                    row_permissions.append(rowpermission)
                else:
                    RowPermission.objects.bulk_create(row_permissions, ignore_conflicts=True)
                return Response({"success": True})
            return Response({"success": False})

    def get_queryset(self):
        queryset = super().get_queryset()
        table_id = self.kwargs.get('pk')
        queryset = queryset.filter(id=table_id)
        user = self.request.user
        all_permissions = get_table_ids_permissions(user)
        if all_permissions:
            queryset = queryset.filter(id__in=all_permissions)
        else:
            queryset = queryset.none()
        return queryset

    def perform_update(self, serializer):
        instance = serializer.save()
        send_table_update(instance)
        return instance


class CellViewSet(viewsets.ModelViewSet):
    queryset = Cell.objects.all()
    serializer_class = CellSerializer
    pagination_class = CellPagination
    ordering_fields = ('row',)

    def perform_create(self, serializer):
        table_id = serializer.validated_data['table'].id
        order = serializer.validated_data['order']
        if order > 0:
            column_max_order = Column.objects.filter(table_id=table_id).aggregate(max_order=Max('order'))['max_order'] + 1
            serializer.save(order=column_max_order)

    def perform_update(self, serializer):
        instance = serializer.save()
        send_cell_update(instance)
        return instance

    def get_queryset(self):
        queryset = super().get_queryset()
        table_id = self.request.query_params.get('table')
        if table_id:
            queryset = queryset.filter(table_id=table_id).order_by('row')
        else:
            queryset.none()

        search_value = self.request.query_params.get('search', '')
        if search_value:
            queryset = queryset.filter(Q(value__icontains=search_value))

        return queryset


class ColumnViewSet(viewsets.ModelViewSet):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer
    filter_backends = (OrderingFilter,)
    ordering_fields = ('id', 'name', 'order', 'data_type')
    ordering = ('id',)


    @action(detail=True, methods=['get'], url_path='select')
    def getSelect(self, request, pk=None):
        column = Column.objects.get(pk=pk)
        if column and column.data_type == 'SELECT':
            select_types = SelectType.objects.filter(column_id=column.id).values_list('value', flat=True)
            return Response({"success": True, "select_values": select_types})
        return Response({"success": False})


    def perform_create(self, serializer):
        table_id = serializer.validated_data['table'].id
        column_max_order = Column.objects.filter(table_id=table_id).aggregate(max_order=Max('order'))['max_order']
        if column_max_order is None:
            serializer.save(order=1)
        else:
            serializer.save(order=column_max_order + 1)

    def get_queryset(self):
        queryset = super().get_queryset()
        table_id = self.request.query_params.get('table')
        if table_id:
            queryset = queryset.filter(table_id=table_id)
        return queryset

    def destroy(self, request, *args, **kwargs):
        try:
            column_id = self.kwargs.get('pk')
            table_id = Column.objects.get(pk=column_id).table.id
            Cell.objects.filter(column=column_id).delete()
            instance = self.get_object()
            instance.delete()
            #Для автоинкремента
            auto_column = Column.objects.filter(table_id=table_id, data_type='auto').first()
            table_columns = Column.objects.filter(table_id=table_id).values_list('id', flat=True)
            if auto_column:
                columns_ids = set(auto_column.related_column_ids)  &  set(table_columns)
                auto_column.related_column_ids = list(columns_ids)
                auto_column.save()
                update_auto_column(table_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Http404:
            return Response(status=status.HTTP_404_NOT_FOUND)


class RowDetailViewSet(viewsets.ModelViewSet):
    serializer_class = RowSerializer
    queryset = Row.objects.all()

    def destroy(self, request, *args, **kwargs):
        row_id = self.kwargs.get('pk')
        table_id = Row.objects.get(pk=row_id).table.id
        if not Row.objects.filter(pk=row_id).exists():
            return Response({'error': 'Row not found'}, status=404)
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            Cell.objects.filter(row=row_id).delete()
            #Для автоинкеремента
            update_auto_column(table_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Http404:
            return Response(status=status.HTTP_404_NOT_FOUND)


class RowListViewSet(viewsets.ModelViewSet):
    serializer_class = RowSerializer
    queryset = Row.objects.all().order_by('order')
    pagination_class = RowPagination

    def sort_by_param(self, queryset, sort_field, sort_direction):
        order_prefix = '' if sort_direction == 'asc' else '-'
        subquery = Cell.objects.filter(
            row=OuterRef('id'),
            column=sort_field
        ).values('value')[:1]

        queryset = queryset.annotate(
            sort_value=Subquery(subquery, output_field=CharField())
        ).order_by(f'{order_prefix}sort_value', 'order')

        return queryset

    def sort_by_param_optimized(self, queryset, sort_field, sort_direction):
        """Оптимизированная сортировка без использования OuterRef"""
        from django.db.models import Case, When, Value, CharField

        # Получаем значения для сортировки одним запросом
        sort_values = Cell.objects.filter(
            column=sort_field,
            row__in=queryset.values_list('id', flat=True)
        ).values('row', 'value')

        # Создаем mapping row_id -> value
        value_map = {item['row']: item['value'] for item in sort_values}

        # Создаем условия для сохранения порядка
        preserved_order = Case(
            *[When(id=row_id, then=Value(pos)) for pos, row_id in enumerate(queryset.values_list('id', flat=True))],
            output_field=CharField()
        )

        # Аннотируем значения для сортировки
        order_prefix = '' if sort_direction == 'asc' else '-'

        result_queryset = queryset.annotate(
            sort_value=Case(
                *[When(id=row_id, then=Value(value)) for row_id, value in value_map.items()],
                default=Value(''),
                output_field=CharField()
            )
        ).order_by(f'{order_prefix}sort_value', preserved_order)

        return result_queryset

    def get_queryset(self):
        queryset = super().get_queryset()
        table_id = self.request.query_params.get('table')
        if table_id:
            queryset = queryset.filter(table=table_id).order_by('order')
        else:
            queryset.none()

        # Если указан признак сортировки
        sort_field = self.request.query_params.get('sort_field', None)
        sort_direction = self.request.query_params.get('sort_direction', None)

        # Общий поиск по строкам
        search_value = self.request.query_params.get('search', None)
        if search_value is not None:
            filtered_queryset = []
            for row in queryset:
                if Cell.objects.filter(Q(value__icontains=search_value, row=row.id)).count() > 0:
                    filtered_queryset.append(row)
            return filtered_queryset

        # Поиск по колоночным фильтрам
        is_column_search = self.request.query_params.get('is_column_search', None)
        if is_column_search is not None:
            column_search_mode = self.request.query_params.get('column_search_mode', None)
            filtered_queryset = []
            if column_search_mode == 'or':
                # 1. Собираем условия фильтрации
                filter_conditions = Q()
                columns = Column.objects.filter(table_id=table_id)

                for column in columns:
                    search_value = self.request.query_params.get(str(column.id))
                    if search_value:
                        # Добавляем условие OR для каждой колонки
                        filter_conditions |= Q(
                            id__in=Cell.objects.filter(
                                column=column.id,
                                value__icontains=search_value
                            ).values_list('row', flat=True)
                        )

                # 2. Применяем фильтрацию
                if filter_conditions:
                    result_queryset = queryset.filter(filter_conditions).distinct()
                else:
                    result_queryset = queryset

                # 3. Сортировка
                if sort_field is not None:
                    result_queryset = self.sort_by_param_optimized(result_queryset, sort_field, sort_direction)

                return result_queryset
            else:
                # 1. Собираем все параметры фильтрации одним запросом
                columns = Column.objects.filter(table_id=table_id).values('id', 'table_id')
                filter_params = {}

                for column in columns:
                    search_value = self.request.query_params.get(str(column['id']))
                    if search_value:
                        filter_params[column['id']] = search_value

                # Если нет параметров фильтрации, возвращаем исходный queryset
                if not filter_params:
                    if sort_field is not None:
                        return self.sort_by_param_optimized(queryset, sort_field, sort_direction)
                    return queryset

                # 2. Определяем базовый набор ID строк
                if filtered_queryset:
                    base_row_ids = [row.id for row in filtered_queryset]
                else:
                    base_row_ids = list(queryset.values_list('id', flat=True))

                # 3. Для каждого условия фильтрации находим подходящие row_id
                valid_row_ids = set(base_row_ids)

                for column_id, search_value in filter_params.items():
                    if not valid_row_ids:  # Если уже нет подходящих строк, выходим
                        break

                    # Ищем ячейки, удовлетворяющие условию
                    matching_cells = Cell.objects.filter(
                        column=column_id,
                        value__icontains=search_value,
                        row__in=valid_row_ids
                    ).values_list('row', flat=True)

                    # Обновляем множество valid_row_ids
                    valid_row_ids = valid_row_ids.intersection(set(matching_cells))

                # 4. Фильтруем исходный queryset по найденным ID
                if valid_row_ids:
                    result_queryset = queryset.filter(id__in=valid_row_ids)
                else:
                    result_queryset = queryset.none()

                # 5. Применяем сортировку
                if sort_field is not None:
                    result_queryset = self.sort_by_param_optimized(result_queryset, sort_field, sort_direction)

                return result_queryset

        if sort_field is not None:
            queryset = self.sort_by_param(queryset, sort_field, sort_direction)

        return queryset


class TablePermissionViewSet(viewsets.ModelViewSet):
    serializer_class = TablePermissionsSerializer
    queryset = TablePermission.objects.all()

    def perform_create(self, serializer):
        table = serializer.validated_data['table']
        user_id = serializer.validated_data['user_id']
        user = User.objects.get(id=user_id)
        row_permissions = []
        for row in Row.objects.filter(table=table):
            row_permission = RowPermission(row=row.id, user=user.id, table=table.id)
            row_permissions.append(row_permission)
        RowPermission.objects.bulk_create(row_permissions)

        serializer.save()

    def perform_destroy(self, instance):
        user_id = instance.user_id
        table_id = instance.table.id
        RowPermission.objects.filter(user=user_id, table=table_id).delete()
        ColumnPermission.objects.filter(user=user_id, table=table_id).delete()
        instance.delete()

    def get_queryset(self):
        queryset = super().get_queryset()
        table_id = self.request.query_params.get('table_id')
        user_id = self.request.query_params.get('user_id')
        if table_id:
            queryset = queryset.filter(table_id=table_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset


class TableFilialPermissionViewSet(viewsets.ModelViewSet):
    serializer_class = TableFilialPermissionsSerializer
    queryset = TableFilialPermission.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        filial_id = self.request.query_params.get('filial_id')
        table_id = self.request.query_params.get('table_id')
        if filial_id:
            queryset = queryset.filter(filial__id=filial_id)
        if table_id:
            queryset = queryset.filter(table__id=table_id)
        return queryset


class RowPermissionViewSet(viewsets.ModelViewSet):
    serializer_class = RowPermissionSerializer
    queryset = RowPermission.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        row_id = self.request.query_params.get('row_id')
        table_id = self.request.query_params.get('table_id')
        rows_ids = self.request.query_params.get('rows_ids')
        if table_id:
            queryset = queryset.filter(table=table_id)
        if user_id:
            queryset = queryset.filter(user=user_id)
        if row_id:
            queryset = queryset.filter(row=row_id)
        if rows_ids:
            filtered_permission = []
            rows_ids = json.loads(rows_ids) # На что пришел запрос с клиента
            for permission in queryset:
                if permission.row in rows_ids:
                    if permission.can_edit:
                        filtered_permission.append(permission)
            return  filtered_permission
        return queryset


class ColumnPermissionViewSet(viewsets.ModelViewSet):
    serializer_class = ColumnPermissionSerializer
    queryset = ColumnPermission.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        column_id = self.request.query_params.get('column_id')
        table_id = self.request.query_params.get('table_id')
        columns_ids = self.request.query_params.get('columns_ids')
        if table_id:
            queryset = queryset.filter(table=table_id)
        if user_id:
            queryset = queryset.filter(user=user_id)
        if column_id:
            queryset = queryset.filter(column=column_id)
        if columns_ids:
            filtered_permission = []
            columns_ids = json.loads(columns_ids) # На что пришел запрос с клиента
            for permission in queryset:
                if permission.column in columns_ids:
                    if permission.can_edit:
                        filtered_permission.append(permission)
            return  filtered_permission
        return queryset


class RowFilialPermissionViewSet(viewsets.ModelViewSet):
    serializer_class = RowFilialPermissionSerializer
    queryset = RowFilialPermission.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        filial_id = self.request.query_params.get('filial_id')
        row_id = self.request.query_params.get('row_id')
        if filial_id:
            queryset = queryset.filter(filial=filial_id)
        if row_id:
            queryset = queryset.filter(row=row_id)

        return queryset


class FileUploadViewSet(viewsets.ViewSet):
    parser_classes = (MultiPartParser, FormParser)
    renderer_classes = [JSONRenderer, FileUploadBrowsableRenderer]

    @action(detail=False, methods=['post'])
    def upload(self, request):
        if 'file' not in request.FILES:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = self.request.user
        file = request.FILES['file']
        name = request.data.get('table_name')
        filename = file.name
        extensions = os.path.splitext(filename)[1].lower()
        if extensions != '.xlsx':
            return Response(
                {"error": "Файл должен быть в формате XLSX"},
                status=status.HTTP_400_BAD_REQUEST
            )
        file_data = BytesIO(file.read())
        import_table(file_data, name, user)
        return Response({
            "filename": file.name,
            "size": file.size,
        })


class RowUploadViewSet(viewsets.ViewSet):
    parser_classes = (MultiPartParser, FormParser)
    renderer_classes = [JSONRenderer, FileUploadBrowsableRenderer]

    @action(detail=False, methods=['post'])
    def upload(self, request):
        table_id = request.data.get('table_id')
        if table_id:
            if 'file' not in request.FILES:
                return Response(
                    {"error": "No file provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user = self.request.user
            file = request.FILES['file']
            filename = file.name
            extensions = os.path.splitext(filename)[1].lower()
            if extensions != '.xlsx':
                return Response(
                    {"error": "Файл должен быть в формате XLSX"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            file_data = BytesIO(file.read())
            import_to_existing_table(file_data, table_id, user)
            return Response({
                "filename": file.name,
                "size": file.size,
            })

class SelectTypeViewSet(viewsets.ModelViewSet):
    queryset = SelectType.objects.all()
    serializer_class = SelectTypeSerializer

    @action(detail=True, methods=['get'], url_path='column')
    def column(self, request, pk=None):
        response = []
        for selecttype in SelectType.objects.filter(column_id=pk):
            response.append(SelectTypeSerializer(selecttype).data)
        return Response(response)


class CellEditLogViewSet(viewsets.ModelViewSet):
    queryset = CellEditLog.objects.all()
    serializer_class = CellEditLogSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        row_id = self.request.query_params.get('row_id')
        if row_id:
            queryset = queryset.filter(row_id=row_id)

        return queryset

