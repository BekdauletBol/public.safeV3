import pytest
import numpy as np
from backend.core.detector import Detection
from backend.core.footpoint_pip import footpoint_pip

def test_static_violation():
    zone = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.int32)
    # Detection inside zone
    det = Detection(bbox=[10, 10, 50, 90], confidence=0.9, track_id=1)
    res = footpoint_pip.check_violation(det, zone)
    assert res.is_current_violation == True

def test_predictive_violation():
    zone = np.array([[100, 0], [200, 0], [200, 200], [100, 200]], dtype=np.int32)
    # Detection outside, but moving toward zone
    det = Detection(bbox=[50, 50, 80, 150], confidence=0.9, track_id=1)
    det.velocity_vector = np.array([10.0, 0.0]) # Moving right 10px/frame
    
    res = footpoint_pip.check_violation(det, zone, lookahead_frames=5)
    # After 5 frames, x will be ~80 + 50 = 130 (inside)
    assert res.is_current_violation == False
    assert res.is_predicted_violation == True
