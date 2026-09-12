"""F8 — preliminary screening sieve along each side of a highway.

Production module. Instead of guessing candidate spots, start with every
metre of each side of the road and remove what the rules forbid:

1. ``probe_points`` walks each reference line in small steps (default 10 m).
2. ``screen_probes`` labels every probe:
   - ``city_rules``   inside a certified city → the city's ordinance decides (REVIEW)
   - ``blocked``      closer than the legal spacing to an existing same-side sign,
                      or (outside cities) too close to a ramp/interchange (FAIL)
   - ``near_limit``   within ±tolerance of one of those limits (REVIEW) —
                      positions in the data are a little bit wrong
   - ``possible_etj`` outside every city but within reach of a certified city's
                      extraterritorial jurisdiction (REVIEW)
   - ``open``         passed the automated checks (REVIEW — other rules, the
                      parcel and a person still have to confirm it)
3. ``merge_stretches`` joins neighbouring probes with the same label into stretches.
4. ``place_candidates`` puts candidate spots in the open stretches, never
   closer to each other than the legal spacing.

Nothing is ever PASS here, and nothing is ever "LEGAL": the rule table is not
yet verified word-for-word (see ``oohscout.rules``).
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import geopandas as gpd
import numpy as np
from shapely.ops import substring

from oohscout.project import RegulatoryStatus
from oohscout.rules import NOT_YET_CHECKED, Rule
from oohscout.track_a_spatial.reference import MilepostScale, _check_same_metric_crs

OPEN = "open"
BLOCKED = "blocked"
NEAR_LIMIT = "near_limit"
CITY_RULES = "city_rules"
POSSIBLE_ETJ = "possible_etj"

_STATUS_OF: dict[str, str] = {
    OPEN: RegulatoryStatus.REVIEW.value,
    NEAR_LIMIT: RegulatoryStatus.REVIEW.value,
    CITY_RULES: RegulatoryStatus.REVIEW.value,
    POSSIBLE_ETJ: RegulatoryStatus.REVIEW.value,
    BLOCKED: RegulatoryStatus.FAIL.value,
}

OPEN_REASON = (
    "Passed automated preliminary screening (spacing, highway facilities). Not yet checked: "
    + "; ".join(f"{r.citation} ({r.rule_id})" for r in NOT_YET_CHECKED)
    + "; parcel and landowner. Final eligibility requires municipal/professional verification."
)


def probe_points(reference_lines: gpd.GeoDataFrame, step_m: float = 10.0) -> gpd.GeoDataFrame:
    """One point every ``step_m`` metres along each reference line.

    Probes sit at ``step_m / 2``, ``1.5 * step_m``, … so each stands for the
    step around it.
    """
    if not (math.isfinite(step_m) and step_m > 0):
        raise ValueError(f"step_m must be a real number > 0, got {step_m!r}")
    rows = []
    for ref in reference_lines.itertuples(index=False):
        for chainage in np.arange(step_m / 2, ref.geometry.length, step_m):
            rows.append(
                {
                    "direction": ref.direction,
                    "side": ref.side,
                    "chainage_m": float(chainage),
                    "geometry": ref.geometry.interpolate(chainage),
                }
            )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=reference_lines.crs)


def _nearest_along(
    chainages: np.ndarray, targets: np.ndarray, target_ids: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Distance along the line from each chainage to the nearest target, and its id."""
    if len(targets) == 0:
        return np.full(len(chainages), np.inf), np.full(len(chainages), "", dtype=object)
    order = np.argsort(targets)
    targets, target_ids = targets[order], target_ids[order]
    right = np.clip(np.searchsorted(targets, chainages), 0, len(targets) - 1)
    left = np.clip(right - 1, 0, len(targets) - 1)
    d_left, d_right = np.abs(chainages - targets[left]), np.abs(chainages - targets[right])
    use_left = d_left <= d_right
    return np.where(use_left, d_left, d_right), np.where(use_left, target_ids[left], target_ids[right])


def screen_probes(
    probes: gpd.GeoDataFrame,
    *,
    signs: gpd.GeoDataFrame,
    sign_id_col: str,
    study_area: gpd.GeoDataFrame,
    cities: gpd.GeoDataFrame,
    city_name_col: str,
    certified_cities: Mapping[str, Rule],
    ramps: gpd.GeoDataFrame,
    spacing_rule: Rule,
    facilities_rule: Rule,
    certified_city_rule: Rule,
    etj_rule: Rule | None = None,
    tolerance_m: float = 15.0,
) -> gpd.GeoDataFrame:
    """Label every probe with a screening outcome.

    Parameters
    ----------
    probes:
        Output of :func:`probe_points`.
    signs:
        Existing signs already passed through
        :func:`~oohscout.track_a_spatial.reference.locate_on_reference`
        (need ``direction`` and ``chainage_m``).
    sign_id_col:
        Column naming each sign (a permit number) — reported as the blocker.
    study_area:
        Probes outside it are dropped.
    cities:
        Incorporated city limits; ``city_name_col`` holds the name.
    certified_cities:
        City name → the rule that applies inside it (e.g. ``{"Waco": WACO_CAP_AND_REPLACE}``).
    ramps:
        Ramp / interchange lines. The facilities rule only applies outside cities.
    spacing_rule, facilities_rule, certified_city_rule:
        Rules from :mod:`oohscout.rules` (their ``distance_m`` is used).
    etj_rule:
        If given, probes outside every city but within ``etj_rule.distance_m``
        of a certified city are flagged ``possible_etj``.
    tolerance_m:
        Half-width of the ``near_limit`` band around each limit.

    Returns
    -------
    gpd.GeoDataFrame
        Probes inside the study area with ``city``, ``screen``,
        ``regulatory_status``, ``reason``, ``citation``, ``blocker`` and
        ``nearest_sign_m`` columns.
    """
    for gdf, label in [(signs, "Signs"), (study_area, "Study area"), (cities, "Cities"), (ramps, "Ramps")]:
        _check_same_metric_crs(gdf, probes, label, "Probes")
    if not (math.isfinite(tolerance_m) and tolerance_m >= 0):
        raise ValueError(f"tolerance_m must be a real number >= 0, got {tolerance_m!r}")

    area = study_area.geometry.union_all()
    out = probes[probes.within(area)].reset_index(drop=True)
    n = len(out)

    # Which city (if any) each probe is in.
    joined = gpd.sjoin(out[["geometry"]], cities[[city_name_col, "geometry"]], predicate="within", how="left")
    city = joined.groupby(level=0)[city_name_col].first().reindex(range(n))
    out["city"] = city.where(city.notna(), None).to_numpy()
    in_city = out["city"].notna().to_numpy()

    # Spacing: distance along the same side to the nearest existing sign.
    nearest_m = np.full(n, np.inf)
    nearest_id = np.full(n, "", dtype=object)
    for direction in out["direction"].unique():
        mask = (out["direction"] == direction).to_numpy()
        same_side = signs[signs["direction"] == direction]
        d, ids = _nearest_along(
            out.loc[mask, "chainage_m"].to_numpy(),
            same_side["chainage_m"].to_numpy(dtype=float),
            same_side[sign_id_col].astype(str).to_numpy(dtype=object),
        )
        nearest_m[mask], nearest_id[mask] = d, ids
    out["nearest_sign_m"] = nearest_m

    # Highway facilities: straight-line distance to the nearest ramp.
    ramp_m = np.full(n, np.inf)
    if len(ramps):
        pairs, dist = ramps.sindex.nearest(out.geometry, return_distance=True, return_all=False)
        ramp_m[pairs[0]] = dist

    spacing_m, facilities_m = spacing_rule.distance_m, facilities_rule.distance_m
    screen = np.full(n, OPEN, dtype=object)
    reason = np.full(n, OPEN_REASON, dtype=object)
    citation = np.full(n, "", dtype=object)
    blocker = np.full(n, "", dtype=object)

    def label(mask: np.ndarray, value: str, rule: Rule, text: str, who: np.ndarray | str) -> None:
        screen[mask], reason[mask], citation[mask] = value, text, rule.citation
        blocker[mask] = who[mask] if isinstance(who, np.ndarray) else who

    # Lowest priority first; later labels overwrite earlier ones.
    if etj_rule is not None and certified_cities:
        certified_shape = cities[cities[city_name_col].isin(list(certified_cities))].geometry.union_all()
        near_certified = (~in_city) & (out.distance(certified_shape).to_numpy() <= etj_rule.distance_m)
        label(near_certified, POSSIBLE_ETJ, etj_rule, etj_rule.summary, "")

    facility_rule_applies = ~in_city
    near_ramp = facility_rule_applies & (np.abs(ramp_m - facilities_m) <= tolerance_m)
    label(near_ramp, NEAR_LIMIT, facilities_rule, f"Within ±{tolerance_m:g} m of the ramp limit. {facilities_rule.summary}", "ramp")
    near_sign = np.abs(nearest_m - spacing_m) <= tolerance_m
    label(near_sign, NEAR_LIMIT, spacing_rule, f"Within ±{tolerance_m:g} m of the spacing limit. {spacing_rule.summary}", nearest_id)

    too_close_ramp = facility_rule_applies & (ramp_m < facilities_m - tolerance_m)
    label(too_close_ramp, BLOCKED, facilities_rule, facilities_rule.summary, "ramp")
    too_close_sign = nearest_m < spacing_m - tolerance_m
    label(too_close_sign, BLOCKED, spacing_rule, spacing_rule.summary, nearest_id)

    for name, city_rule in certified_cities.items():
        inside = (out["city"] == name).to_numpy()
        label(
            inside,
            CITY_RULES,
            certified_city_rule,
            f"{name} is a certified city: {certified_city_rule.summary} {city_rule.citation}: {city_rule.summary}",
            name,
        )

    out["screen"] = screen
    out["regulatory_status"] = [_STATUS_OF[s] for s in screen]
    out["reason"] = reason
    out["citation"] = citation
    out["blocker"] = blocker
    return out


def merge_stretches(
    screened: gpd.GeoDataFrame, reference_lines: gpd.GeoDataFrame, step_m: float = 10.0
) -> gpd.GeoDataFrame:
    """Join neighbouring probes with the same outcome into stretches of road.

    Returns one row per stretch: ``direction``, ``side``, ``screen``,
    ``regulatory_status``, ``reason``, ``citation``, ``blockers`` (unique,
    comma-separated), ``from_m`` / ``to_m`` (the stretch's extent, half a
    step past its end probes), ``first_probe_m`` / ``last_probe_m`` (the
    outermost positions actually checked), ``length_m`` and the stretch as a
    LineString cut from the reference line.
    """
    lines = {ref.direction: ref for ref in reference_lines.itertuples(index=False)}
    rows = []
    for direction, group in screened.sort_values(["direction", "chainage_m"]).groupby("direction"):
        ch = group["chainage_m"].to_numpy()
        # fillna first: a missing city must compare equal to the next missing city.
        key = group["screen"] + "|" + group["citation"] + "|" + group["city"].fillna("").astype(str)
        new_run = (key != key.shift()).to_numpy() | np.r_[True, np.diff(ch) > step_m * 1.5]
        run_id = np.cumsum(new_run)
        line = lines[direction].geometry
        for _, run in group.groupby(run_id):
            from_m = max(0.0, run["chainage_m"].iloc[0] - step_m / 2)
            to_m = min(line.length, run["chainage_m"].iloc[-1] + step_m / 2)
            first = run.iloc[0]
            blockers = sorted({b for b in run["blocker"] if b})
            rows.append(
                {
                    "direction": direction,
                    "side": first["side"],
                    "city": first["city"],
                    "screen": first["screen"],
                    "regulatory_status": first["regulatory_status"],
                    "reason": first["reason"],
                    "citation": first["citation"],
                    "blockers": ", ".join(blockers),
                    "from_m": float(from_m),
                    "to_m": float(to_m),
                    "first_probe_m": float(run["chainage_m"].iloc[0]),
                    "last_probe_m": float(run["chainage_m"].iloc[-1]),
                    "length_m": float(to_m - from_m),
                    "geometry": substring(line, from_m, to_m),
                }
            )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=screened.crs)


def place_candidates(
    stretches: gpd.GeoDataFrame,
    reference_lines: gpd.GeoDataFrame,
    spacing_rule: Rule,
    *,
    id_prefix: str,
    mileposts: MilepostScale | None = None,
) -> gpd.GeoDataFrame:
    """Place candidate spots in the open stretches, at least the legal spacing apart.

    Walks each side in the direction of travel and puts a spot at the first
    checked position of each open stretch, then every ``spacing_rule.distance_m``
    metres up to its last checked position — never closer than that to the
    previous spot, even across two open stretches. Spots never sit on a
    stretch's outer edge: that edge is shared with the neighbouring stretch
    (a city line, a blocked zone) and was not itself checked.

    IDs read ``<prefix>-<side>-MP<milepost>`` when a milepost scale is given
    (e.g. ``IH35-E-MP331.42``), else ``<prefix>-<side>-KM<km along the line>``.
    """
    spacing_m = spacing_rule.distance_m
    lines = {ref.direction: ref.geometry for ref in reference_lines.itertuples(index=False)}
    rows = []
    open_stretches = stretches[stretches["screen"] == OPEN].sort_values(["direction", "from_m"])
    for direction, group in open_stretches.groupby("direction"):
        last = -np.inf
        for stretch in group.itertuples(index=False):
            position = max(stretch.first_probe_m, last + spacing_m)
            while position <= stretch.last_probe_m:
                rows.append(
                    {
                        "direction": direction,
                        "side": stretch.side,
                        "chainage_m": float(position),
                        "regulatory_status": RegulatoryStatus.REVIEW.value,
                        "reason": OPEN_REASON,
                        "geometry": lines[direction].interpolate(position),
                    }
                )
                last = position
                position += spacing_m

    candidates = gpd.GeoDataFrame(rows, geometry="geometry", crs=stretches.crs)
    if candidates.empty:
        candidates["candidate_id"] = []
        return candidates
    if mileposts is not None:
        candidates["milepost"] = [
            float(mileposts.at(d, c)) for d, c in zip(candidates["direction"], candidates["chainage_m"])
        ]
        candidates["candidate_id"] = [
            f"{id_prefix}-{s}-MP{mp:06.2f}" for s, mp in zip(candidates["side"], candidates["milepost"])
        ]
    else:
        candidates["candidate_id"] = [
            f"{id_prefix}-{s}-KM{c / 1000:06.2f}" for s, c in zip(candidates["side"], candidates["chainage_m"])
        ]
    assert candidates["candidate_id"].is_unique, "candidate_id must be unique."
    return candidates
