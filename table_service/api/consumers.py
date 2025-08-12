from channels.generic.websocket import AsyncJsonWebsocketConsumer

from api.serializers import TableDetailSerializer


class TableUpdatesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("table_list_updates", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("table_list_updates", self.channel_name)

    async def table_updated(self, event):
        await self.send_json({
            "type": "table_update",
            "id": event["data"]["id"],
            "entity": event["data"]["entity"],
        })