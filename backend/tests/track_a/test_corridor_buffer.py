"""F6 tests — corridor buffer (the search zone around the highway).

Toy tests use a 1 km line in EPSG:32614 so the expected numbers can be
worked out by hand. The real-data test reads the F1/F2 caches and writes its
own cache to ``tmp_path`` — never to ``backend/data/processed/``, where a
``.gpkg`` without a ``.source.yaml`` would fail the F4 provenance audit.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pytest
from oohscout.track_a_spatial import (
    build_corridor_buffer,
    load_or_build_corridor_buffer,
    load_or_build_highway_centerline,
    load_or_build_study_area,
)
from shapely.geometry import LineString, Point, box

TOY_CRS = 32614  # UTM 14N, metres
PROCESSED = Path("backend/data/processed")


def _toy_lines(crs: int = TOY_CRS) -> gpd.GeoDataFrame:
    """One 1 km line along the x-axis."""
    return gpd.GeoDataFrame(geometry=[LineString([(0, 0), (1000, 0)])], crs=crs)


def _toy_area(crs: int = TOY_CRS) -> gpd.GeoDataFrame:
    """A 10 km box around the toy line."""
    return gpd.GeoDataFrame(geometry=[box(-5000, -5000, 5000, 5000)], crs=crs)


# --- geometry ----------------------------------------------------------------


def test_point_499m_away_is_inside_and_501m_is_outside() -> None:
    zone = build_corridor_buffer(_toy_lines(), _toy_area(), distance_m=500)
    assert zone.contains(Point(500, 499))
    assert not zone.contains(Point(500, 501))


def test_overlapping_segments_become_one_polygon() -> None:
    """Union before buffer: the overlap is counted once, not twice."""
    lines = gpd.GeoDataFrame(
        geometry=[LineString([(0, 0), (1000, 0)]), LineString([(500, 0), (1500, 0)])],
        crs=TOY_CRS,
    )
    zone = build_corridor_buffer(lines, _toy_area(), distance_m=500)
    assert zone.geom_type == "Polygon"
    # 1500 m x 1000 m box + a 500 m circle (Shapely draws it with 64 sides).
    assert zone.area == pytest.approx(1500 * 1000 + Point(0, 0).buffer(500).area, rel=1e-6)


def test_zone_is_clipped_to_the_study_area() -> None:
    area = gpd.GeoDataFrame(geometry=[box(0, -600, 800, 600)], crs=TOY_CRS)
    zone = build_corridor_buffer(_toy_lines(), area, distance_m=500)
    assert zone.area == pytest.approx(800 * 1000)
    assert area.geometry.iloc[0].buffer(1e-6).contains(zone)


# --- input checks ------------------------------------------------------------


def test_degrees_are_rejected() -> None:
    with pytest.raises(ValueError, match="degrees"):
        build_corridor_buffer(_toy_lines(crs=4326), _toy_area(crs=4326), distance_m=500)


def test_feet_are_rejected() -> None:
    """Texas State Plane is projected but in US survey feet — 500 would mean 152 m."""
    with pytest.raises(ValueError, match="foot"):
        build_corridor_buffer(_toy_lines(crs=2277), _toy_area(crs=2277), distance_m=500)


def test_missing_crs_is_rejected() -> None:
    lines = gpd.GeoDataFrame(geometry=[LineString([(0, 0), (1000, 0)])])
    with pytest.raises(ValueError, match="no CRS"):
        build_corridor_buffer(lines, _toy_area(), distance_m=500)


def test_mismatched_crs_is_rejected() -> None:
    with pytest.raises(ValueError, match="same CRS"):
        build_corridor_buffer(_toy_lines(crs=32614), _toy_area(crs=32615), distance_m=500)


@pytest.mark.parametrize("bad", [0, -5, float("nan"), float("inf")])
def test_bad_distance_is_rejected(bad: float) -> None:
    with pytest.raises(ValueError, match="distance_m"):
        build_corridor_buffer(_toy_lines(), _toy_area(), distance_m=bad)


def test_highway_outside_study_area_is_rejected() -> None:
    far_away = gpd.GeoDataFrame(geometry=[box(90_000, 90_000, 91_000, 91_000)], crs=TOY_CRS)
    with pytest.raises(ValueError, match="empty"):
        build_corridor_buffer(_toy_lines(), far_away, distance_m=500)


# --- cache -------------------------------------------------------------------


def test_cache_file_name_includes_the_distance(tmp_path: Path) -> None:
    """A 1000 m request must never return the cached 500 m zone."""
    zone_500 = load_or_build_corridor_buffer(
        _toy_lines(), _toy_area(), tmp_path, cache_slug="toy", distance_m=500
    )
    zone_1000 = load_or_build_corridor_buffer(
        _toy_lines(), _toy_area(), tmp_path, cache_slug="toy", distance_m=1000
    )
    assert zone_500.cache_path.name == "toy_500m.gpkg"
    assert zone_1000.cache_path.name == "toy_1000m.gpkg"
    assert zone_1000.area_km2 > zone_500.area_km2


def test_second_call_reads_the_cache(tmp_path: Path) -> None:
    first = load_or_build_corridor_buffer(_toy_lines(), _toy_area(), tmp_path, cache_slug="toy")
    # Degree inputs would be rejected if the zone were rebuilt; a cache hit never looks at them.
    second = load_or_build_corridor_buffer(
        _toy_lines(crs=4326), _toy_area(crs=4326), tmp_path, cache_slug="toy"
    )
    assert second.cache_path == first.cache_path
    assert second.area_km2 == pytest.approx(first.area_km2)
    assert second.buffer_gdf_metric.crs.to_epsg() == TOY_CRS


# --- real data ---------------------------------------------------------------


@pytest.fixture(scope="module")
def mclennan_ih35() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """F1 study area + F2 centerline from the project cache (no network)."""
    if not (PROCESSED / "mclennan_ih35_centerline.gpkg").exists():
        pytest.skip("F1/F2 caches not built on this checkout")
    study = load_or_build_study_area(
        place="McLennan County, Texas", crs_metric=32614, cache_dir=PROCESSED
    )
    corridor = load_or_build_highway_centerline(
        admin_poly=study.admin_poly, cache_dir=PROCESSED, crs_metric=32614
    )
    return corridor.corridor_gdf_metric, study.admin_gdf_metric


def test_real_ih35_zone_is_one_plausible_polygon(
    mclennan_ih35: tuple[gpd.GeoDataFrame, gpd.GeoDataFrame], tmp_path: Path
) -> None:
    """~65 km of IH-35 x 2 sides x 0.5 km ≈ 65 km² (measured 65.4 km²)."""
    lines, area = mclennan_ih35
    zone = load_or_build_corridor_buffer(
        lines, area, tmp_path, cache_slug="mclennan_ih35_buffer", distance_m=500
    )
    assert 60.0 <= zone.area_km2 <= 72.0, f"{zone.area_km2:.1f} km²"
    assert len(zone.buffer_gdf_metric) == 1
    assert zone.buffer_gdf_metric.geom_type.iloc[0] == "Polygon"
    assert area.geometry.union_all().buffer(1).contains(zone.buffer_gdf_metric.geometry.iloc[0])
