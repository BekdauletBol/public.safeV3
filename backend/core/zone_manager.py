import numpy as np
import cv2
from datetime import datetime
from typing import List, Dict, Tuple
from backend.config import settings
from loguru import logger

class ZoneManager:
    """
    Adaptive Zone Geometry (AZG) - (Patent-Critical).
    Morphs danger zones based on time-of-day, weather, and crowd density.
    """
    def __init__(self):
        self.base_zones: Dict[str, np.ndarray] = {} # node_id -> polygon
        self.weather_condition: str = "clear" # clear, rain, fog, snow
        self.pedestrian_counts: Dict[str, List[int]] = {} # node_id -> last 60s history

    def set_base_zone(self, node_id: str, polygon: List[Tuple[float, float]]):
        self.base_zones[node_id] = np.array(polygon, dtype=np.int32)
        logger.info(f"Base zone set for node {node_id}")

    def get_active_zone(self, node_id: str) -> np.ndarray:
        if node_id not in self.base_zones:
            return np.array([], dtype=np.int32)
        
        polygon = self.base_zones[node_id]
        expansion_factor = 1.0
        
        # 1. Time-of-day modifier
        hour = datetime.now().hour
        if settings.NIGHT_MODE_START <= hour or hour < settings.NIGHT_MODE_END:
            expansion_factor += 0.25 # Night mode (+25%)
        elif settings.RUSH_HOUR_MORNING[0] <= hour < settings.RUSH_HOUR_MORNING[1] or \
             settings.RUSH_HOUR_EVENING[0] <= hour < settings.RUSH_HOUR_EVENING[1]:
            expansion_factor += 0.15 # Rush hour (+15%)

        # 2. Weather modifier
        if self.weather_condition in ['rain', 'fog', 'snow']:
            expansion_factor += 0.20 # Bad weather (+20%)

        # 3. Density modifier
        avg_count = np.mean(self.pedestrian_counts.get(node_id, [0])[-60:])
        if avg_count > 10:
            expansion_factor += 0.10 # High density (+10%)

        if expansion_factor == 1.0:
            return polygon

        # Scale polygon vertices outward from centroid
        M = cv2.moments(polygon)
        if M["m00"] == 0: return polygon
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        
        expanded_poly = []
        for x, y in polygon:
            ex = cx + (x - cx) * expansion_factor
            ey = cy + (y - cy) * expansion_factor
            expanded_poly.append([ex, ey])
            
        return np.array(expanded_poly, dtype=np.int32)

    def update_density(self, node_id: str, count: int):
        if node_id not in self.pedestrian_counts:
            self.pedestrian_counts[node_id] = []
        self.pedestrian_counts[node_id].append(count)
        if len(self.pedestrian_counts[node_id]) > 60:
            self.pedestrian_counts[node_id].pop(0)

zone_manager = ZoneManager()
