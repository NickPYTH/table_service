from rest_framework import serializers
from django.contrib.auth.models import User
from tables.models import Filial, Employee, Department, Profile, Admin, Table, Column, Cell, Row


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class FilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filial
        fields = '__all__'
        extra_kwargs = {
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
        fields = ['id', 'name', 'order', 'data_type']



class RowSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Row
        fields = ['id', 'order', 'created_by']


class CellSerializer(serializers.ModelSerializer):
    row = RowSerializer(read_only=True)
    column = ColumnSerializer(read_only=True)
    value = serializers.SerializerMethodField()

    class Meta:
        model = Cell
        fields = ['id', 'row', 'column', 'value']

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



class TableSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField()
    created_at = serializers.SerializerMethodField()


    class Meta:
        model = Table
        fields = ['id','title','owner','created_at','share_token']

    def get_created_at(self, obj):
        return int(obj.created_at.timestamp()) * 1000


# {
# table:{}
# cells:[
# {id row: {}, column: {}, type:"str",value:"some value"}
# ]
# }