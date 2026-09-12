"""F7a — reference lines: one continuous line per direction of travel.

Production module. Everything later in the screening is measured along these
lines:

- ``build_reference_lines`` glues F2's raw OSM segments (245 for IH-35 in
  McLennan, both carriageways mixed) into one line per direction.
- ``locate_on_reference`` gives any point (an existing sign, a ramp, a probe)
  its side of the road, its chainage along that side's line, and its offset.
- ``build_milepost_scale`` pins chainage to the highway authority's own
  mileposts (TxDOT reference markers), so a position reads "MP 331.4" instead
  of "12.3 km from wherever our download happened to start".

Invariants:
- Metric CRS only (same guard as F6).
- Each line keeps the direction of travel, so chainage 0 is where drivers
  enter it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely import line_merge
from shapely.geometry.base import BaseGeometry

from oohscout.track_a_spatial.corridor import _require_metric_crs

REFERENCE_LAYER = "reference_lines"

# US traffic drives on the right: northbound lanes are the east carriageway,
# so a point nearest the northbound line is on the east side of the highway.
_SIDE_OF: dict[str, str] = {"NB": "E", "SB": "W", "EB": "S", "WB": "N"}


def _travel_direction(line: BaseGeometry, north_south: bool) -> str:
    """Name the direction a one-way OSM segment is drawn in.

    OSM draws one-way roads in the direction of travel, so the first and last
    vertex tell us which way the traffic goes.
    """
    (x0, y0), (x1, y1) = line.coords[0], line.coords[-1]
    if north_south:
        return "NB" if y1 > y0 else "SB"
    return "EB" if x1 > x0 else "WB"


def build_reference_lines(lines_metric: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Merge highway segments into one continuous line per direction of travel.

    Pure function: no files, no network.

    Parameters
    ----------
    lines_metric:
        One-way highway segments in a metric CRS (typically
        ``Corridor.corridor_gdf_metric``), each drawn in its direction of
        travel as OSM does for divided highways.

    Returns
    -------
    gpd.GeoDataFrame
        Two rows (``NB``/``SB`` or ``EB``/``WB``) with ``direction``,
        ``side`` (the side of the highway that carriageway runs on),
        ``length_m`` and one LineString each.

    Raises
    ------
    ValueError
        If the input is not in a metric CRS, does not hold both directions of
        travel, or one direction does not join into a single line (a gap in
        the source data, or a branch that would have to be flipped to fit).
    """
    _require_metric_crs(lines_metric, "Highway lines")

    # A highway taller than it is wide runs north-south.
    min_x, min_y, max_x, max_y = lines_metric.total_bounds
    north_south = (max_y - min_y) >= (max_x - min_x)
    directions = lines_metric.geometry.apply(lambda g: _travel_direction(g, north_south))
    if directions.nunique() != 2:
        raise ValueError(
            f"Expected both directions of travel, found {sorted(directions.unique())}. "
            "An undivided road or a one-way subset cannot give one line per side."
        )

    rows = []
    for direction in sorted(directions.unique()):
        segments = lines_metric.geometry[directions == direction]
        # directed=True joins segments head-to-tail only, so the merged line
        # still runs in the direction of travel.
        merged = line_merge(segments.union_all(), directed=True)
        if merged.geom_type != "LineString":
            raise ValueError(
                f"{direction} segments do not join into one continuous line "
                f"({len(merged.geoms)} pieces). Check the source data for gaps."
            )
        rows.append(
            {
                "direction": direction,
                "side": _SIDE_OF[direction],
                "length_m": float(merged.length),
                "geometry": merged,
            }
        )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=lines_metric.crs)


def load_or_build_reference_lines(
    lines_metric: gpd.GeoDataFrame, cache_dir: Path, *, cache_slug: str
) -> gpd.GeoDataFrame:
    """Load cached reference lines, or build and cache them if missing."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{cache_slug}.gpkg"
    if cache_path.exists():
        return gpd.read_file(cache_path, layer=REFERENCE_LAYER)
    reference_lines = build_reference_lines(lines_metric)
    reference_lines.to_file(cache_path, layer=REFERENCE_LAYER, driver="GPKG")
    return reference_lines


def _check_same_metric_crs(a: gpd.GeoDataFrame, b: gpd.GeoDataFrame, label_a: str, label_b: str) -> None:
    _require_metric_crs(a, label_a)
    _require_metric_crs(b, label_b)
    if a.crs != b.crs:
        raise ValueError(
            f"{label_a} ({a.crs.to_string()}) and {label_b} ({b.crs.to_string()}) "
            "must use the same CRS."
        )


def locate_on_reference(
    points: gpd.GeoDataFrame, reference_lines: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Give each point its side of the highway, chainage and offset.

    A point belongs to the side whose reference line is nearest — a sign east
    of IH-35 is nearest the northbound (east) carriageway.

    Parameters
    ----------
    points:
        Point features in the same metric CRS as ``reference_lines``.
    reference_lines:
        Output of :func:`build_reference_lines`.

    Returns
    -------
    gpd.GeoDataFrame
        A copy of ``points`` with ``direction``, ``side``, ``chainage_m``
        (distance along that side's line from its start) and ``offset_m``
        (distance from the line).
    """
    _check_same_metric_crs(points, reference_lines, "Points", "Reference lines")
    lines = list(reference_lines.itertuples(index=False))
    distances = np.column_stack([points.distance(ref.geometry).to_numpy() for ref in lines])
    nearest = distances.argmin(axis=1)

    located = points.copy()
    located["direction"] = [lines[i].direction for i in nearest]
    located["side"] = [lines[i].side for i in nearest]
    located["chainage_m"] = [
        float(lines[i].geometry.project(geom)) for i, geom in zip(nearest, points.geometry)
    ]
    located["offset_m"] = distances[np.arange(len(points)), nearest]
    return located


@dataclass(frozen=True)
class MilepostScale:
    """Converts chainage on each reference line to the authority's mileposts.

    Built from reference markers (one point per milepost). Between two
    markers the milepost is interpolated linearly; outside the first/last
    marker it is held at the end value, so markers should extend past the
    study area.
    """

    chainages: dict[str, np.ndarray]
    mileposts: dict[str, np.ndarray]

    def at(self, direction: str, chainage_m: float | np.ndarray) -> np.ndarray:
        """Milepost at ``chainage_m`` on the ``direction`` line."""
        return np.interp(chainage_m, self.chainages[direction], self.mileposts[direction])


def build_milepost_scale(
    reference_lines: gpd.GeoDataFrame,
    markers: gpd.GeoDataFrame,
    *,
    marker_col: str,
    max_offset_m: float = 100.0,
) -> MilepostScale:
    """Project milepost markers onto each reference line and build the scale.

    Parameters
    ----------
    reference_lines:
        Output of :func:`build_reference_lines`.
    markers:
        Point markers for **one** roadbed of the same highway (e.g. TxDOT
        reference markers on IH-35's main roadbed), same metric CRS.
    marker_col:
        Column holding the milepost number.
    max_offset_m:
        Markers farther than this from a line are ignored for that line —
        a marker past the end of the line would otherwise project onto the
        line's end point and break the ordering.

    Raises
    ------
    ValueError
        If fewer than two markers lie along a line, or the mileposts do not
        run steadily one way along it (markers from two roadbeds or two
        highways mixed together).
    """
    _check_same_metric_crs(markers, reference_lines, "Markers", "Reference lines")

    chainages: dict[str, np.ndarray] = {}
    mileposts: dict[str, np.ndarray] = {}
    for ref in reference_lines.itertuples(index=False):
        near = markers[markers.distance(ref.geometry) <= max_offset_m]
        if len(near) < 2:
            raise ValueError(
                f"At least two milepost markers within {max_offset_m:g} m of the "
                f"{ref.direction} line are needed to build a scale."
            )
        ch = np.array([ref.geometry.project(g) for g in near.geometry])
        order = np.argsort(ch)
        ch, mp = ch[order], near[marker_col].astype(float).to_numpy()[order]
        steps = np.diff(mp)
        if not (np.all(steps > 0) or np.all(steps < 0)):
            raise ValueError(
                f"Mileposts do not run steadily along the {ref.direction} line; "
                "pass markers for a single roadbed of a single highway."
            )
        chainages[ref.direction] = ch
        mileposts[ref.direction] = mp
    return MilepostScale(chainages=chainages, mileposts=mileposts)
