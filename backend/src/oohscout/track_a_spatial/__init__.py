"""Track A — Deterministic Spatial Engine.

Pure GIS functions. Never calls the LLM. Never asks Track B.

Shipped modules:
- study_area: F1 — retargetable study-area loader (McLennan County today,
  any Nominatim-geocodable place tomorrow).

Planned modules:
- corridor: F2 — IH-35 highway centerline; F6 — corridor buffer;
  F7 — candidate site sampling.
- demand: F10-F18 — DBSCAN, KMeans, isochrones, advertiser POI features.
- spacing: F8-F9 — LRS engine using verified 43 TAC rules.
- scoring: F25-F27 — persona-weighted opportunity score.
- lease: F28-F30 — spatial lag lease pricing model.
- visibility: F23 — LiDAR U-Net raycast for obstruction analysis.
"""

from oohscout.track_a_spatial.study_area import (
    StudyArea,
    assert_contains_point,
    load_or_build_study_area,
)

__all__ = [
    "StudyArea",
    "assert_contains_point",
    "load_or_build_study_area",
]
