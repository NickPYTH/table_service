from datetime import datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.db.models.expressions import F
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from tables.models import CellEditLog, Filial, Employee, Department, Profile, Admin, Table, Column, Cell, Row, \
    RowPermission, \
    TablePermission, TableFilialPermission, RowFilialPermission, CellLock, ColumnPermission, ColumnFilialPermission, \
    SelectType


def notify_table_update():
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "table_updates",
        {
            "type": "table.updated",
            "message": "Table data updated",
        }
    )

def numberToChar(num):
    if num < 1:
        return "T"
    result = ""
    while num > 0:
        num -= 1
        result = chr(num % 26 + 65) + result
        num //= 26
    return result


def update_auto_with_related_number(auto_column, rows_ids):
    related_column_id = auto_column.related_number_column_id

    rows_with_values = []
    for row_id in rows_ids:
        cell = Cell.objects.filter(column=related_column_id, row=row_id).first()
        current_value = cell.value if cell else None
        rows_with_values.append((row_id, current_value))
    number = 1
    previous_value = None

    for row_id, current_value in rows_with_values:
        if current_value != previous_value:
            number = 1
            previous_value = current_value

        Cell.objects.filter(column=auto_column.id, row=row_id).update(value=str(number))
        number += 1


def update_auto_with_related_columns(auto_column, rows_ids):
    column_ids = auto_column.related_column_ids
    columns_dict = []
    for row_id in rows_ids:
        row_value_list = []
        for column_id in column_ids:
            cell = Cell.objects.filter(column=column_id, row=row_id).first()
            column_value = cell.value if cell else None
            row_value_list.append(column_value)
        columns_dict.append(tuple(row_value_list))

    unique_rows = list(set(columns_dict))
    for unique_row in unique_rows:
        indices = [x for x, item in enumerate(columns_dict) if item == unique_row]
        number = 1
        for index in indices:
            Cell.objects.filter(column=auto_column.id, row=rows_ids[index]).update(value=str(number))
            number += 1


def update_auto_column(table_id):
    auto_column = Column.objects.filter(table_id=table_id, data_type='auto').first()
    if not auto_column:
        return

    rows_ids = Table.objects.prefetch_related('rows').get(id=table_id).rows.all().values_list('id', flat=True)
    Cell.objects.filter(row__in=rows_ids, column=auto_column.id).update(value="")

    if auto_column.related_number_column_id:
        update_auto_with_related_number(auto_column, rows_ids)
    else:
        update_auto_with_related_columns(auto_column, rows_ids)

# def update_auto_column(table_id):
#     auto_column = Column.objects.filter(table_id=table_id, data_type='auto').first()
#     if auto_column:
#         column_ids = auto_column.related_column_ids
#         column_by_date_id = auto_column.related_number_column_id
#         columns_dict = []
#         rows_ids = Table.objects.prefetch_related('rows').get(id=table_id).rows.all().values_list('id', flat=True)
#         Cell.objects.filter(row__in=rows_ids, column=auto_column.id).update(value="")
#         if not column_by_date_id:
#             for row_id in rows_ids:
#                 row_value_list = []
#                 for column_id in column_ids:
#                     column_value = Cell.objects.filter(column=column_id, row=row_id).first().value
#                     row_value_list.append(column_value)
#                 columns_dict.append(tuple(row_value_list))
#                 row_value_list.clear()
#         unique_rows = list(set(columns_dict))
#         for unique_row in unique_rows:
#             indices = [x for x, item in enumerate(columns_dict) if item == unique_row]
#             number = 1
#             for index in indices:
#                 Cell.objects.filter(column=auto_column.id, row=rows_ids[index]).update(value="{}".format(number))
#                 number += 1

def normalize_row_orders(table):
    rows = Row.objects.filter(table=table).order_by('order')
    for index, row in enumerate(rows):
        if row.order != index:
            Row.objects.filter(id=row.id).update(order=index)

#TODO Import table column permissions, setting table column permissions in table permissions, edit column permissions when table  edit,
class UserSerializer(serializers.ModelSerializer):
    second_name = serializers.CharField(read_only=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',  'second_name']


class FilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filial
        fields = '__all__'
        extra_kwargs = {
            'id': {'read_only': True},
            'set_date': {'format': '%Y-%m-%d'},
            'end_date': {'format': '%Y-%m-%d'}
        }


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'
        extra_kwargs = {
            'set_date': {'format': '%Y-%m-%d'},
            'end_date': {'format': '%Y-%m-%d'}
        }


class EmployeeSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(source='id_department', read_only=True)
    filial = FilialSerializer(source='id_filial', read_only=True)

    class Meta:
        model = Employee
        fields = '__all__'
        extra_kwargs = {
            'set_date': {'format': '%Y-%m-%d'},
            'end_date': {'format': '%Y-%m-%d'},
            'id_filial': {'write_only': True},
            'id_department': {'write_only': True}
        }


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    employee = EmployeeSerializer()

    class Meta:
        model = Profile
        fields = '__all__'


class AdminSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Admin
        fields = '__all__'
        extra_kwargs = {
            'created_at': {'format': '%Y-%m-%d %H:%M:%S'}
        }


class ProfileCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'


class ColumnSerializer(serializers.ModelSerializer):
    select_values = serializers.SerializerMethodField(required=False)
    related_column_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    related_number_column_id = serializers.IntegerField(required=False)
    class Meta:
        model = Column
        fields = ['id', 'name', 'order', 'data_type', "table", 'select_values', 'related_column_ids','related_number_column_id']
        extra_kwargs = {
            'id': {'required': False},
            'table': {'required': False},
            'name': {'required': False},
            'order': {'required': False},
            'data_type': {'required': False},
        }

    #Попробовать реализовать логику с автоинкрементом здесь в методе update
    def update(self, instance, validated_data):
        if validated_data['data_type'] == 'select':
            column_values = Cell.objects.filter(column=instance.id).exclude(value__isnull=True).exclude(value="").values_list('value', flat=True)
            column_dict_select = []
            for column_value in column_values:
                select_type = SelectType(column_id=instance.id, name=column_value)
                column_dict_select.append(select_type)
            SelectType.objects.bulk_create(column_dict_select, ignore_conflicts=True)
        elif validated_data['data_type'] == 'auto':
            super().update(instance, validated_data)
            table_id = Column.objects.get(id=instance.id).table.id
            update_auto_column(table_id)
        else:
            SelectType.objects.filter(column_id=instance.id).delete()
        return super().update(instance, validated_data)

    def create(self, validated_data):
        notify_table_update()
        table = validated_data['table']
        columns = Column.objects.filter(table=table)
        column = super().create(validated_data)
        user = self.context['request'].user
        if len(columns) == 0:
            Row.objects.create(table=column.table, created_by=user)
        rows = column.table.rows.all()
        cells = [Cell(row=row.id, column=column.id, table_id=table.id) for row in rows]
        Cell.objects.bulk_create(cells)

        # Накидываем права на новый столбец
        for table_permission in TablePermission.objects.filter(table=table, can_edit=True):
            ColumnPermission.objects.create(user=table_permission.user.id, column=column.id, table=table.id, can_edit=True, can_view=True).save()

        return column

    def get_select_values(self, obj):
        values = SelectType.objects.filter(column_id=obj.id).exclude(name__isnull=True).exclude(name="").values_list('name', flat=True)
        return values


class CellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cell
        fields = ['id', 'column', 'row', 'value', 'formula_value']
        extra_kwargs = {
            'column': {'required': False},
            'row': {'required': False},
        }

    def update(self, instance, validated_data):
        super().update(instance, validated_data)
        table_id = Cell.objects.get(id=instance.id).table_id
        update_auto_column(table_id)
        return instance


class RowSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    order = serializers.IntegerField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    cells = CellSerializer(many=True, read_only=True)
    cells_list = serializers.SerializerMethodField()

    class Meta:
        model = Row
        fields = ['id', 'order', 'created_by', "table", "cells", "cells_list"]

    def get_cells_list(self, obj):
        cell_list = []
        # Если указан признак сортировки
        if 'sort_field' in self.context['request'].query_params:
            sort_field = self.context['request'].query_params.get('sort_field')
            sort_direction = self.context['request'].query_params.get('sort_direction') # asc/(-)desc
            queryset = Cell.objects.filter(row=obj.id).order_by('column')
        else:
            queryset = Cell.objects.filter(row=obj.id)
        for cell in queryset:
            cell_list.append(CellSerializer(cell).data)
        return cell_list

    def create(self, validated_data):
        table = validated_data.pop('table')
        position = None
        row_for_copy = None
        with_copy = False
        if 'withCopy' in self.context['request'].data:
            with_copy = self.context['request'].data['withCopy']
        if 'currentRowId' in self.context['request'].data:
            current_row_id = self.context['request'].data['currentRowId']
            row_for_copy = Row.objects.get(id=current_row_id)
        if 'position' in self.context['request'].data:
            position = self.context['request'].data['position']
        owner = self.context['request'].user

        # Нормализуем порядок перед вставкой тк при удалении остаются дырки
        normalize_row_orders(table)

        all_rows = Row.objects.filter(table=table).order_by('order')
        rows_count = all_rows.count()

        if isinstance(position, int):
            if position < 0:
                position = 0
            elif position > rows_count:
                position = rows_count
            order = position
            Row.objects.filter(table=table, order__gte=position).update(order=F('order') + 1)
        else:
            order = rows_count

        row = Row.objects.create(table=table, created_by=owner, order=order)

        # Накидываем права на новую строку
        for table_permission in TablePermission.objects.filter(table=table, can_edit=True):
            RowPermission.objects.create(user=table_permission.user.id, row=row.id, table=table.id).save()

        columns = table.columns.all()
        cells = [Cell(row=row.id, column=column.id, table_id=table.id) for column in columns]
        Cell.objects.bulk_create(cells)

        if row_for_copy and with_copy:
            cells_for_copy = Cell.objects.filter(row=row_for_copy.id)
            for cell_for_copy in cells_for_copy:
                for cell in cells:
                    if cell.column == cell_for_copy.column:
                        cell.value = cell_for_copy.value
                        cell.save()

        #Для автоинкремента
        update_auto_column(table.id)

        return row


class TableDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    created_at = serializers.SerializerMethodField()
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Table
        fields = ['id','title','owner','created_at','share_token', 'with_cell_confirm', 'with_cell_logging']
        extra_kwargs = {
            'share_token': {'read_only': True},
            'created_at': {'read_only': True},
        }

    def update(self, request, pk=None):
        table = Table.objects.get(pk=request.id)
        table.title = pk.get('title')
        table.with_cell_confirm = pk.get('with_cell_confirm')
        table.with_cell_logging = pk.get('with_cell_logging')
        table.save()
        return table

    def get_created_at(self, obj):
        return int(obj.created_at.timestamp()) * 1000


class TableListSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields  = ['id','title','owner','created_at','share_token', 'with_cell_confirm', 'with_cell_logging']
        extra_kwargs = {
            'share_token': {'read_only': True},
            'created_at': {'read_only': True},
        }

    def get_created_at(self, obj):
        return int(obj.created_at.timestamp()) * 1000

    def create(self, validated_data):
        owner = self.context['request'].user
        created_at = datetime.now()
        title = validated_data.pop('title')
        with_cell_confirm = validated_data.pop('with_cell_confirm')
        with_cell_logging = validated_data.pop('with_cell_logging')
        table = Table.objects.create(owner=owner, title=title, created_at=created_at, with_cell_confirm=with_cell_confirm, with_cell_logging=with_cell_logging)
        TablePermission.objects.create(table=table, user=owner)
        notify_table_update()
        return table


class TablePermissionsSerializer(serializers.ModelSerializer):
    # В модельке сделать уникальный ключ по двум полям, может быть задвоение
    user_id = serializers.IntegerField()
    user = UserSerializer(read_only=True)
    class Meta:
        model = TablePermission
        fields = ['id','user_id','can_view', 'can_edit', 'table', 'user']

    def create(self, validated_data):
        user = get_object_or_404(User,id=validated_data['user_id'])
        if user:
            permissions = TablePermission.objects.create(user=user, **validated_data)
            table = validated_data['table']
            table_id = table.id
            user_id = validated_data['user_id']
            row_permissions_list = []
            column_permissions_list = []
            rows = Row.objects.filter(table=table_id).all()
            columns = Column.objects.filter(table=table_id).all()
            for row in rows:
                row_permission = RowPermission(user=user_id, row=row.id, table=table_id, can_edit=True, can_delete=True)
                row_permissions_list.append(row_permission)
            for column in columns:
                column_permission = ColumnPermission(user=user_id, column=column.id, table=table_id, can_view=True,
                                                     can_edit=True)
                column_permissions_list.append(column_permission)
            RowPermission.objects.bulk_create(row_permissions_list, ignore_conflicts=True)
            ColumnPermission.objects.bulk_create(column_permissions_list, ignore_conflicts=True)
            return permissions
        return None

    def update(self, request, pk=None):
        table_permission = TablePermission.objects.get(pk=request.id)
        table_permission.can_edit = pk.get('can_edit')
        table_permission.save()
        row_permissions = []
        column_permissions = []
        for row_permission in RowPermission.objects.filter(user=request.user_id, table=request.table_id):
            row_permission.can_edit = pk.get('can_edit')
            row_permission.can_delete = pk.get('can_edit')
            row_permissions.append(row_permission)
        for column_permission in ColumnPermission.objects.filter(user=request.user_id, table=request.table_id):
            column_permission.can_edit = pk.get('can_edit')
            column_permission.can_view = pk.get('can_edit')
            column_permissions.append(column_permission)
        RowPermission.objects.bulk_update(row_permissions, fields=['can_edit', 'can_delete'])
        ColumnPermission.objects.bulk_update(column_permissions, fields=['can_edit', 'can_view'])
        return table_permission




    def _delete_related_permissions(self, instance):
        table_id = instance.id
        user_id = instance.user_id
        RowPermission.objects.filter(user=user_id, table=table_id).delete()
        ColumnPermission.objects.filter(user=user_id, table=table_id).delete()


class TableFilialPermissionsSerializer(serializers.ModelSerializer):
    filial_id = serializers.IntegerField()
    filial = FilialSerializer(read_only=True)
    class Meta:
        model = TableFilialPermission
        fields = ['id','table','filial_id','can_view','filial']

    def create(self, validated_data):
        filial = get_object_or_404(Filial,id=validated_data['filial_id'])
        if filial:
            permissions = TableFilialPermission.objects.create(filial=filial, **validated_data)
            return permissions


class RowPermissionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.IntegerField()
    row = serializers.IntegerField()
    table = serializers.IntegerField()
    user_model = serializers.SerializerMethodField()
    class Meta:
        model = RowPermission
        fields = ['id','row','user', 'table', 'can_edit', 'can_delete', 'user_model']

    def create(self, validated_data):
        permissions = RowPermission.objects.create(row=validated_data['row'], user=validated_data['user'], table=validated_data['table'])
        return permissions

    def get_user_model(self, obj):
        user = User.objects.get(id=obj.user)
        return UserSerializer(user).data


class RowFilialPermissionSerializer(serializers.ModelSerializer):
    filial_id = serializers.IntegerField()
    row_id = serializers.IntegerField()
    filial = FilialSerializer(read_only=True)
    id = serializers.IntegerField(read_only=True)
    class Meta:
        model = RowFilialPermission
        fields = ['id','filial_id','can_edit','can_delete','row_id','filial']


    def create(self, validated_data):
        row = get_object_or_404(Row, id=validated_data['row_id'])
        filial = get_object_or_404(Filial,id=validated_data['filial_id'])
        if filial and row:
            permissions = RowFilialPermission.objects.create(filial=filial, row=row, **validated_data)
            return permissions


class CellLockSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    cell = CellSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    class Meta:
        model = CellLock
        fields = ['id','cell','user','locked_at']


class FileUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        max_length=1024,
        allow_empty_file=False,
        help_text='KEK'
    )
    name = serializers.CharField()
    # class Meta:
    #     fields = ['name','file']
    #     # model = File
    #     serializers.raise_errors_on_nested_writes = False


class ColumnPermissionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    can_view = serializers.BooleanField(required=False)
    can_edit = serializers.BooleanField(required=False)
    table = serializers.IntegerField()
    user = serializers.IntegerField()
    column = serializers.IntegerField()
    user_model = serializers.SerializerMethodField()

    class Meta:
        model = ColumnPermission
        fields = ['id','column','user','table','can_view','can_edit', 'user_model']

    def create(self, validated_data):
        permissions = ColumnPermission.objects.create(column=validated_data['column'],
                                                      user=validated_data['user'],
                                                      table=validated_data['table'],
                                                      can_view=validated_data['can_view'],
                                                      can_edit=validated_data['can_edit'],
                                                      )
        return permissions

    def get_user_model(self, obj):
        user = User.objects.get(id=obj.user)
        return UserSerializer(user).data


class ColumnFilialPermissionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    can_delete = serializers.BooleanField(required=False)
    can_edit = serializers.BooleanField(required=False)
    filial = FilialSerializer(read_only=True)
    filial_id = serializers.IntegerField(write_only=True)
    column = ColumnSerializer(read_only=True)
    column_id = serializers.IntegerField(write_only=True)
    class Meta:
        model = ColumnFilialPermission
        fields = ['id','column_id','column','filial_id','filial', 'can_delete', 'can_edit']

    def create(self, validated_data):
        column = get_object_or_404(Column,id=validated_data['column_id'])
        filial = get_object_or_404(Filial,id=validated_data['filial_id'])
        if filial and column:
            permissions = ColumnFilialPermission.objects.create(filial=filial, column=column, **validated_data)
            return permissions
        return None


class SelectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SelectType
        fields = '__all__'


class CellEditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CellEditLog
        fields = ['id', 'user', 'old_value', 'new_value', 'cell']
    user = serializers.SerializerMethodField()
    cell = serializers.SerializerMethodField()

    def get_user(self, obj):
        user = User.objects.get(id=obj.user_id)
        return user.last_name + " " + user.first_name

    def get_cell(self, obj):
        cell = Cell.objects.get(id=obj.cell_id)
        row = Row.objects.get(id=cell.row)
        column = Column.objects.get(id=cell.column)
        return numberToChar(column.order) + "" + str(row.order+1)
