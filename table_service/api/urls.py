from xml.etree.ElementInclude import include

from django.urls import path
from rest_framework.routers import DefaultRouter


from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'filials', views.FilialViewSet)
router.register(r'departments', views.DepartmentViewSet)
router.register(r'employees', views.EmployeeViewSet)
router.register(r'profiles', views.ProfileViewSet)
router.register(r'admins', views.AdminViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('get_current_user', views.CurrentUserView.as_view(), name='get_current_user')

]