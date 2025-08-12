import os
from django.core.asgi import get_asgi_application
from django.urls import path

# Установка переменной окружения ДО всех импортов
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'table_service.settings')

# Получаем Django application
django_application = get_asgi_application()

# Импортируем Channels только после настройки Django
from channels.routing import ProtocolTypeRouter, URLRouter
import django
django.setup()  # Явная настройка Django

# Теперь безопасно импортируем consumers
from api.consumers import TableUpdatesConsumer

application = ProtocolTypeRouter({
    "http": django_application,
    "websocket": URLRouter([
        path("ws/table-updates/", TableUpdatesConsumer.as_asgi()),
    ]),
})