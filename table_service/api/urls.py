from django.urls import path, include
from rest_framework.routers import DefaultRouter


from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='users')
router.register(r'filials', views.FilialViewSet, basename='filials')
router.register(r'departments', views.DepartmentViewSet, basename='departments')
router.register(r'employees', views.EmployeeViewSet, basename='employees')
router.register(r'profiles', views.ProfileViewSet, basename='profiles')
router.register(r'admins', views.AdminViewSet, basename='admins')
router.register(r'tables', views.TableListViewSet, basename='tables')
router.register(r'table', views.TableDetailViewSet, basename='table-detail')

router.register(r'cells', views.CellViewSet, basename='cells')

urlpatterns = [
    path('', include(router.urls)),
    path('get_current_user', views.CurrentUserView.as_view(), name='get_current_user')

]