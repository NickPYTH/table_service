from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile, Employee, Filial, Department


# 1. Инлайн для Profile (чтобы редактировать вместе с User)
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профили'
    fk_name = 'user'
    fields = ('employee',)  # Поля, которые хотим редактировать


# 2. Кастомный UserAdmin с инлайном Profile
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_employee', 'is_staff')
    list_select_related = ('profile', 'profile__employee')

    def get_employee(self, instance):
        return instance.profile.employee if hasattr(instance, 'profile') else None
    get_employee.short_description = 'Сотрудник'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


# 3. Админка для Employee
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'tabnumber', 'full_name', 'post_name', 'filial_info', 'department_info', 'set_date', 'end_date')
    list_filter = ('id_filial', 'id_department')
    search_fields = ('firstname', 'secondname', 'lastname', 'tabnumber')

    def full_name(self, obj):
        return f"{obj.secondname} {obj.firstname} {obj.lastname}"

    full_name.short_description = 'ФИО'

    def filial_info(self, obj):
        if obj.id_filial:
            filial = Filial.objects.filter(id=obj.id_filial).first()
            return filial.name if filial else obj.id_filial
        return "-"

    filial_info.short_description = 'Филиал'

    def department_info(self, obj):
        if obj.id_department:
            department = Department.objects.filter(id=obj.id_department).first()
            return department.name if department else obj.id_department
        return "-"

    department_info.short_description = 'Отдел'


# 4. Админка для Filial
class FilialAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'short_name', 'boss', 'set_date', 'end_date')
    search_fields = ('name', 'short_name', 'boss')
    list_filter = ('set_date', 'end_date')


# 5. Админка для Department
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'short_name', 'id_filial', 'id_parent')
    list_filter = ('id_filial',)
    search_fields = ('name', 'short_name')


# Регистрация моделей
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Filial, FilialAdmin)
admin.site.register(Department, DepartmentAdmin)
