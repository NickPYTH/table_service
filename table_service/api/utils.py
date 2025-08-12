from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from api.serializers import TableDetailSerializer


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