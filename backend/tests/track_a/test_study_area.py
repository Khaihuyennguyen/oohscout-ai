"""F1a smoke tests — proves study_area.py is importable and behaves correctly.

These tests deliberately hit the real Nominatim endpoint (or the cached .gpkg)
rather than mocking. Milan's discipline: mock-based tests can pass while the
real integration is broken. See CLAUDE.md for the rule.

Run:
    uv run pytest backend/tests/track_a/test_study_area.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from oohscout.track_a_spatial import (
    StudyArea,
    assert_contains_point,
    load_or_build_study_area,
)

MCLENNAN_PLACE = "McLennan County, Texas"
MCLENNAN_CRS_METRIC = 32614
MCLENNAN_REFERENCE_AREA_KM2 = 2746.0
WACO_COURTHOUSE_LON = -97.1467
WACO_COURTHOUSE_LAT = 31.5493


@pytest.fixture(scope="module")
def mclennan_study(tmp_path_factory: pytest.TempPathFactory) -> StudyArea:
    """Load McLennan once per test module.

    Uses the real cached .gpkg at backend/data/processed/ when present so the
    test is fast and offline; falls back to a per-test temp dir if the cache
    is missing so CI without pre-warmed data still works.
    """
    project_cache = Path("backend/data/processed")
    cache_dir = (
        project_cache
        if (project_cache / "mclennan_county_study_area.gpkg").exists()
        else tmp_path_factory.mktemp("gpkg_cache")
    )
    return load_or_build_study_area(
        place=MCLENNAN_PLACE,
        crs_metric=MCLENNAN_CRS_METRIC,
        cache_dir=cache_dir,
        reference_total_area_km2=MCLENNAN_REFERENCE_AREA_KM2,
        area_tolerance_pct=5.0,
    )


def test_mclennan_returns_single_polygon(mclennan_study: StudyArea) -> None:
    assert len(mclennan_study.admin_gdf) == 1


def test_mclennan_metric_crs_matches_request(mclennan_study: StudyArea) -> None:
    assert mclennan_study.admin_gdf_metric.crs.to_epsg() == MCLENNAN_CRS_METRIC


def test_mclennan_area_within_five_percent_of_census(mclennan_study: StudyArea) -> None:
    area_km2 = mclennan_study.study_area.area / 1_000_000
    diff_pct = abs(area_km2 - MCLENNAN_REFERENCE_AREA_KM2) / MCLENNAN_REFERENCE_AREA_KM2 * 100
    assert diff_pct <= 5.0, f"Measured {area_km2:.1f} km² is {diff_pct:.2f}% off reference"


def test_waco_courthouse_is_inside_mclennan_boundary(mclennan_study: StudyArea) -> None:
    """Option B — deterministic replacement for the manual visual gate item."""
    assert_contains_point(
        mclennan_study,
        lon=WACO_COURTHOUSE_LON,
        lat=WACO_COURTHOUSE_LAT,
        label="Waco courthouse",
    )


def test_wrong_reference_area_raises(mclennan_study: StudyArea, tmp_path: Path) -> None:
    """A retarget that quotes the wrong reference area must fail loudly."""
    with pytest.raises(AssertionError, match="differs from published"):
        load_or_build_study_area(
            place=MCLENNAN_PLACE,
            crs_metric=MCLENNAN_CRS_METRIC,
            cache_dir=tmp_path,
            reference_total_area_km2=100.0,  # McLennan is 2,746 km² — deliberately wrong
            area_tolerance_pct=5.0,
        )
