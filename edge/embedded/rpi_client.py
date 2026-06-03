import cv2
import asyncio
import websockets
import json
import time
import argparse
from loguru import logger

class RPiClient:
    """
    Raspberry Pi / Embedded Edge Client for public.safe.
    """
    def __init__(self, node_id: str, server_url: str, camera_index: int = 0):
        self.node_id = node_id
        self.server_url = f"{server_url}/ws/node/{node_id}"
        self.camera_index = camera_index
        self.cap = None

    async def stream(self):
        while True:
            try:
                logger.info(f"Connecting to {self.server_url}...")
                async with websockets.connect(self.server_url) as ws:
                    logger.info("Connected! Starting capture...")
                    self.cap = cv2.VideoCapture(self.camera_index)
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

                    while self.cap.isOpened():
                        ret, frame = self.cap.read()
                        if not ret: break

                        # Encode JPEG
                        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                        
                        # Send binary
                        await ws.send(buffer.tobytes())
                        
                        # Target ~15-20 FPS to reduce bandwidth
                        await asyncio.sleep(1/20)

            except Exception as e:
                logger.error(f"Stream error: {e}. Retrying in 5s...")
                if self.cap: self.cap.release()
                await asyncio.sleep(5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", default="rpi_node_01")
    parser.add_argument("--server", default="ws://localhost:8000")
    args = parser.parse_args()

    client = RPiClient(args.id, args.server)
    asyncio.run(client.stream())
