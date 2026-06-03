# public.safe v3.0
## Intelligent Pedestrian Safety Network

public.safe is a distributed edge-AI pedestrian safety network designed for B2G (Business-to-Government) city-wide deployments. It utilizes a 3-tier architecture to detect, predict, and propagate pedestrian safety threats in real-time.

### Core Innovations (Patent-Critical)
1. **Predictive Threat Scoring (PTS)**: Sigmoid-based scoring and Time-To-Collision (TTC) estimation using optical flow velocity vectors.
2. **Mesh Alert Propagation (MAP)**: Haversine-based pre-alerting of neighboring edge nodes to heighten sensitivity before a threat arrives.
3. **Adaptive Zone Geometry (AZG)**: Dynamic morphing of danger zones based on time-of-day, weather, and crowd density.
4. **Footpoint+PIP v2**: Predictive violation detection using projected ground contact points.

### Architecture
```
[Edge Nodes] <-> [Zone Coordinator (FastAPI)] <-> [City Dashboard (React)]
```

### Quick Start
1. **Docker Compose (Full Stack)**:
   ```bash
   docker-compose up --build
   ```
2. **Manual Backend Setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   python main.py
   ```
3. **Manual Dashboard Setup**:
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```

### Performance
- **Latency**: < 150ms median (End-to-End)
- **Accuracy**: > 0.92 F1 Score (YOLOv8n)
- **Scalability**: Tested up to 50 concurrent edge nodes per coordinator.

### License
MIT
