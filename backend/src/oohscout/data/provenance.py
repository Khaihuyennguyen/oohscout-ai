"""F4 — Data provenance sidecars.

Every cached dataset in `backend/data/processed/` gets a matching
`.source.yaml` sidecar answering: where did this come from, under what
license, when did we download it, can we sell it, can we redistribute it.

The audit function is meant to be called from pytest so any new dataset
without a sidecar fails the build.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

# File extensions we treat as datasets requiring provenance sidecars.
# Kept intentionally short — expand as new formats enter the project.
DATA_EXTENSIONS: tuple[str, ...] = (".gpkg", ".geojson", ".parquet")
SIDECAR_EXTENSION = ".source.yaml"


@dataclass(frozen=True)
class SourceRecord:
    """One provenance record — becomes one `.source.yaml` file.

    Fields ordered to read as a natural narrative when serialized.
    """

    source_name: str
    source_url: str
    record_count: int
    license: str
    commercial_use_allowed: bool | str
    redistribution_allowed: bool | str
    retrieval_method: str = "HTTPS download"
    retrieval_date: str = field(default_factory=lambda: str(date.today()))
    authority: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a dict ready for YAML serialization, preserving field order."""
        return asdict(self)


def sidecar_path_for(data_path: Path) -> Path:
    """Return the sidecar path that pairs with a given data file.

    Example: ``mclennan_ih35_centerline.gpkg`` -> ``mclennan_ih35_centerline.source.yaml``.
    Uses ``.with_suffix`` so parent directories and stems are preserved.
    """
    return Path(data_path).with_suffix(SIDECAR_EXTENSION)


def write_source_yaml(data_path: Path, record: SourceRecord) -> Path:
    """Write ``record`` next to ``data_path`` and return the sidecar path.

    Uses ``yaml.safe_dump`` with ``sort_keys=False`` so the file reads in
    the same field order as `SourceRecord`.

    Parameters
    ----------
    data_path:
        Absolute path to the cached data file the sidecar describes.
    record:
        The provenance record to serialize.

    Returns
    -------
    Path
        The path the sidecar was written to.
    """
    sidecar = sidecar_path_for(data_path)
    sidecar.write_text(yaml.safe_dump(record.to_dict(), sort_keys=False))
    return sidecar


def read_source_yaml(data_path: Path) -> dict[str, Any]:
    """Read the sidecar for ``data_path`` and return it as a dict.

    Raises FileNotFoundError if the sidecar is missing — callers that want
    a soft check should use :func:`audit_provenance` instead.
    """
    sidecar = sidecar_path_for(data_path)
    if not sidecar.exists():
        raise FileNotFoundError(f"No provenance sidecar for {data_path.name}")
    return yaml.safe_load(sidecar.read_text())


def audit_provenance(data_dir: Path) -> tuple[list[Path], list[Path]]:
    """Scan ``data_dir`` for data files missing their sidecars.

    Only checks files with extensions in :data:`DATA_EXTENSIONS`. Sidecar
    files themselves are ignored.

    Returns
    -------
    tuple[list[Path], list[Path]]
        ``(data_files, missing_sidecars)``. Both lists are sorted for
        deterministic pytest output.
    """
    data_dir = Path(data_dir)
    data_files = sorted(
        f
        for ext in DATA_EXTENSIONS
        for f in data_dir.glob(f"*{ext}")
        if not f.name.endswith(SIDECAR_EXTENSION)
    )
    missing = sorted(
        f for f in data_files if not sidecar_path_for(f).exists()
    )
    return data_files, missing
