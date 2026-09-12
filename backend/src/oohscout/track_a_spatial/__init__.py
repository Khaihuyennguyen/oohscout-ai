"""Track A — Deterministic Spatial Engine.

Pure GIS functions. Never calls the LLM. Never asks Track B.

Shipped modules:
- study_area:     F1 — retargetable study-area loader (McLennan County today,
                  any Nominatim-geocodable place tomorrow).
- corridor:       F2 — IH-35 highway centerline for a given study area.
                  F6 — corridor buffer: the search zone within N metres of the
                  highway, clipped to the study area.
- reference:      F7a — one reference line per direction of travel; locate any
                  point on it (side, chainage, offset); milepost scale.
- existing_signs: existing permitted signs placed on the highway, back-to-back
                  pairs merged.
- screening:      F8 — preliminary screening sieve (blocked / near limit /
                  city rules / possible ETJ / open) and candidate placement.

Planned modules:
- demand:     F10-F18 — DBSCAN, KMeans, isochrones, advertiser POI features.
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
from oohscout.track_a_spatial.existing_signs import prepare_existing_signs, select_highway_signs
from oohscout.track_a_spatial.reference import (
    MilepostScale,
    build_milepost_scale,
    build_reference_lines,
    load_or_build_reference_lines,
    locate_on_reference,
)
from oohscout.track_a_spatial.screening import (
    merge_stretches,
    place_candidates,
    probe_points,
    screen_probes,
)
from oohscout.track_a_spatial.study_area import (
    StudyArea,
    assert_contains_point,
    load_or_build_study_area,
)

__all__ = [
    "Corridor",
    "CorridorBuffer",
    "MilepostScale",
    "StudyArea",
    "assert_contains_point",
    "build_corridor_buffer",
    "build_milepost_scale",
    "build_reference_lines",
    "load_or_build_corridor_buffer",
    "load_or_build_highway_centerline",
    "load_or_build_reference_lines",
    "load_or_build_study_area",
    "locate_on_reference",
    "merge_stretches",
    "place_candidates",
    "prepare_existing_signs",
    "probe_points",
    "screen_probes",
    "select_highway_signs",
]
