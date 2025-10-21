from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer

from api.serializers import TableDetailSerializer, CellSerializer, CellLockSerializer


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
