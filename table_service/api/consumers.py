from channels.generic.websocket import AsyncJsonWebsocketConsumer
from tables.models import User


from api.helper import get_cell_by_id, create_cell_lock, get_cell_lock_by_cell, remove_cell_lock, get_user
from api.utils import send_cell_lock_update
from tables.models import Cell, CellLock
import json
import ast

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
        # todo remove all user locks
        await self.channel_layer.group_discard("cell_list_updates", self.channel_name)

    async def cell_updated(self, event):
        await self.send_json({
            "type": "cell_update",
            "id": event["data"]["id"],
            "entity": event["data"]["entity"],
        })

    async def receive(self, text_data):
        a = 1

class CellLockUpdatesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("cell_lock_updates", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("cell_lock_updates", self.channel_name)

    async def cell_lock_updated(self, event):
        await self.send_json({
            "type": "cell_lock_update",
            "id": event["data"]["id"],
            "entity": event["data"]["entity"],
        })

    async def receive(self, text_data):
        # {type: "remove\create", cell_id: 123, user_id: 1}
        data =ast.literal_eval(text_data)
        cell_id = data["cell_id"]
        cell = await get_cell_by_id(cell_id)
        lock_type = data['type']
        # user = self.scope["user"]
        user = await get_user(data['user_id'])
        if user.is_anonymous:
            await self.close()
            return

        if lock_type == "create":
            cell_lock = await create_cell_lock(cell, user)
            await send_cell_lock_update(cell_lock)
        elif lock_type == "remove":
            cell_lock = await get_cell_lock_by_cell(cell)
            if cell_lock:
                await remove_cell_lock(cell_lock)
