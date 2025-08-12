from datetime import datetime

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from tables.models import Filial, Employee, Department, Profile, Admin, Table, Column, Cell, Row, RowPermission, \
    TablePermission, TableFilialPermission, RowFilialPermission
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

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']



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
        cells = [Cell(row=row, column=column) for row in rows]
        Cell.objects.bulk_create(cells)
        return column



class RowSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    order = serializers.IntegerField(read_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Row
        fields = ['id', 'order', 'created_by', "table"]

    def create(self, validated_data):
        table = validated_data.pop('table')
        owner = self.context['request'].user
        order = Row.objects.count()
        row = Row.objects.create(table=table, created_by=owner, order=order)
        RowPermission.objects.create(user=owner, row=row)
        columns = table.columns.all()
        cells = [Cell(row=row,column=column) for column in columns]
        Cell.objects.bulk_create(cells)
        return row


class CellSerializer(serializers.ModelSerializer):
    row = RowSerializer()
    column = ColumnSerializer()
    value = serializers.SerializerMethodField(read_only=True)
    write_value = serializers.CharField(write_only=True, allow_null=True, required=False)

    class Meta:
        model = Cell
        fields = ['id', 'row', 'column', 'value','write_value']

    def get_value(self, obj):
        if obj.column.data_type == Column.ColumnType.TEXT:
            return obj.text_value
        elif obj.column.data_type == Column.ColumnType.INTEGER:
            return obj.integer_value
        elif obj.column.data_type == Column.ColumnType.FLOAT:
            return obj.float_value
        elif obj.column.data_type == Column.ColumnType.BOOLEAN:
            return obj.boolean_value
        elif obj.column.data_type == Column.ColumnType.DATE:
            return obj.date_value.isoformat() if obj.date_value else None
        return None

    def validate(self, data):
        write_value = data.get('write_value')
        if write_value is not None:
            column = self.instance.column if self.instance else data.get('column')
            if not column:
                raise serializers.ValidationError("Column is required")
            try:
                if column.data_type == Column.ColumnType.TEXT:
                    data['text_value'] = str(write_value)
                elif column.data_type == Column.ColumnType.INTEGER:
                    data['integer_value'] = int(write_value)
                elif column.data_type == Column.ColumnType.FLOAT:
                    data['float_value'] = float(write_value)
                elif column.data_type == Column.ColumnType.BOOLEAN:
                    data['boolean_value'] = write_value.lower() in ['true', '1', 'yes']
                elif column.data_type == Column.ColumnType.DATE:
                    data['date_value'] = datetime.strptime(write_value, '%Y-%m-%d').date()
            except (ValueError, TypeError) as e:
                raise serializers.ValidationError(f"Invalid value for {column.data_type}: {str(e)}")
        return data

    def create(self, validated_data):
        validated_data.pop('write_value', None)
        return  super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('write_value', None)
        return super().update(instance, validated_data)




class TableDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    created_at = serializers.SerializerMethodField()
    cells = serializers.SerializerMethodField()
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Table
        fields = ['id','title','owner','created_at','share_token', 'cells']
        extra_kwargs = {
            'share_token': {'read_only': True},
            'created_at': {'read_only': True},
            'cells': {'read_only': True},
        }

    def update(self, request, pk=None):
        table = Table.objects.get(pk=request.id)
        table.title = pk.get('title')
        table.save()
        return table


    def get_created_at(self, obj):
        return int(obj.created_at.timestamp()) * 1000

    def get_cells(self, obj):
        return [
            {
                'id':cell.id,
                'row':RowSerializer(cell.row, read_only=True).data,
                'column':ColumnSerializer(cell.column, read_only=True).data,
                'value':CellSerializer().get_value(cell),
            }
            for cell in Cell.objects.filter(row__table=obj)
        ]


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
    class Meta:
        model = TablePermission
        fields = ['id','user_id','can_view','table']

    def create(self, validated_data):
        user = get_object_or_404(User,id=validated_data['user_id'])
        if user:
            permissions = TablePermission.objects.create(user=user, **validated_data)
            return permissions


class TableFilialPermissionsSerializer(serializers.ModelSerializer):
    filial_id = serializers.IntegerField()
    class Meta:
        model = TableFilialPermission
        fields = ['id','table','filial_id','can_view']

    def create(self, validated_data):
        filial = get_object_or_404(Filial,id=validated_data['filial_id'])
        if filial:
            permissions = TableFilialPermission.objects.create(filial=filial, **validated_data)
            return permissions




class RowPermissionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField()
    row_id = serializers.IntegerField()
    class Meta:
        model = RowPermission
        fields = ['row_id','user_id','can_edit','can_delete']

    def create(self, validated_data):
        row = get_object_or_404(Row,id=validated_data['row_id'])
        user = get_object_or_404(User,id=validated_data['user_id'])
        if user and row:
            permissions = RowPermission.objects.create(row=row, user=user, **validated_data)
            return permissions


class RowFilialPermissionSerializer(serializers.ModelSerializer):
    filial_id = serializers.IntegerField()
    row_id = serializers.IntegerField()
    class Meta:
        model = RowFilialPermission
        fields = ['filial_id','can_edit','can_delete','row_id']


    def create(self, validated_data):
        row = get_object_or_404(Row, id=validated_data['row_id'])
        filial = get_object_or_404(Filial,id=validated_data['filial_id'])
        if filial and row:
            permissions = RowFilialPermission.objects.create(filial=filial, row=row, **validated_data)
            return permissions



