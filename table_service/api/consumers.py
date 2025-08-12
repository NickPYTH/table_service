from channels.generic.websocket import AsyncWebsocketConsumer
import json

class TableUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'You are now connected!'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        pass