"""F1 — Retargetable study-area loader.

Production module. The notebook (docs/learning/chapters/ua_advanced_ch01_setup/
03_oohscout_adaptation.ipynb) is the learning artifact; this module is what
FastAPI endpoints, agent tools, and tests import.

Key invariants (mirrors CLAUDE.md architectural rules):
- Two representations kept in sync: WGS 84 (`admin_gdf`, for OSMnx input) and
  a projected metric CRS (`admin_gdf_metric`, for area/distance measurement).
- Cache-first: repeat calls read the GeoPackage on disk without hitting
  Nominatim.
- GeoPackage (not GeoJSON): RFC 7946 mandates WGS 84 for GeoJSON; projected
  metric coordinates belong in a CRS-aware format.
- Deterministic assertions replace the manual visual check for downstream
  callers. The visual check remains in the notebook for humans.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import osmnx as ox
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class StudyArea:
    """Immutable pair of representations for one administrative area.

    Attributes
    ----------
    place:
        The Nominatim-geocodable name the area was resolved from, e.g.
        ``"McLennan County, Texas"``. Kept so downstream code can label output.
    admin_gdf:
        Single-row ``GeoDataFrame`` in WGS 84 (EPSG:4326). Feed this to
        OSMnx ``features_from_polygon`` calls — OSM data arrives in degrees.
    admin_gdf_metric:
        Single-row ``GeoDataFrame`` in the requested projected metric CRS.
        Use this for every buffer, distance, and area calculation.
    admin_poly:
        Union of ``admin_gdf`` geometry. Same coordinates as ``admin_gdf``,
        already merged for callers that need a single shapely object.
    study_area:
        Union of ``admin_gdf_metric`` geometry. Same role as ``admin_poly``
        but in metric coordinates.
    cache_path:
        The ``.gpkg`` file the projected boundary is cached to.
    """

    place: str
    admin_gdf: gpd.GeoDataFrame
    admin_gdf_metric: gpd.GeoDataFrame
    admin_poly: BaseGeometry
    study_area: BaseGeometry
    cache_path: Path


def _slugify(place: str) -> str:
    """Turn ``"McLennan County, Texas"`` into ``"mclennan_county"``.

    Used to derive a stable filename per study area.
    """
    return place.split(",")[0].strip().lower().replace(" ", "_")


def load_or_build_study_area(
    place: str,
    crs_metric: int,
    cache_dir: Path,
    *,
    crs_geographic: int = 4326,
    reference_total_area_km2: float | None = None,
    area_tolerance_pct: float = 5.0,
) -> StudyArea:
    """Load a cached study-area boundary, or build and cache it if missing.

    Parameters
    ----------
    place:
        Nominatim-geocodable place name.
    crs_metric:
        EPSG code for the local projected metric CRS (e.g. 32614 for UTM 14N
        over Central Texas). See https://epsg.io for zone selection.
    cache_dir:
        Directory to write / read the ``.gpkg`` cache. Created if missing.
    crs_geographic:
        Geographic CRS used for the returned WGS 84 representation. Default
        EPSG:4326.
    reference_total_area_km2:
        Optional published administrative area. When provided, the returned
        study area is asserted to match within ``area_tolerance_pct``. Use the
        U.S. Census TIGERweb total area (land + water) for U.S. counties.
    area_tolerance_pct:
        Allowed percent difference from ``reference_total_area_km2``. Default
        5%.

    Returns
    -------
    StudyArea
        Frozen dataclass with both representations, unioned geometries, and
        the cache path.

    Raises
    ------
    AssertionError
        If the geocoder returns something other than one Polygon/MultiPolygon,
        the metric CRS does not match ``crs_metric``, or the measured area
        falls outside ``area_tolerance_pct`` of ``reference_total_area_km2``.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_slugify(place)}_study_area.gpkg"

    if cache_path.exists():
        admin_gdf_metric = gpd.read_file(cache_path, layer="study_area")
        admin_gdf = admin_gdf_metric.to_crs(epsg=crs_geographic)
    else:
        admin_gdf = ox.geocode_to_gdf(place)
        admin_gdf_metric = admin_gdf.to_crs(epsg=crs_metric)
        admin_gdf_metric.to_file(cache_path, layer="study_area", driver="GPKG")

    # Deterministic invariants — the notebook prints these; production raises.
    assert len(admin_gdf) == 1, f"Expected one record for {place!r}, got {len(admin_gdf)}"
    assert (
        admin_gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all()
    ), "Study-area geometry must be Polygon or MultiPolygon."
    assert admin_gdf.geometry.is_valid.all(), "Study-area geometry is not valid."
    assert not admin_gdf.geometry.is_empty.any(), "Study-area geometry is empty."
    assert admin_gdf_metric.crs.to_epsg() == crs_metric, (
        f"Projected CRS EPSG:{admin_gdf_metric.crs.to_epsg()} != requested EPSG:{crs_metric}"
    )

    admin_poly = admin_gdf.geometry.union_all()
    study_area = admin_gdf_metric.geometry.union_all()

    if reference_total_area_km2 is not None:
        area_km2 = study_area.area / 1_000_000.0
        diff_pct = abs(area_km2 - reference_total_area_km2) / reference_total_area_km2 * 100
        assert diff_pct <= area_tolerance_pct, (
            f"{place} area {area_km2:,.1f} km² differs from published "
            f"{reference_total_area_km2:,.1f} km² by {diff_pct:.2f}% "
            f"(tolerance {area_tolerance_pct}%). Geocoder likely returned the "
            "wrong boundary."
        )

    return StudyArea(
        place=place,
        admin_gdf=admin_gdf,
        admin_gdf_metric=admin_gdf_metric,
        admin_poly=admin_poly,
        study_area=study_area,
        cache_path=cache_path,
    )


def assert_contains_point(
    study: StudyArea, lon: float, lat: float, label: str = "reference point"
) -> None:
    """Assert a known lon/lat sits inside the study area (Option B check).

    This replaces the manual "eyeball the map" gate item with a deterministic
    check. For McLennan County, pass Waco courthouse (-97.1467, 31.5493).

    Parameters
    ----------
    study:
        Result of :func:`load_or_build_study_area`.
    lon, lat:
        Coordinates of a landmark known to sit inside the boundary, in WGS 84.
    label:
        Human-readable name used in the assertion message.
    """
    point_metric = (
        gpd.GeoSeries([Point(lon, lat)], crs=4326)
        .to_crs(study.admin_gdf_metric.crs)
        .iloc[0]
    )
    assert study.study_area.contains(point_metric), (
        f"{label} ({lon}, {lat}) is not inside {study.place}. "
        "Geocoder likely returned the wrong boundary."
    )
