from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from api.views import CurrentUserView
from . import views

urlpatterns = [
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', views.table_list, name='table_list'),
    path('create/', views.create_table, name='create_table'),
    path('<int:pk>/', views.table_detail, name='table_detail'),
    path('<int:pk>/delete_table', views.delete_table, name='delete_table'),
    path('<int:pk>/add_column/', views.add_column, name='add_column'),
    path('<int:pk>/add_row/', views.add_row, name='add_row'),
    path('<int:table_pk>/delete_column/<int:column_pk>/', views.delete_column, name='delete_column'),
    path('<int:table_pk>/delete_row/<int:row_pk>/', views.delete_row, name='delete_row'),
    path('<int:table_pk>/edit_row/<int:row_pk>/', views.edit_row, name='edit_row'),
    path('shared/', views.shared_tables_list, name='shared_tables_list'),
    path('shared/<str:share_token>/', views.shared_table_view, name='shared_table_view'),
    path('shared/<str:share_token>/revoke_redact/', views.revoke_redact_rows, name='revoke_redact_rows'),
    path('<int:table_pk>/<int:row_pk>/row_permissions/', views.manage_row_permissions, name='manage_row_permissions'),
    path('<int:table_pk>/table_permissions/', views.manage_table_permissions, name='manage_table_permissions'),
    path('<int:table_pk>/unlock_filial/', views.unlock_filial_table, name='unlock_filial_table'),
    path('api/unlock_row/<int:row_pk>/', views.unlock_row_api, name='unlock_row_api'),
    path('admins/', views.manage_admins, name='manage_admins'),
    path('<int:table_pk>/export/', views.export_table, name='export_table'),
]
