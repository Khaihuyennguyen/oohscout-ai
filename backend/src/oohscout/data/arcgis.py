"""Fetch features from a public ArcGIS FeatureServer layer (TxDOT open data).

Used for TxDOT's commercial-sign permits, certified-city signs, reference
markers and city boundaries. The queries are plain HTTPS GETs:

- every URL passes :func:`oohscout.security.assert_public_url` (CLAUDE.md rule 12),
- each response body is capped at 50 MB,
- results are cached as GeoPackage with a ``.source.yaml`` provenance sidecar (F4).
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from oohscout.data.provenance import SourceRecord, write_source_yaml
from oohscout.security import assert_public_url

MAX_RESPONSE_BYTES = 50 * 1024 * 1024
PAGE_SIZE = 1000
_TIMEOUT_S = 60


def _get_json(url: str, params: dict[str, object]) -> dict:
    """GET ``url`` and parse JSON, refusing private hosts and oversized bodies."""
    assert_public_url(url)
    with requests.get(url, params=params, timeout=_TIMEOUT_S, stream=True) as response:
        response.raise_for_status()
        body = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            body.extend(chunk)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ValueError(f"Response from {url} is larger than {MAX_RESPONSE_BYTES} bytes.")
    return json.loads(bytes(body))


def fetch_arcgis_features(
    layer_url: str,
    *,
    bbox: tuple[float, float, float, float],
    where: str = "1=1",
    out_fields: str = "*",
) -> gpd.GeoDataFrame:
    """Fetch every feature of an ArcGIS layer that intersects ``bbox``.

    Parameters
    ----------
    layer_url:
        The layer endpoint, e.g. ``".../FeatureServer/0"`` (no ``/query``).
    bbox:
        ``(west, south, east, north)`` in WGS 84 degrees.
    where:
        SQL-style attribute filter understood by the server, e.g.
        ``"RTE_NM LIKE 'IH0035%'"``.
    out_fields:
        Comma-separated fields to return, or ``"*"``.

    Returns
    -------
    gpd.GeoDataFrame
        Features in EPSG:4326 (possibly empty).

    Raises
    ------
    ValueError
        If the server reports an error, or a response breaks the size cap.
    """
    frames = []
    offset = 0
    while True:
        payload = _get_json(
            f"{layer_url}/query",
            {
                "f": "geojson",
                "where": where,
                "geometry": ",".join(str(v) for v in bbox),
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": out_fields,
                "outSR": 4326,
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
            },
        )
        if "error" in payload:
            raise ValueError(f"ArcGIS error from {layer_url}: {payload['error']}")
        features = payload.get("features", [])
        if features:
            frames.append(gpd.GeoDataFrame.from_features(features, crs=4326))
        if len(features) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=4326)
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=4326)


def load_or_fetch_arcgis_layer(
    layer_url: str,
    cache_path: Path,
    *,
    bbox: tuple[float, float, float, float],
    source: SourceRecord,
    where: str = "1=1",
) -> gpd.GeoDataFrame:
    """Read ``cache_path`` if it exists; otherwise fetch the layer and cache it.

    The provenance sidecar is written from ``source`` with ``record_count``
    replaced by the number of features actually fetched.
    """
    cache_path = Path(cache_path)
    if cache_path.exists():
        return gpd.read_file(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    gdf = fetch_arcgis_features(layer_url, bbox=bbox, where=where)
    gdf.to_file(cache_path, driver="GPKG")
    write_source_yaml(
        cache_path,
        SourceRecord(**{**source.to_dict(), "record_count": len(gdf)}),
    )
    return gdf
