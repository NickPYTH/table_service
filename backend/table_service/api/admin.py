from django.contrib import admin
from tables.models import (Table, Column, Cell, Row, TablePermission, TableFilialPermission,
                           RowFilialPermission, Filial, Department, Employee, Profile,
                           Admin, RowLock, CellLock, TableFilialLock, RowPermission)

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    pass

@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    pass

@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    pass

@admin.register(Row)
class RowAdmin(admin.ModelAdmin):
    pass

@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    pass

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    pass

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    pass

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    pass

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    pass

@admin.register(TablePermission)
class TablePermissionAdmin(admin.ModelAdmin):
    pass

@admin.register(TableFilialPermission)
class TableFilialPermissionAdmin(admin.ModelAdmin):
    pass

@admin.register(RowFilialPermission)
class RowFilialPermissionAdmin(admin.ModelAdmin):
    pass
@admin.register(RowPermission)
class RowPermissionAdmin(admin.ModelAdmin):
    pass

    


@admin.register(RowLock)
class RowLockAdmin(admin.ModelAdmin):
    pass
@admin.register(CellLock)
class CellLockAdmin(admin.ModelAdmin):
    pass
@admin.register(TableFilialLock)
class TableFilialLockAdmin(admin.ModelAdmin):
    pass



