from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer

from api.serializers import TableDetailSerializer, CellSerializer, CellLockSerializer
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.utils import timezone

from tables.models import TableUserOnline, Table


@sync_to_async(thread_sensitive=False)
def get_user_from_session_id(session_id):
    try:
        session = Session.objects.get(session_key=session_id)
        session_data = session.get_decoded()

        # Получаем ID пользователя из сессии
        user_id = session_data.get('_auth_user_id')

        if user_id:
            return User.objects.get(id=user_id)
    except (Session.DoesNotExist, User.DoesNotExist):
        return None

@sync_to_async(thread_sensitive=False)
def register_user(user, table_id):
    table = Table.objects.get(id=table_id)
    if TableUserOnline.objects.filter(user=user, table=table).count() == 0:
        online_record = TableUserOnline(user=user, table=table)
        online_record.save()

@sync_to_async(thread_sensitive=False)
def un_register_user(user, table_id):
    table = Table.objects.get(id=table_id)
    TableUserOnline.objects.filter(user=user, table=table).delete()


def send_table_update(instance=None):
    channel_layer = get_channel_layer()

    serializer = TableDetailSerializer(instance)
    serialized_data = serializer.data

    async_to_sync(channel_layer.group_send)(
        "table_list_updates",
        {
            "type": "table.updated",
            "data": {
                "id": instance.id if instance else None,
                "entity": serialized_data,
                "message": "Table list updated",
            }
        }
    )

def send_table_create(instance=None):
    channel_layer = get_channel_layer()

    serializer = TableDetailSerializer(instance)
    serialized_data = serializer.data

    async_to_sync(channel_layer.group_send)(
        "table_list_updates",
        {
            "type": "table.created",
            "data": {
                "id": instance.id if instance else None,
                "entity": serialized_data,
                "message": "Table list created",
            }
        }
    )

def send_cell_update(instance=None):
    channel_layer = get_channel_layer()

    serializer = CellSerializer(instance)
    serialized_data = serializer.data

    async_to_sync(channel_layer.group_send)(
        "cell_list_updates",
        {
            "type": "cell.updated",
            "data": {
                "id": instance.id if instance else None,
                "entity": serialized_data,
                "message": "Cell updated",
            }
        }
    )

@sync_to_async(thread_sensitive=False)
def send_cell_lock_update(instance=None):
    channel_layer = get_channel_layer()

    serializer = CellLockSerializer(instance)
    serialized_data = serializer.data

    async_to_sync(channel_layer.group_send)(
        "cell_lock_updates",
        {
            "type": "cell.lock.updated",
            "data": {
                "id": instance.id if instance else None,
                "entity": serialized_data,
                "message": "Cell lock updated",
            }
        }
    )

@sync_to_async(thread_sensitive=False)
def send_cell_lock_remove(instance=None):
    channel_layer = get_channel_layer()

    serializer = CellLockSerializer(instance)
    serialized_data = serializer.data

    async_to_sync(channel_layer.group_send)(
        "cell_lock_updates",
        {
            "type": "cell.lock.removed",
            "data": {
                "id": instance.id if instance else None,
                "entity": serialized_data,
                "message": "Cell lock removed",
            }
        }
    )

def send_to_demon(username, path):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "demon",
        {
            "type": "send.signal",
            "data": {
                "username": username,
                "path": path,
            }
        }
    )
