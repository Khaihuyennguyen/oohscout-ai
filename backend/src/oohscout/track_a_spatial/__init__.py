"""Track A — Deterministic Spatial Engine.

Pure GIS functions. Never calls the LLM. Never asks Track B.
Modules (to be built):
- corridor: get_corridor, buffer, sample candidate points
- demand: DBSCAN, KMeans, isochrones, advertiser POI features
- spacing: LRS engine using verified 43 TAC rules
- scoring: persona-weighted opportunity score
- lease: spatial lag lease pricing model
- visibility: LiDAR U-Net raycast for obstruction analysis
"""
