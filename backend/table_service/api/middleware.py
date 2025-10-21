from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from urllib.parse import parse_qs

class RemoteUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        pass


class WebSocketRemoteUserMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Ленивый импорт User, чтобы избежать AppRegistryNotReady
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # 1. Извлекаем заголовки из scope (WebSocket-подключение)
        headers = dict(scope.get("headers", []))

        # 2. Ищем заголовок 'x-remote-user' (в Channels они в bytes)
        remote_user = None
        for header_name, header_value in headers.items():
            if header_name.lower() == b'x-remote-user':
                remote_user = header_value.decode()
                break

        # 3. Аутентифицируем пользователя
        if remote_user:
            try:
                scope["user"] = await User.objects.aget(username=remote_user)
            except User.DoesNotExist:
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


class RemoteUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        pass
