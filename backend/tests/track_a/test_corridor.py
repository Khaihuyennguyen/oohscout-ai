"""F2 smoke tests — proves corridor.py is importable and behaves correctly.

Uses the real cached .gpkg at backend/data/processed/ when present; falls back
to a per-test temp dir + live Overpass call when the cache is missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from oohscout.track_a_spatial import (
    Corridor,
    StudyArea,
    load_or_build_ih35_centerline,
    load_or_build_study_area,
)

MCLENNAN_PLACE = "McLennan County, Texas"
MCLENNAN_CRS_METRIC = 32614
MCLENNAN_REFERENCE_AREA_KM2 = 2746.0

# Total length includes both directions of IH-35 plus frontage / ramp
# segments that carry the "I 35" ref. Measured 131 km; band accommodates
# future OSM data changes without becoming meaningless.
IH35_MIN_LENGTH_KM = 100.0
IH35_MAX_LENGTH_KM = 160.0


@pytest.fixture(scope="module")
def study_and_cache_dir(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[StudyArea, Path]:
    """Load F1 study area from the project cache when it exists."""
    project_cache = Path("backend/data/processed")
    cache_dir = (
        project_cache
        if (project_cache / "mclennan_county_study_area.gpkg").exists()
        else tmp_path_factory.mktemp("gpkg_cache")
    )
    study = load_or_build_study_area(
        place=MCLENNAN_PLACE,
        crs_metric=MCLENNAN_CRS_METRIC,
        cache_dir=cache_dir,
        reference_total_area_km2=MCLENNAN_REFERENCE_AREA_KM2,
    )
    return study, cache_dir


@pytest.fixture(scope="module")
def corridor(study_and_cache_dir: tuple[StudyArea, Path]) -> Corridor:
    study, cache_dir = study_and_cache_dir
    return load_or_build_ih35_centerline(
        admin_poly=study.admin_poly,
        cache_dir=cache_dir,
        crs_metric=MCLENNAN_CRS_METRIC,
    )


def test_corridor_has_segments(corridor: Corridor) -> None:
    assert len(corridor.corridor_gdf) > 0


def test_corridor_geometries_are_lines_only(corridor: Corridor) -> None:
    types = set(corridor.corridor_gdf.geometry.geom_type.unique())
    assert types.issubset({"LineString", "MultiLineString"}), (
        f"Non-line geometry types leaked in: {types}"
    )


def test_corridor_osmid_is_unique(corridor: Corridor) -> None:
    """The dedupe step protects downstream joins from Cartesian explosion."""
    assert corridor.corridor_gdf["osmid"].is_unique


def test_corridor_metric_crs_matches_request(corridor: Corridor) -> None:
    assert corridor.corridor_gdf_metric.crs.to_epsg() == MCLENNAN_CRS_METRIC


def test_corridor_total_length_is_plausible(corridor: Corridor) -> None:
    """IH-35 through McLennan includes both directions; ~130 km expected."""
    length_km = corridor.total_length_m / 1000.0
    assert IH35_MIN_LENGTH_KM <= length_km <= IH35_MAX_LENGTH_KM, (
        f"Measured {length_km:.1f} km is outside plausible range "
        f"[{IH35_MIN_LENGTH_KM}, {IH35_MAX_LENGTH_KM}] km."
    )


def test_corridor_cache_exists_after_load(corridor: Corridor) -> None:
    assert corridor.cache_path.exists(), (
        f"Expected .gpkg cache at {corridor.cache_path}, not found."
    )


def test_wrong_reference_length_raises(
    study_and_cache_dir: tuple[StudyArea, Path], tmp_path: Path
) -> None:
    """Retargeting with a nonsense reference length must fail loudly."""
    study, _ = study_and_cache_dir
    with pytest.raises(AssertionError, match="differs from reference"):
        load_or_build_ih35_centerline(
            admin_poly=study.admin_poly,
            cache_dir=tmp_path,
            crs_metric=MCLENNAN_CRS_METRIC,
            reference_length_km=10.0,  # IH-35 is ~130 km — deliberately wrong
            length_tolerance_pct=10.0,
            cache_slug="mclennan_ih35_wrong_ref_test",
        )
