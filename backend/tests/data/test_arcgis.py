"""Tests — ArcGIS fetcher: paging, errors, size cap, SSRF guard, cache + provenance.

No network: ``requests.get`` and the DNS-based URL guard are replaced.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Self

import pytest
import yaml
from oohscout.data import arcgis
from oohscout.data.provenance import SourceRecord

LAYER = "https://services.example.org/arcgis/rest/services/Signs/FeatureServer/0"
BBOX = (-97.6, 31.2, -96.8, 31.9)


def _feature(i: int) -> dict:
    return {"type": "Feature", "properties": {"id": i}, "geometry": {"type": "Point", "coordinates": [-97.1, 31.5]}}


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start : start + chunk_size]


@pytest.fixture()
def fake_server(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Serve 5 features in pages of 2; record every call."""
    calls: list[dict] = []
    monkeypatch.setattr(arcgis, "PAGE_SIZE", 2)
    monkeypatch.setattr(arcgis, "assert_public_url", lambda url: calls.append({"checked": url}))

    def fake_get(url: str, params: dict, timeout: int, stream: bool) -> _FakeResponse:
        calls.append(params)
        offset = params["resultOffset"]
        return _FakeResponse({"features": [_feature(i) for i in range(offset, min(offset + 2, 5))]})

    monkeypatch.setattr(arcgis.requests, "get", fake_get)
    return calls


def test_all_pages_are_fetched(fake_server: list[dict]) -> None:
    gdf = arcgis.fetch_arcgis_features(LAYER, bbox=BBOX)
    assert gdf["id"].tolist() == [0, 1, 2, 3, 4]
    assert gdf.crs.to_epsg() == 4326
    offsets = [c["resultOffset"] for c in fake_server if "resultOffset" in c]
    assert offsets == [0, 2, 4]


def test_every_request_passes_the_url_guard(fake_server: list[dict]) -> None:
    arcgis.fetch_arcgis_features(LAYER, bbox=BBOX)
    checked = [c["checked"] for c in fake_server if "checked" in c]
    assert checked and all(url == f"{LAYER}/query" for url in checked)


def test_private_addresses_are_refused() -> None:
    with pytest.raises(ValueError, match="SSRF"):
        arcgis.fetch_arcgis_features("http://127.0.0.1/arcgis/FeatureServer/0", bbox=BBOX)


def test_server_errors_are_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(arcgis, "assert_public_url", lambda url: None)
    monkeypatch.setattr(
        arcgis.requests, "get", lambda *a, **k: _FakeResponse({"error": {"code": 400, "message": "bad where"}})
    )
    with pytest.raises(ValueError, match="bad where"):
        arcgis.fetch_arcgis_features(LAYER, bbox=BBOX)


def test_oversized_responses_are_refused(fake_server: list[dict], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(arcgis, "MAX_RESPONSE_BYTES", 50)
    with pytest.raises(ValueError, match="larger than"):
        arcgis.fetch_arcgis_features(LAYER, bbox=BBOX)


def test_cache_writes_provenance_and_is_reused(
    fake_server: list[dict], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = SourceRecord(
        source_name="Test signs", source_url=LAYER, record_count=0, license="Public",
        commercial_use_allowed=True, redistribution_allowed=True,
    )
    path = tmp_path / "signs.gpkg"
    first = arcgis.load_or_fetch_arcgis_layer(LAYER, path, bbox=BBOX, source=source)
    sidecar = yaml.safe_load(path.with_suffix(".source.yaml").read_text())
    assert sidecar["record_count"] == 5 == len(first)

    monkeypatch.setattr(arcgis.requests, "get", lambda *a, **k: pytest.fail("cache hit must not fetch"))
    second = arcgis.load_or_fetch_arcgis_layer(LAYER, path, bbox=BBOX, source=source)
    assert len(second) == 5
