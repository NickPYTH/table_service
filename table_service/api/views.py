from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework import viewsets, permissions, generics
from rest_framework.views import APIView
from .helper import get_table_ids_permissions, get_row_ids_permissions
from tables.models import Filial, Department, Employee, Profile, Admin, Table, Cell, Column, Row, RowPermission, \
    TablePermission, TableFilialPermission, RowFilialPermission
from .serializers import (
    UserSerializer,
    FilialSerializer,
    DepartmentSerializer,
    EmployeeSerializer,
    ProfileSerializer,
    AdminSerializer,
    ProfileCreateUpdateSerializer,
    TableListSerializer, TableDetailSerializer, CellSerializer, ColumnSerializer, RowSerializer,
    RowPermissionSerializer, TablePermissionsSerializer, TableFilialPermissionsSerializer, RowFilialPermissionSerializer
)
from .utils import send_table_update


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [permissions.IsAdminUser]


class FilialViewSet(viewsets.ModelViewSet):
    queryset = Filial.objects.all()
    serializer_class = FilialSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


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
        return self.request.user

# class CurrentUserView(APIView):
#     # permission_classes = (IsAuthenticated,)
#     def get(self, request):
#         print(request)
#         return JsonResponse({'user': 'kek'})

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
    queryset = Table.objects.all().prefetch_related(
            'rows__cells',
            'rows__cells__column',
        )
    def get_queryset(self):
        queryset = super().get_queryset()
        table_id = self.kwargs.get('pk')
        queryset = queryset.filter(table_id=table_id)
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

class ColumnViewSet(viewsets.ModelViewSet):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        table_id = self.request.query_params.get('table_id')
        if table_id:
            queryset = queryset.filter(table_id=table_id)
        return queryset

class RowDetailViewSet(viewsets.ModelViewSet):
    serializer_class = RowSerializer
    queryset = Row.objects.all()
    def get_queryset(self):
        queryset = super().get_queryset()
        row_id = self.kwargs.get('pk')
        queryset = queryset.filter(id=row_id)
        user = self.request.user
        all_permissions = get_row_ids_permissions(user)
        if all_permissions:
            queryset = queryset.filter(id__in=all_permissions)
        else:
            queryset = queryset.none()
        return queryset

class RowListViewSet(viewsets.ModelViewSet):
    serializer_class = RowSerializer
    queryset = Row.objects.all()
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        all_permissions = get_row_ids_permissions(user)
        if all_permissions:
            queryset = queryset.filter(id__in=all_permissions)
        else:
            queryset = queryset.none()
        table_id = self.request.query_params.get('table_id')
        if table_id and queryset:
            queryset = queryset.filter(table_id=table_id)
        return queryset



class TablePermissionViewSet(viewsets.ModelViewSet):
    serializer_class = TablePermissionsSerializer
    queryset = TablePermission.objects.all()

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
        if user_id:
            queryset = queryset.filter(user__id=user_id)
        if row_id:
            queryset = queryset.filter(row__id=row_id)
        return queryset


class RowFilialPermissionViewSet(viewsets.ModelViewSet):
    serializer_class = RowFilialPermissionSerializer
    queryset = RowFilialPermission.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        filial_id = self.request.query_params.get('filial_id')
        row_id = self.request.query_params.get('row_id')
        if filial_id:
            queryset = queryset.filter(filial__id=filial_id)
        if row_id:
            queryset = queryset.filter(row__id=row_id)

        return queryset

