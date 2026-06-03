import asyncio
from typing import Dict, Optional
from loguru import logger
from backend.config import settings

class QueueManager:
    """
    Manages LIFO queues for each connected edge node.
    Ensures only the most recent frame is processed to minimize latency.
    """
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.metrics: Dict[str, Dict] = {}

    async def get_queue(self, node_id: str) -> asyncio.Queue:
        if node_id not in self.queues:
            self.queues[node_id] = asyncio.Queue(maxsize=settings.LIFO_QUEUE_MAX)
            self.metrics[node_id] = {"dropped": 0, "processed": 0}
            logger.info(f"Initialized LIFO queue for node: {node_id}")
        return self.queues[node_id]

    async def put_frame(self, node_id: str, frame: bytes):
        queue = await self.get_queue(node_id)
        if queue.full():
            try:
                queue.get_nowait()
                self.metrics[node_id]["dropped"] += 1
            except asyncio.QueueEmpty:
                pass
        await queue.put(frame)

    async def get_frame(self, node_id: str) -> Optional[bytes]:
        queue = await self.get_queue(node_id)
        try:
            frame = await queue.get()
            self.metrics[node_id]["processed"] += 1
            return frame
        except Exception as e:
            logger.error(f"Error getting frame for node {node_id}: {e}")
            return None

    def get_health(self, node_id: str) -> Dict:
        return self.metrics.get(node_id, {"dropped": 0, "processed": 0})

queue_manager = QueueManager()
