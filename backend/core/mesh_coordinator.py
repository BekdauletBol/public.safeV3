import asyncio
import time
from typing import Dict, List, Optional, Tuple
from haversine import haversine, Unit
from loguru import logger
from backend.config import settings

class NodeInfo:
    def __init__(self, node_id: str, lat: float, lon: float, connection=None):
        self.node_id = node_id
        self.lat = lat
        self.lon = lon
        self.connection = connection
        self.sensitivity_mode: str = "NORMAL" # NORMAL, HEIGHTENED
        self.pre_alert_expiry: float = 0

class MeshCoordinator:
    """
    Mesh Alert Propagation (MAP) - (Patent-Critical).
    Coordinates alerts across neighboring edge nodes.
    """
    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}

    def register_node(self, node_id: str, lat: float, lon: float, connection=None):
        self.nodes[node_id] = NodeInfo(node_id, lat, lon, connection)
        logger.info(f"Node {node_id} registered at ({lat}, {lon})")

    async def propagate_alert(self, origin_node_id: str, threat_direction: Tuple[float, float]):
        if origin_node_id not in self.nodes: return
        
        origin = self.nodes[origin_node_id]
        neighbors = self.get_neighbors(origin_node_id, settings.MESH_RADIUS_METERS)
        
        for neighbor in neighbors:
            # Estimate arrival time (1.4 m/s average walking speed)
            dist_km = haversine((origin.lat, origin.lon), (neighbor.lat, neighbor.lon))
            dist_m = dist_km * 1000
            arrival_ms = (dist_m / 1.4) * 1000
            
            await self.send_pre_alert(neighbor.node_id, origin_node_id, arrival_ms)

    def get_neighbors(self, node_id: str, radius_m: float) -> List[NodeInfo]:
        if node_id not in self.nodes: return []
        origin = self.nodes[node_id]
        
        neighbors = []
        for other_id, other_node in self.nodes.items():
            if other_id == node_id: continue
            
            dist_km = haversine((origin.lat, origin.lon), (other_node.lat, other_node.lon))
            if dist_km * 1000 <= radius_m:
                neighbors.append(other_node)
        return neighbors

    async def send_pre_alert(self, target_id: str, origin_id: str, arrival_ms: float):
        neighbor = self.nodes[target_id]
        neighbor.sensitivity_mode = "HEIGHTENED"
        neighbor.pre_alert_expiry = time.time() + (arrival_ms + 5000) / 1000.0
        logger.info(f"Pre-alert sent to {target_id} from {origin_id}. HEIGHTENED sensitivity for {arrival_ms/1000:.1f}s")
        
        # In a real system, this would push a message to the target node's connection
        # if neighbor.connection:
        #    await neighbor.connection.send_json({"type": "PRE_ALERT", ...})

    def get_sensitivity(self, node_id: str) -> float:
        """Returns the confidence threshold based on sensitivity mode."""
        node = self.nodes.get(node_id)
        if not node: return settings.CONFIDENCE_THRESHOLD
        
        if node.sensitivity_mode == "HEIGHTENED" and time.time() < node.pre_alert_expiry:
            return 0.20 # Lower threshold for heightened sensitivity
        
        # Reset if expired
        if node.sensitivity_mode == "HEIGHTENED":
            node.sensitivity_mode = "NORMAL"
        return settings.CONFIDENCE_THRESHOLD

mesh_coordinator = MeshCoordinator()
