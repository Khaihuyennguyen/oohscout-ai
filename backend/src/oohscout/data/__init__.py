"""Track A — Data ingestion + provenance.

Shipped modules:
- provenance: F4 — `.source.yaml` sidecar helpers + audit.

Planned modules:
- txdot:    F3a — TxDOT REST API client (currently notebook-only).
- osm:      OSMnx wrappers around Overpass.
- sentinel: Sentinel-2 STAC + rasterio.
- mcad:     MCAD parcel client (blocked on data request).
"""

from oohscout.data.provenance import (
    DATA_EXTENSIONS,
    SIDECAR_EXTENSION,
    SourceRecord,
    audit_provenance,
    read_source_yaml,
    sidecar_path_for,
    write_source_yaml,
)

__all__ = [
    "DATA_EXTENSIONS",
    "SIDECAR_EXTENSION",
    "SourceRecord",
    "audit_provenance",
    "read_source_yaml",
    "sidecar_path_for",
    "write_source_yaml",
]
