# public.safe | Technical Patent Claims

### Claim 1: Predictive Violation Detection
A method for predicting pedestrian-to-zone violations comprising:
- Estimating ground contact points (footpoints) of a detected pedestrian.
- Computing a velocity vector via optical flow between consecutive image frames.
- Projecting future footpoint positions based on said velocity vector.
- Performing a Point-in-Polygon (PIP) test against an adaptive danger zone for both current and projected positions.

### Claim 2: Adaptive Danger Zone Geometry
A system for dynamic spatial risk assessment comprising:
- A base danger zone polygon defined in image coordinates.
- A plurality of environmental modifiers (Time-of-day, Weather, Density).
- A mechanism for scaling polygon vertices outward from a geometric centroid based on a calculated expansion factor derived from said modifiers.

### Claim 3: Mesh-Based Pre-Alert Propagation
A distributed method for network-wide sensitivity adjustment comprising:
- Detecting a critical threat at a primary edge node.
- Identifying neighboring nodes within a calculated spatial radius.
- Propagating a pre-alert containing arrival time estimates.
- Temporarily lowering detection confidence thresholds at neighboring nodes to increase responsiveness.

### Claim 4: Integrated Probabilistic Threat Assessment
A probabilistic scoring pipeline comprising:
- Calculating a Time-To-Collision (TTC) value based on approach velocity and zone boundary distance.
- Applying a sigmoid function to the TTC value to generate a normalized Threat Score (0.0 to 1.0).
- Categorizing risk levels (SAFE, WARNING, DANGER, CRITICAL) for real-time visualization and alerting.
