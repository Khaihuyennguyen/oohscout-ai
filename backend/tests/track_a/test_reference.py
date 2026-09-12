"""F7a tests — reference lines, locating points on them, milepost scale.

Toy highway (EPSG:32614): the northbound carriageway runs up x = +15, the
southbound one down x = -15, 10 km each, drawn as two segments per direction
in the direction of travel (as OSM does).
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pytest
from oohscout.track_a_spatial import (
    build_milepost_scale,
    build_reference_lines,
    load_or_build_highway_centerline,
    load_or_build_reference_lines,
    load_or_build_study_area,
    locate_on_reference,
)
from shapely.geometry import LineString, Point

TOY_CRS = 32614
MILE_M = 1609.344
PROCESSED = Path("backend/data/processed")


def toy_highway(crs: int = TOY_CRS) -> gpd.GeoDataFrame:
    segments = [
        LineString([(15, 0), (15, 4000)]),
        LineString([(15, 4000), (15, 10_000)]),
        LineString([(-15, 10_000), (-15, 6000)]),
        LineString([(-15, 6000), (-15, 0)]),
    ]
    return gpd.GeoDataFrame(geometry=segments, crs=crs)


def _points(*xy: tuple[float, float], crs: int = TOY_CRS) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in xy], crs=crs)


def _by_direction(gdf: gpd.GeoDataFrame, direction: str) -> gpd.GeoDataFrame:
    return gdf[gdf["direction"] == direction]


# --- build_reference_lines ---------------------------------------------------


def test_segments_join_into_one_line_per_direction() -> None:
    refs = build_reference_lines(toy_highway())
    assert sorted(refs["direction"]) == ["NB", "SB"]
    assert (refs.geom_type == "LineString").all()
    assert refs["length_m"].tolist() == pytest.approx([10_000, 10_000])


def test_reference_lines_keep_the_direction_of_travel() -> None:
    refs = build_reference_lines(toy_highway())
    nb = _by_direction(refs, "NB").geometry.iloc[0]
    sb = _by_direction(refs, "SB").geometry.iloc[0]
    assert nb.coords[0] == (15, 0) and nb.coords[-1] == (15, 10_000)
    assert sb.coords[0] == (-15, 10_000) and sb.coords[-1] == (-15, 0)


def test_each_line_knows_its_side_of_the_highway() -> None:
    north_south = build_reference_lines(toy_highway())
    assert dict(zip(north_south["direction"], north_south["side"])) == {"NB": "E", "SB": "W"}
    east_west = gpd.GeoDataFrame(
        geometry=[LineString([(0, -15), (10_000, -15)]), LineString([(10_000, 15), (0, 15)])],
        crs=TOY_CRS,
    )
    refs = build_reference_lines(east_west)
    assert dict(zip(refs["direction"], refs["side"])) == {"EB": "S", "WB": "N"}


def test_gap_in_a_carriageway_is_rejected() -> None:
    lines = toy_highway()
    lines.loc[0, "geometry"] = LineString([(15, 0), (15, 3000)])
    with pytest.raises(ValueError, match="continuous"):
        build_reference_lines(lines)


def test_branch_is_not_glued_on_backwards() -> None:
    """A branch starting where the carriageway starts must not be flipped to join it."""
    lines = toy_highway()
    lines.loc[len(lines), "geometry"] = LineString([(15, 0), (400, 100)])
    with pytest.raises(ValueError, match="continuous"):
        build_reference_lines(lines)


def test_only_one_direction_is_rejected() -> None:
    with pytest.raises(ValueError, match="both directions"):
        build_reference_lines(toy_highway().iloc[:2])


def test_degrees_are_rejected() -> None:
    with pytest.raises(ValueError, match="degrees"):
        build_reference_lines(toy_highway(crs=4326))


def test_reference_lines_are_cached(tmp_path: Path) -> None:
    first = load_or_build_reference_lines(toy_highway(), tmp_path, cache_slug="toy_ref")
    # A cache hit never looks at the (invalid) input.
    second = load_or_build_reference_lines(toy_highway().iloc[:1], tmp_path, cache_slug="toy_ref")
    assert second["length_m"].tolist() == pytest.approx(first["length_m"].tolist())


# --- locate_on_reference -----------------------------------------------------


def test_points_get_side_chainage_and_offset() -> None:
    refs = build_reference_lines(toy_highway())
    located = locate_on_reference(_points((100, 2000), (-100, 2000)), refs)
    east, west = located.iloc[0], located.iloc[1]
    assert (east["side"], east["direction"]) == ("E", "NB")
    assert east["chainage_m"] == pytest.approx(2000)
    assert east["offset_m"] == pytest.approx(85)
    # Southbound counts from the north end, so y = 2000 is 8 km along it.
    assert (west["side"], west["direction"]) == ("W", "SB")
    assert west["chainage_m"] == pytest.approx(8000)


def test_locate_rejects_mismatched_crs() -> None:
    refs = build_reference_lines(toy_highway())
    with pytest.raises(ValueError, match="same CRS"):
        locate_on_reference(_points((100, 2000), crs=32615), refs)


# --- milepost scale ----------------------------------------------------------


def test_mileposts_are_interpolated_between_markers() -> None:
    refs = build_reference_lines(toy_highway())
    markers = _points((0, 0), (0, MILE_M), (0, 2 * MILE_M), (0, 10_000))
    markers["mp"] = [100, 101, 102, 100 + 10_000 / MILE_M]
    scale = build_milepost_scale(refs, markers, marker_col="mp")
    assert scale.at("NB", MILE_M * 1.5) == pytest.approx(101.5)
    # 1.5 miles along the southbound line is 1.5 miles south of the north end.
    assert scale.at("SB", MILE_M * 1.5) == pytest.approx(100 + 10_000 / MILE_M - 1.5)


def test_markers_past_the_end_of_the_line_are_ignored() -> None:
    refs = build_reference_lines(toy_highway())
    markers = _points((0, -3000), (0, 1000), (0, 9000))  # the first lies 3 km before the line starts
    markers["mp"] = [98.0, 100.0, 105.0]
    scale = build_milepost_scale(refs, markers, marker_col="mp")
    # Kept, it would project onto chainage 0 and drag this value down to 99.
    assert scale.at("NB", 500) == pytest.approx(100.0)


def test_mixed_up_markers_are_rejected() -> None:
    refs = build_reference_lines(toy_highway())
    markers = _points((0, 0), (0, 3000), (0, 6000))
    markers["mp"] = [100, 105, 102]
    with pytest.raises(ValueError, match="steadily"):
        build_milepost_scale(refs, markers, marker_col="mp")


def test_a_single_marker_is_rejected() -> None:
    refs = build_reference_lines(toy_highway())
    markers = _points((0, 0))
    markers["mp"] = [100]
    with pytest.raises(ValueError, match="two"):
        build_milepost_scale(refs, markers, marker_col="mp")


# --- real data ---------------------------------------------------------------


def test_real_ih35_gives_two_lines_of_about_65_km() -> None:
    if not (PROCESSED / "mclennan_ih35_centerline.gpkg").exists():
        pytest.skip("F1/F2 caches not built on this checkout")
    study = load_or_build_study_area(place="McLennan County, Texas", crs_metric=32614, cache_dir=PROCESSED)
    corridor = load_or_build_highway_centerline(admin_poly=study.admin_poly, cache_dir=PROCESSED, crs_metric=32614)
    refs = build_reference_lines(corridor.corridor_gdf_metric)
    assert sorted(refs["direction"]) == ["NB", "SB"]
    assert refs["length_m"].between(64_000, 67_000).all()
