from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from api.consumers import TableUpdatesConsumer  # Или правильный путь к вашему consumer

application = ProtocolTypeRouter({
    "websocket": URLRouter([
        re_path(r"^ws/table-updates/$", TableUpdatesConsumer.as_asgi()),
    ]),
})