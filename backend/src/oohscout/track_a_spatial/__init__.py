"""Track A — Deterministic Spatial Engine.

Pure GIS functions. Never calls the LLM. Never asks Track B.

Shipped modules:
- study_area: F1 — retargetable study-area loader (McLennan County today,
  any Nominatim-geocodable place tomorrow).
- corridor:   F2 — IH-35 highway centerline for a given study area.
              F6 — corridor buffer: the search zone within N metres of the
              highway, clipped to the study area.

Planned modules:
- demand:     F10-F18 — DBSCAN, KMeans, isochrones, advertiser POI features.
- spacing:    F8-F9 — LRS engine using verified 43 TAC rules.
- scoring:    F25-F27 — persona-weighted opportunity score.
- lease:      F28-F30 — spatial lag lease pricing model.
- visibility: F23 — LiDAR U-Net raycast for obstruction analysis.
"""

from oohscout.track_a_spatial.corridor import (
    Corridor,
    CorridorBuffer,
    build_corridor_buffer,
    load_or_build_corridor_buffer,
    load_or_build_highway_centerline,
)
from oohscout.track_a_spatial.study_area import (
    StudyArea,
    assert_contains_point,
    load_or_build_study_area,
)

__all__ = [
    "Corridor",
    "CorridorBuffer",
    "StudyArea",
    "assert_contains_point",
    "build_corridor_buffer",
    "load_or_build_corridor_buffer",
    "load_or_build_highway_centerline",
    "load_or_build_study_area",
]
