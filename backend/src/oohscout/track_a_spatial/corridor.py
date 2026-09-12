"""F2 — IH-35 highway centerline loader for a given study area.

Production module. Applies the F1 pattern to a different OSM feature class:
- F1 fetched an administrative polygon (buildings → county boundary)
- F2 fetches highway LineStrings inside that polygon

Invariants (mirrors CLAUDE.md architectural rules):
- Two representations kept in sync: WGS 84 (`corridor_gdf`, for downstream
  OSMnx / web-map use) and a projected metric CRS (`corridor_gdf_metric`,
  for length / buffer / candidate-sampling math).
- Cache-first: repeat calls read the GeoPackage on disk without hitting
  Overpass.
- GeoPackage (not GeoJSON): projected metric coordinates need a CRS-aware
  format.
- Filtered to LineString / MultiLineString only — never a Point or Polygon.
- `osmid` (or its equivalent unique key) is asserted unique so downstream
  joins to permits, AADT stations, and candidates never explode into a
  Cartesian join.

F6 (bottom of this module) turns the centerline into the search zone: every
spot within ``distance_m`` of the highway, clipped to the study area.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import osmnx as ox
from shapely.geometry.base import BaseGeometry

# OSM tags IH-35 with ref="I 35" (space between the "I" and "35").
# Some segments carry multi-ref like "I 35;US 77" — we accept any ref that
# starts with "I 35" so business routes and combined segments still match.
DEFAULT_HIGHWAY_REF = "I 35"
DEFAULT_HIGHWAY_TAGS: dict[str, list[str]] = {"highway": ["motorway"]}


@dataclass(frozen=True)
class Corridor:
    """Immutable pair of representations for one highway inside a study area.

    Attributes
    ----------
    highway_ref:
        The OSM ``ref`` value used to filter (e.g. ``"I 35"``).
    corridor_gdf:
        Filtered ``GeoDataFrame`` in WGS 84 (EPSG:4326). Feed this to any
        downstream OSMnx call that also wants degrees.
    corridor_gdf_metric:
        Same rows in the requested projected metric CRS. Use for length,
        buffer, projection-onto-line, and candidate sampling.
    total_length_m:
        Sum of the projected geometry length in meters. This is the number
        you compare to Google Maps' "IH-35 through McLennan County" figure.
    cache_path:
        The ``.gpkg`` file the projected corridor is cached to.
    """

    highway_ref: str
    corridor_gdf: gpd.GeoDataFrame
    corridor_gdf_metric: gpd.GeoDataFrame
    total_length_m: float
    cache_path: Path


def _matches_ref(ref_value: object, highway_ref: str) -> bool:
    """Return True if ``ref_value`` names the target highway.

    OSM ``ref`` may be a plain string ("I 35"), a semicolon-joined multi-ref
    ("I 35;US 77"), or missing entirely (``None``/``NaN``). We accept a
    match if any component starts with ``highway_ref``.
    """
    if ref_value is None:
        return False
    text = str(ref_value)
    if not text or text.lower() == "nan":
        return False
    return any(part.strip().startswith(highway_ref) for part in text.split(";"))


def load_or_build_highway_centerline(
    admin_poly: BaseGeometry,
    cache_dir: Path,
    *,
    crs_metric: int = 32614,
    crs_geographic: int = 4326,
    highway_ref: str = DEFAULT_HIGHWAY_REF,
    highway_tags: dict[str, list[str]] | None = None,
    cache_slug: str = "mclennan_ih35_centerline",
    reference_length_km: float | None = None,
    length_tolerance_pct: float = 10.0,
) -> Corridor:
    """Load a cached IH-35 centerline for the given ``admin_poly``, or build it.

    Parameters
    ----------
    admin_poly:
        Study-area polygon in WGS 84 (typically ``StudyArea.admin_poly`` from
        :mod:`oohscout.track_a_spatial.study_area`).
    cache_dir:
        Directory to write / read the ``.gpkg`` cache. Created if missing.
    crs_metric:
        Projected CRS for metric measurement. Default UTM 14N (Central Texas).
    crs_geographic:
        Geographic CRS for the returned WGS 84 representation. Default 4326.
    highway_ref:
        OSM ``ref`` prefix to keep. Default ``"I 35"`` (IH-35).
    highway_tags:
        OSM tag dict passed to Overpass. Default ``{"highway": ["motorway"]}``.
    cache_slug:
        Filename stem for the ``.gpkg``. Change when retargeting to another
        county to avoid clobbering McLennan's cache.
    reference_length_km:
        Optional independently-known length (from Google Maps or the highway
        department). When provided, the measured length is asserted within
        ``length_tolerance_pct``.
    length_tolerance_pct:
        Allowed percent difference from ``reference_length_km``. Default 10%.

    Returns
    -------
    Corridor
        Frozen dataclass with both CRS representations, total metric length,
        and the cache path.

    Raises
    ------
    AssertionError
        If the filtered result is empty, geometries are not LineString /
        MultiLineString, the metric CRS mismatches, `osmid` is not unique,
        or the length is outside the reference tolerance.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{cache_slug}.gpkg"
    tags = highway_tags or DEFAULT_HIGHWAY_TAGS

    if cache_path.exists():
        corridor_gdf_metric = gpd.read_file(cache_path, layer="corridor")
        corridor_gdf = corridor_gdf_metric.to_crs(epsg=crs_geographic)
    else:
        # Overpass returns a possibly-MultiIndexed GeoDataFrame; flatten it
        # so `osmid` becomes a column we can query and assert on.
        raw = ox.features_from_polygon(admin_poly, tags=tags).reset_index()
        if "id" in raw.columns and "osmid" not in raw.columns:
            raw = raw.rename(columns={"id": "osmid"})

        # Keep LineString / MultiLineString only. Some OSM tag combinations
        # attach a Point (for a numbered exit) that would break length math.
        is_line = raw.geometry.geom_type.isin(["LineString", "MultiLineString"])
        raw = raw[is_line].copy()

        # Filter to the target highway ref.
        if "ref" not in raw.columns:
            raw["ref"] = None
        matched = raw[raw["ref"].apply(lambda v: _matches_ref(v, highway_ref))].copy()

        assert len(matched) > 0, (
            f"No LineString features with ref starting with {highway_ref!r} "
            "found inside admin_poly. Widen highway_tags or check ref value."
        )

        # OSMnx occasionally returns a way twice (verified: identical geometry,
        # identical attrs). Dedupe on osmid so downstream length + spacing math
        # doesn't double-count. Confirmed safe: geoms.equals() = True on dupes.
        matched = matched.drop_duplicates(subset=["osmid"], keep="first")

        # Keep a lean column set for the cache; project to metric CRS.
        core_cols = ["osmid", "ref", "name", "highway", "geometry"]
        keep_cols = [c for c in core_cols if c in matched.columns]
        corridor_gdf = matched[keep_cols].reset_index(drop=True)
        corridor_gdf_metric = corridor_gdf.to_crs(epsg=crs_metric)

        # Persist the projected representation. GPKG holds CRS metadata
        # correctly; GeoJSON would silently reproject to WGS 84 on write.
        corridor_gdf_metric.to_file(cache_path, layer="corridor", driver="GPKG")
        corridor_gdf = corridor_gdf_metric.to_crs(epsg=crs_geographic)

    # Deterministic invariants — the notebook prints these; production raises.
    assert len(corridor_gdf) > 0, "Corridor is empty after cache load."
    assert (
        corridor_gdf.geometry.geom_type.isin(["LineString", "MultiLineString"]).all()
    ), "Corridor must contain only LineString / MultiLineString geometries."
    assert corridor_gdf_metric.crs.to_epsg() == crs_metric, (
        f"Metric CRS EPSG:{corridor_gdf_metric.crs.to_epsg()} != requested EPSG:{crs_metric}"
    )
    assert corridor_gdf["osmid"].is_unique, (
        "osmid is not unique — downstream joins would explode. "
        "Check for duplicate OSM ways in the fetched data."
    )

    total_length_m = float(corridor_gdf_metric.geometry.length.sum())

    if reference_length_km is not None:
        length_km = total_length_m / 1000.0
        diff_pct = abs(length_km - reference_length_km) / reference_length_km * 100
        assert diff_pct <= length_tolerance_pct, (
            f"Corridor length {length_km:.2f} km differs from reference "
            f"{reference_length_km:.2f} km by {diff_pct:.2f}% "
            f"(tolerance {length_tolerance_pct}%)."
        )

    return Corridor(
        highway_ref=highway_ref,
        corridor_gdf=corridor_gdf,
        corridor_gdf_metric=corridor_gdf_metric,
        total_length_m=total_length_m,
        cache_path=cache_path,
    )


# ---------------------------------------------------------------------------
# F6 — corridor buffer (the search zone every later feature works inside)
# ---------------------------------------------------------------------------

BUFFER_LAYER = "corridor_buffer"
_METRE_UNIT_NAMES = ("metre", "meter")


@dataclass(frozen=True)
class CorridorBuffer:
    """Everything within ``distance_m`` of a highway, clipped to the study area.

    Attributes
    ----------
    distance_m:
        Buffer width in metres. A product setting ("near is a choice"), not a
        legal distance.
    buffer_gdf_metric:
        One-row ``GeoDataFrame`` (``distance_m`` column + geometry) in the
        metric CRS of the inputs.
    area_km2:
        Area of the zone. Sanity check: road length x 2 x distance, minus the
        overlap between the two carriageways.
    cache_path:
        The ``.gpkg`` file the zone is cached to. The distance is part of the
        file name, so a different width never returns a stale zone.
    """

    distance_m: float
    buffer_gdf_metric: gpd.GeoDataFrame
    area_km2: float
    cache_path: Path


def _require_metric_crs(gdf: gpd.GeoDataFrame, label: str) -> None:
    """Raise ``ValueError`` unless ``gdf`` uses a projected CRS measured in metres.

    ``is_projected`` alone is not enough: Texas State Plane (EPSG:2277) is
    projected but measured in US survey feet, so ``buffer(500)`` there would
    be 152 m, not 500 m.
    """
    if gdf.crs is None:
        raise ValueError(f"{label} has no CRS defined.")
    if not gdf.crs.is_projected:
        raise ValueError(f"{label} CRS is in degrees; a projected CRS is required.")
    unit = gdf.crs.axis_info[0].unit_name
    if unit not in _METRE_UNIT_NAMES:
        raise ValueError(f"{label} is measured in {unit!r}, not metres; reproject with .to_crs().")


def build_corridor_buffer(
    lines_metric: gpd.GeoDataFrame,
    study_area_metric: gpd.GeoDataFrame,
    distance_m: float,
) -> BaseGeometry:
    """Buffer the union of ``lines_metric`` by ``distance_m``, clipped to the study area.

    Pure function: no files, no network. The lines are unioned *before*
    buffering — buffering F2's 245 segments one by one would give 245
    overlapping polygons (323 km² for McLennan at 500 m) instead of one zone
    (65 km²).

    Parameters
    ----------
    lines_metric:
        Highway lines in a metric CRS (typically ``Corridor.corridor_gdf_metric``).
    study_area_metric:
        Study-area polygon(s) in the same CRS (typically
        ``StudyArea.admin_gdf_metric``). A GeoDataFrame rather than a bare
        Shapely geometry so its CRS can be checked.
    distance_m:
        Buffer width in metres.

    Returns
    -------
    BaseGeometry
        The zone — a Polygon (or MultiPolygon if the highway leaves and
        re-enters the study area).

    Raises
    ------
    ValueError
        If ``distance_m`` is not a finite number > 0, either input is not in a
        metric CRS, the two CRSs differ, or the zone is empty (the lines do
        not reach the study area).
    """
    if not (math.isfinite(distance_m) and distance_m > 0):
        raise ValueError(f"distance_m must be a real number > 0, got {distance_m!r}")
    _require_metric_crs(lines_metric, "Highway lines")
    _require_metric_crs(study_area_metric, "Study area")
    if lines_metric.crs != study_area_metric.crs:
        raise ValueError(
            f"Highway lines ({lines_metric.crs.to_string()}) and study area "
            f"({study_area_metric.crs.to_string()}) must use the same CRS."
        )

    # Glue the road pieces into one shape, widen it, then cut it to the study area.
    merged = lines_metric.geometry.union_all()
    wide = merged.buffer(distance_m)
    study_area_shape = study_area_metric.geometry.union_all()
    zone = wide.intersection(study_area_shape)
    if zone.area == 0:
        raise ValueError("Corridor buffer is empty: the highway lines do not reach the study area.")
    return zone


def load_or_build_corridor_buffer(
    lines_metric: gpd.GeoDataFrame,
    study_area_metric: gpd.GeoDataFrame,
    cache_dir: Path,
    *,
    cache_slug: str,
    distance_m: float = 500.0,
) -> CorridorBuffer:
    """Load a cached corridor buffer, or build and cache it if missing.

    Parameters
    ----------
    lines_metric, study_area_metric:
        See :func:`build_corridor_buffer`.
    cache_dir:
        Directory to write / read the ``.gpkg`` cache. Created if missing.
    cache_slug:
        Filename stem naming the corridor, e.g. ``"mclennan_ih35_buffer"``.
        No default on purpose: the caller names the corridor, never this
        module.
    distance_m:
        Buffer width in metres. Default 500 m. Becomes part of the cache
        file name (``<cache_slug>_500m.gpkg``), so a different width never
        returns a stale zone.

    Returns
    -------
    CorridorBuffer
        Frozen dataclass with the one-row zone, its area, and the cache path.

    Raises
    ------
    ValueError
        On a cache miss, for any input rejected by :func:`build_corridor_buffer`.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{cache_slug}_{distance_m:g}m.gpkg"

    if cache_path.exists():
        buffer_gdf_metric = gpd.read_file(cache_path, layer=BUFFER_LAYER)
    else:
        zone = build_corridor_buffer(lines_metric, study_area_metric, distance_m)
        buffer_gdf_metric = gpd.GeoDataFrame(
            {"distance_m": [float(distance_m)]}, geometry=[zone], crs=lines_metric.crs
        )
        buffer_gdf_metric.to_file(cache_path, layer=BUFFER_LAYER, driver="GPKG")

    area_km2 = float(buffer_gdf_metric.geometry.area.iloc[0]) / 1_000_000.0
    return CorridorBuffer(
        distance_m=float(distance_m),
        buffer_gdf_metric=buffer_gdf_metric,
        area_km2=area_km2,
        cache_path=cache_path,
    )
