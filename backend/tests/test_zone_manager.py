import pytest
import numpy as np
from backend.core.zone_manager import zone_manager

def test_zone_expansion():
    base_poly = [[100, 100], [200, 100], [200, 200], [100, 200]]
    zone_manager.set_base_zone("test_node", base_poly)
    
    # Clear weather
    zone_manager.weather_condition = "clear"
    poly1 = zone_manager.get_active_zone("test_node")
    
    # Bad weather
    zone_manager.weather_condition = "rain"
    poly2 = zone_manager.get_active_zone("test_node")
    
    # poly2 should be larger than poly1
    # Simple area check
    area1 = cv2.contourArea(poly1) if 'cv2' in globals() else 10000
    import cv2
    area1 = cv2.contourArea(poly1)
    area2 = cv2.contourArea(poly2)
    
    assert area2 > area1
