import ast

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from api.helper import get_cell_by_id, create_cell_lock, get_cell_lock_by_cell, remove_cell_lock, get_user, \
    update_cell_by_id, reorder_columns, send_to_demon_proxy
from api.utils import send_cell_lock_update, send_cell_lock_remove, get_user_from_session_id, register_user, \
    un_register_user


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
        #user = await get_user_from_session_id(self.scope.get('cookies').get('sessionid'))
        #table_id = bytes.decode(self.scope.get('query_string')).split('=')[1]
        #await register_user(user, table_id)
        await self.accept()
        await self.channel_layer.group_add("cell_list_updates", self.channel_name)

    async def disconnect(self, close_code):
        # todo remove all user locks
        user = await get_user_from_session_id(self.scope.get('cookies').get('sessionid'))
        table_id = bytes.decode(self.scope.get('query_string')).split('=')[1]
        await un_register_user(user, table_id)
        await self.channel_layer.group_discard("cell_list_updates", self.channel_name)

    async def cell_updated(self, event):
        await self.send_json({
            "type": "cell_update",
            "id": event["data"]["id"],
            "entity": event["data"]["entity"],
        })

    async def receive(self, text_data):
        # {type: "update", cell_id: 123, value: "some val"}
        data = ast.literal_eval(text_data)
        if data["type"] == 'column_reorder':
           await reorder_columns(data["table_id"], data["old_index"], data["new_index"])
        else:
            cell_id = data["cell_id"]
            user_id = data["user_id"]
            await update_cell_by_id(cell_id, data["value"], user_id)


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

    async def cell_lock_removed(self, event):
        await self.send_json({
            "type": "cell_lock_remove",
            "id": event["data"]["id"],
            "entity": event["data"]["entity"],
        })

    async def receive(self, text_data):
        # {type: "remove\create", cell_id: 123, user_id: 1}
        data = ast.literal_eval(text_data)
        cell_id = data["cell_id"]
        cell = await get_cell_by_id(cell_id)
        lock_type = data['type']
        # user = self.scope["user"]
        user = await get_user(data['user_id'])
        if user.is_anonymous:
            await self.close()
            return

        if lock_type == "create":
            # Перед созданием блокировки, удаляем все другие блокировки пользователя
            cell_lock = await create_cell_lock(cell, user)
            await send_cell_lock_update(cell_lock)
        elif lock_type == "remove":
            cell_lock = await get_cell_lock_by_cell(cell)
            if cell_lock:
                await send_cell_lock_remove(cell_lock)
                await remove_cell_lock(cell_lock)


class DemonConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("demon", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("demon", self.channel_name)

    async def send_signal(self, event):
        await self.send_json({
            "type": "demon",
            "username": event['data']['username'],
            "path": event['data']['path'],
        })

    async def receive(self, text_data):
        # {username: 123, path: 1}
        data = ast.literal_eval(text_data)
        username = data["username"]
        path = data["path"]
        await send_to_demon_proxy(username, path)
