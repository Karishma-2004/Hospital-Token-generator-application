from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from doctors.models import Hospital
from .queue import board_snapshot


class QueueConsumer(AsyncJsonWebsocketConsumer):
    """Public, read-only feed of one hospital's live queue board (token numbers only)."""

    async def connect(self):
        self.hospital_id = int(self.scope["url_route"]["kwargs"]["hospital_id"])
        self.group = None
        if not await self._hospital_is_approved():
            await self.close(code=4404)
            return
        self.group = f"queue_{self.hospital_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        board = await database_sync_to_async(board_snapshot)(self.hospital_id)
        await self.send_json({"type": "queue.update", "board": board})

    async def disconnect(self, code):
        if self.group:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        pass  # clients only listen

    async def queue_update(self, event):
        await self.send_json({"type": "queue.update", "board": event["board"]})

    @database_sync_to_async
    def _hospital_is_approved(self):
        return Hospital.objects.filter(id=self.hospital_id, status=Hospital.STATUS_APPROVED).exists()