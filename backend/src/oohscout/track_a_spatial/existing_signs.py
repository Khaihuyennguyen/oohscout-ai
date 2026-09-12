"""Existing billboards placed on the highway (the input every spacing check needs).

Production module. Takes permit points from one or more sources (TxDOT
commercial-sign permits, certified-city permits), keeps the ones along the
target highway, gives each its side and chainage, and merges back-to-back /
double-faced structures that appear as two permits at the same spot (Waco
Code §28-1043 counts them as one sign).
"""

from __future__ import annotations

import math
import re

import geopandas as gpd
import numpy as np

from oohscout.track_a_spatial.reference import locate_on_reference


def select_highway_signs(signs: gpd.GeoDataFrame, *, hwy_col: str, pattern: str) -> gpd.GeoDataFrame:
    """Keep signs whose highway field matches ``pattern`` (a regular expression, case-insensitive).

    Permit data spells one road many ways — TxDOT has "IH 35", "IH35", "I35",
    "Interstate 35" and "4400 N IH 35" for IH-35 — so match a pattern, not a string.
    """
    regex = re.compile(pattern, re.IGNORECASE)
    keep = signs[hwy_col].astype(str).apply(lambda v: bool(regex.search(v)))
    return signs[keep].copy()


def prepare_existing_signs(
    signs_metric: gpd.GeoDataFrame,
    reference_lines: gpd.GeoDataFrame,
    *,
    id_col: str,
    max_offset_m: float = 400.0,
    merge_within_m: float = 5.0,
) -> gpd.GeoDataFrame:
    """Locate signs on the reference lines, drop strays, merge back-to-back pairs.

    Parameters
    ----------
    signs_metric:
        Sign points already filtered to the highway, in the lines' metric CRS.
    reference_lines:
        Output of :func:`~oohscout.track_a_spatial.reference.build_reference_lines`.
    id_col:
        Permit-number column, kept as the sign's id.
    max_offset_m:
        Signs farther than this from the highway are dropped (a wrong
        coordinate, or a sign on a crossing road).
    merge_within_m:
        Two permits on the same side within this distance of each other along
        the road are one structure; the first is kept, ``permits`` lists all.

    Returns
    -------
    gpd.GeoDataFrame
        One row per structure with ``direction``, ``side``, ``chainage_m``,
        ``offset_m`` and ``permits``.
    """
    if not (math.isfinite(merge_within_m) and merge_within_m >= 0):
        raise ValueError(f"merge_within_m must be a real number >= 0, got {merge_within_m!r}")
    located = locate_on_reference(signs_metric, reference_lines)
    located = located[located["offset_m"] <= max_offset_m]
    located = located.sort_values(["direction", "chainage_m"]).reset_index(drop=True)

    structure = np.zeros(len(located), dtype=int)
    current = -1
    previous_direction, previous_chainage = None, -np.inf
    for i, (direction, chainage) in enumerate(zip(located["direction"], located["chainage_m"])):
        if direction != previous_direction or chainage - previous_chainage > merge_within_m:
            current += 1
        structure[i] = current
        previous_direction, previous_chainage = direction, chainage
    located["structure"] = structure
    located[id_col] = located[id_col].astype(str)

    permits = located.groupby("structure")[id_col].apply(lambda ids: ", ".join(ids))
    merged = located.drop_duplicates("structure", keep="first").copy()
    merged["permits"] = merged["structure"].map(permits)
    return merged.drop(columns="structure").reset_index(drop=True)
