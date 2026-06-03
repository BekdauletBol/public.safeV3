import csv
import os
from datetime import datetime
from backend.config import settings

class TelemetryLogger:
    """
    Logs session telemetry to CSV for analytics.
    """
    def __init__(self):
        self.log_path = settings.TELEMETRY_PATH
        self._ensure_header()

    def _ensure_header(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'node_id', 'track_id', 'threat_score', 'ttc_ms', 'status'])

    def log_detection(self, node_id: str, track_id: int, threat_score: float, ttc_ms: float, status: str):
        with open(self.log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                node_id,
                track_id,
                f"{threat_score:.4f}",
                f"{ttc_ms:.2f}",
                status
            ])

telemetry_logger = TelemetryLogger()
