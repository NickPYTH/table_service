from channels.generic.websocket import AsyncJsonWebsocketConsumer


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

    async def table_created(self, event):
        await self.send_json({
            "type": "table_create",
            "id": event["data"]["id"],
            "entity": event["data"]["entity"],
        })


class CellUpdatesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("cell_list_updates", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("cell_list_updates", self.channel_name)

    async def cell_updated(self, event):
        await self.send_json({
            "type": "cell_update",
            "id": event["data"]["id"],
            "entity": event["data"]["entity"],
        })

    async def receive(self, text_data):
        a = 1
