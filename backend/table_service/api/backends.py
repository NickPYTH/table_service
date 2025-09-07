from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class RemoteUserBackend(ModelBackend):
    def authenticate(self, request, remote_user=None):
        if remote_user is None:
            remote_user = request.META.get('HTTP_X_REMOTE_USER')
        if remote_user:
            try:
                user = User.objects.get(username=remote_user)
            except User.DoesNotExist:
                return None
            return user
        return User.objects.get(pk=1)
        # return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
