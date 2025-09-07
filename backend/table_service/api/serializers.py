from datetime import datetime

from django.contrib.admin import action
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from tables.models import Filial, Employee, Department, Profile, Admin, Table, Column, Cell, Row, RowPermission, \
    TablePermission, TableFilialPermission, RowFilialPermission, CellLock, ColumnPermission, ColumnFilialPermission
from datetime import datetime

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def notify_table_update():
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "table_updates",
        {
            "type": "table.updated",
            "message": "Table data updated",
        }
    )

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
    class Meta:
        model = Column
        fields = ['id', 'name', 'order', 'data_type', "table"]

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
        return column


class CellSerializer(serializers.ModelSerializer):
    #row = RowSerializer()
    #column = ColumnSerializer()
    #value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Cell
        fields = ['id', 'column', 'row', 'value']


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
        for cell in Cell.objects.filter(row=obj.id):
            cell_list.append(CellSerializer(cell).data)
        return cell_list

    def create(self, validated_data):
        table = validated_data.pop('table')
        owner = self.context['request'].user
        order = Row.objects.count()
        row = Row.objects.create(table=table, created_by=owner, order=order)
        # Накидываем права на новую строку основываясь на пользователях с правами на редактирование таблицы
        for table_permission in TablePermission.objects.filter(table=table, can_edit=True):
            RowPermission.objects.create(user=table_permission.user.id, row=row.id, table=table.id).save()
        # -----
        columns = table.columns.all()
        cells = [Cell(row=row.id,column=column.id, table_id=table.id) for column in columns]
        Cell.objects.bulk_create(cells)
        return row


class TableDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    created_at = serializers.SerializerMethodField()
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Table
        fields = ['id','title','owner','created_at','share_token']
        extra_kwargs = {
            'share_token': {'read_only': True},
            'created_at': {'read_only': True},
        }

    def update(self, request, pk=None):
        table = Table.objects.get(pk=request.id)
        table.title = pk.get('title')
        table.save()
        return table

    def get_created_at(self, obj):
        return int(obj.created_at.timestamp()) * 1000


class TableListSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields  = ['id','title','owner','created_at','share_token']
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
        table = Table.objects.create(owner=owner, title=title, created_at=created_at)
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
            return permissions

    def update(self, request, pk=None):
        table_permission = TablePermission.objects.get(pk=request.id)
        table_permission.can_edit = pk.get('can_edit')
        table_permission.save()
        row_permissions = []
        for row_permission in RowPermission.objects.filter(user=request.user_id, table=request.table_id):
            row_permission.can_edit = pk.get('can_edit')
            row_permissions.append(row_permission)
        RowPermission.objects.bulk_update(row_permissions, fields=['can_edit'])
        return table_permission


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
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    column = ColumnSerializer(read_only=True)
    column_id = serializers.IntegerField(write_only=True)
    class Meta:
        model = ColumnPermission
        fields = ['id','column_id','user_id','user','column','can_view','can_edit']

    def create(self, validated_data):
        column = get_object_or_404(Column,id=validated_data['column_id'])
        user = get_object_or_404(User,id=validated_data['user_id'])
        if user and column:
            permissions = ColumnPermission.objects.create(column=column, user=user, **validated_data)
            return permissions
        return None


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




