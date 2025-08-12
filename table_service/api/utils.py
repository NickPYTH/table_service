from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from api.serializers import TableDetailSerializer, CellSerializer


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
                "message": "Cell list updated",
            }
        }
    )

