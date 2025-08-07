from django.urls import path

from api.views import CurrentUserView

urlpatterns = [
    path('get_current_user', CurrentUserView.as_view(), name='get_current_user'),
]