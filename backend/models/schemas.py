from pydantic import BaseModel
from typing import List, Tuple, Optional

class Point(BaseModel):
    x: float
    y: float

class ZoneConfig(BaseModel):
    node_id: str
    polygon: List[Tuple[float, float]]

class NodeStatus(BaseModel):
    node_id: str
    status: str
    lat: float
    lon: float
    sensitivity: str

class ViolationEvent(BaseModel):
    timestamp: str
    node_id: str
    threat_score: float
    ttc_ms: float
    violation_type: str # CURRENT, PREDICTED
