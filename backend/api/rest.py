from fastapi import APIRouter, HTTPException
from typing import List
from backend.models.schemas import ZoneConfig, NodeStatus
from backend.core.zone_manager import zone_manager
from backend.core.mesh_coordinator import mesh_coordinator

router = APIRouter()

@router.get("/api/nodes", response_model=List[NodeStatus])
async def get_nodes():
    nodes = []
    for node_id, node in mesh_coordinator.nodes.items():
        nodes.append(NodeStatus(
            node_id=node_id,
            status="active" if node.connection else "idle",
            lat=node.lat,
            lon=node.lon,
            sensitivity=node.sensitivity_mode
        ))
    return nodes

@router.put("/api/zones/{node_id}")
async def update_zone(node_id: str, config: ZoneConfig):
    zone_manager.set_base_zone(node_id, config.polygon)
    return {"status": "success"}

@router.post("/api/weather")
async def update_weather(condition: str):
    if condition not in ['clear', 'rain', 'fog', 'snow']:
        raise HTTPException(status_code=400, detail="Invalid weather condition")
    zone_manager.weather_condition = condition
    return {"status": "success", "condition": condition}

@router.get("/health")
async def health():
    return {"status": "ok", "nodes": len(mesh_coordinator.nodes)}
