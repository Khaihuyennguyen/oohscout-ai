"""F8 tests — the screening sieve and candidate placement.

Toy highway from test_reference: NB up x = +15, SB down x = -15, 10 km.
The legal numbers are the real Texas ones: 1,500 ft = 457.2 m spacing,
1,000 ft = 304.8 m from ramps (outside cities).
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from oohscout.rules import (
    TX_CERTIFIED_CITY,
    TX_FREEWAY_SPACING,
    TX_HIGHWAY_FACILITIES,
    WACO_CAP_AND_REPLACE,
    Rule,
)
from oohscout.track_a_spatial import (
    build_milepost_scale,
    build_reference_lines,
    merge_stretches,
    place_candidates,
    prepare_existing_signs,
    probe_points,
    screen_probes,
)
from shapely.geometry import LineString, Point, box

from .test_reference import MILE_M, TOY_CRS, toy_highway

SPACING = TX_FREEWAY_SPACING.distance_m  # 457.2
RAMP = TX_HIGHWAY_FACILITIES.distance_m  # 304.8
TOL = 15.0
STEP = 10.0


def _gdf(geoms: list, crs: int = TOY_CRS, **cols: list) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(cols, geometry=geoms, crs=crs)


def _empty(crs: int = TOY_CRS) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[], crs=crs)


def _cities(*rows: tuple[str, tuple[float, float, float, float]]) -> gpd.GeoDataFrame:
    if not rows:
        return _gdf([], name=[])
    return _gdf([box(*b) for _, b in rows], name=[n for n, _ in rows])


def _screen(
    *,
    signs: list[tuple[str, float, float]] = (),
    cities: gpd.GeoDataFrame | None = None,
    certified: dict[str, Rule] | None = None,
    ramps: list[LineString] = (),
    area: tuple[float, float, float, float] = (-5000, -1000, 5000, 11_000),
    etj: Rule | None = None,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    refs = build_reference_lines(toy_highway())
    sign_gdf = _gdf([Point(x, y) for _, x, y in signs], permit=[p for p, _, _ in signs])
    located = prepare_existing_signs(sign_gdf, refs, id_col="permit") if signs else sign_gdf.assign(
        direction=[], chainage_m=[]
    )
    screened = screen_probes(
        probe_points(refs, STEP),
        signs=located,
        sign_id_col="permit",
        study_area=_gdf([box(*area)]),
        cities=cities if cities is not None else _cities(),
        city_name_col="name",
        certified_cities=certified or {},
        ramps=_gdf(list(ramps)) if ramps else _empty(),
        spacing_rule=TX_FREEWAY_SPACING,
        facilities_rule=TX_HIGHWAY_FACILITIES,
        certified_city_rule=TX_CERTIFIED_CITY,
        etj_rule=etj,
        tolerance_m=TOL,
    )
    return refs, located, screened


def _at(screened: gpd.GeoDataFrame, direction: str, chainage: float) -> gpd.GeoSeries:
    rows = screened[screened["direction"] == direction]
    return rows.iloc[(rows["chainage_m"] - chainage).abs().argmin()]


# --- screening ---------------------------------------------------------------


def test_no_signs_no_cities_means_everything_is_open() -> None:
    _, _, screened = _screen()
    assert set(screened["screen"]) == {"open"}
    assert set(screened["regulatory_status"]) == {"REVIEW"}


def test_spots_too_close_to_an_existing_sign_are_blocked_on_that_side_only() -> None:
    _, _, screened = _screen(signs=[("S1", 80, 5000)])  # east side, NB chainage 5000
    blocked = _at(screened, "NB", 5000 + SPACING - TOL - 10)
    assert (blocked["screen"], blocked["regulatory_status"], blocked["blocker"]) == ("blocked", "FAIL", "S1")
    assert blocked["citation"] == "43 TAC §21.180"
    assert _at(screened, "NB", 5000 + SPACING + TOL + 10)["screen"] == "open"
    assert _at(screened, "SB", 5000)["screen"] == "open"  # the west side is unaffected


def test_a_band_around_the_limit_is_review_not_pass_or_fail() -> None:
    _, _, screened = _screen(signs=[("S1", 80, 5000)])
    edge = _at(screened, "NB", 5000 + SPACING)
    assert (edge["screen"], edge["regulatory_status"]) == ("near_limit", "REVIEW")


def test_ramps_block_outside_cities_only() -> None:
    ramp = LineString([(40, 2000), (40, 2300)])
    _, _, rural = _screen(ramps=[ramp])
    assert _at(rural, "NB", 2150)["screen"] == "blocked"
    assert _at(rural, "NB", 2300 + RAMP + TOL + 10)["screen"] == "open"

    town = _cities(("Smallville", (-500, 1000, 500, 3500)))
    _, _, urban = _screen(ramps=[ramp], cities=town)
    assert _at(urban, "NB", 2150)["screen"] == "open"
    assert _at(urban, "NB", 2150)["city"] == "Smallville"


def test_certified_city_hands_the_decision_to_the_city() -> None:
    waco = _cities(("Waco", (-500, 7000, 500, 9000)))
    _, _, screened = _screen(signs=[("S1", 80, 8000)], cities=waco, certified={"Waco": WACO_CAP_AND_REPLACE})
    inside = _at(screened, "NB", 8000)
    assert (inside["screen"], inside["regulatory_status"]) == ("city_rules", "REVIEW")
    assert "§28-1078" in inside["reason"]


def test_possible_etj_is_flagged_outside_the_certified_city() -> None:
    waco = _cities(("Waco", (-500, 7000, 500, 9000)))
    etj = Rule("ETJ", "test", "possible ETJ", 1000 / 0.3048, "https://example.org")  # 1 km reach
    _, _, screened = _screen(cities=waco, certified={"Waco": WACO_CAP_AND_REPLACE}, etj=etj)
    assert _at(screened, "NB", 6500)["screen"] == "possible_etj"
    assert _at(screened, "NB", 2000)["screen"] == "open"


def test_probes_outside_the_study_area_are_dropped() -> None:
    _, _, screened = _screen(area=(-5000, 0, 5000, 5000))
    assert screened.geometry.y.max() <= 5000


def test_nothing_is_ever_pass_or_legal() -> None:
    waco = _cities(("Waco", (-500, 7000, 500, 9000)))
    _, _, screened = _screen(signs=[("S1", 80, 3000)], cities=waco, certified={"Waco": WACO_CAP_AND_REPLACE})
    assert set(screened["regulatory_status"]) <= {"REVIEW", "FAIL"}
    assert not screened["reason"].str.contains("LEGAL").any()


@pytest.mark.parametrize("bad", [-1, float("nan")])
def test_bad_tolerance_is_rejected(bad: float) -> None:
    refs = build_reference_lines(toy_highway())
    with pytest.raises(ValueError, match="tolerance_m"):
        screen_probes(
            probe_points(refs, STEP), signs=_gdf([], permit=[], direction=[], chainage_m=[]), sign_id_col="permit",
            study_area=_gdf([box(-5000, -1000, 5000, 11_000)]), cities=_cities(), city_name_col="name",
            certified_cities={}, ramps=_empty(), spacing_rule=TX_FREEWAY_SPACING,
            facilities_rule=TX_HIGHWAY_FACILITIES, certified_city_rule=TX_CERTIFIED_CITY, tolerance_m=bad,
        )


def test_mismatched_crs_is_rejected() -> None:
    refs = build_reference_lines(toy_highway())
    with pytest.raises(ValueError, match="same CRS"):
        screen_probes(
            probe_points(refs, STEP), signs=_gdf([], permit=[], direction=[], chainage_m=[]), sign_id_col="permit",
            study_area=_gdf([box(-5000, -1000, 5000, 11_000)], crs=32615), cities=_cities(), city_name_col="name",
            certified_cities={}, ramps=_empty(), spacing_rule=TX_FREEWAY_SPACING,
            facilities_rule=TX_HIGHWAY_FACILITIES, certified_city_rule=TX_CERTIFIED_CITY,
        )


@pytest.mark.parametrize("bad", [0, -10, float("inf")])
def test_bad_probe_step_is_rejected(bad: float) -> None:
    with pytest.raises(ValueError, match="step_m"):
        probe_points(build_reference_lines(toy_highway()), bad)


# --- stretches -----------------------------------------------------------------


def test_stretches_cover_each_side_without_gaps() -> None:
    refs, _, screened = _screen(signs=[("S1", 80, 5000)])
    stretches = merge_stretches(screened, refs, STEP)
    for direction in ("NB", "SB"):
        side = stretches[stretches["direction"] == direction].sort_values("from_m")
        assert side["length_m"].sum() == pytest.approx(10_000)
        assert np.allclose(side["from_m"].to_numpy()[1:], side["to_m"].to_numpy()[:-1])
    nb = stretches[stretches["direction"] == "NB"].sort_values("from_m")
    assert nb["screen"].tolist() == ["open", "near_limit", "blocked", "near_limit", "open"]
    assert nb.iloc[2]["blockers"] == "S1"


# --- candidates ----------------------------------------------------------------


def _candidates(**kwargs) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    refs, located, screened = _screen(**kwargs)
    stretches = merge_stretches(screened, refs, STEP)
    return located, stretches, place_candidates(stretches, refs, TX_FREEWAY_SPACING, id_prefix="TOY")


def test_candidates_keep_the_legal_spacing_from_existing_signs() -> None:
    located, _, cands = _candidates(signs=[("S1", 80, 5000), ("S2", -80, 2000)])
    for direction in ("NB", "SB"):
        mine = cands[cands["direction"] == direction]["chainage_m"].to_numpy()
        signs = located[located["direction"] == direction]["chainage_m"].to_numpy()
        assert np.abs(mine[:, None] - signs[None, :]).min() >= SPACING


def test_candidates_keep_the_legal_spacing_from_each_other() -> None:
    _, _, cands = _candidates(signs=[("S1", 80, 5000)])
    for direction in ("NB", "SB"):
        mine = np.sort(cands[cands["direction"] == direction]["chainage_m"].to_numpy())
        assert np.diff(mine).min() >= SPACING - 1e-6
    # 10 km with nothing in the way fits floor(10 000 / 457.2) + 1 = 22 spots.
    assert (cands["direction"] == "SB").sum() == 22


def test_spacing_between_new_spots_holds_across_a_short_break() -> None:
    """A 100 m strip of certified city splits the road into two open stretches."""
    strip = _cities(("Waco", (-500, 5000, 500, 5100)))
    _, _, cands = _candidates(cities=strip, certified={"Waco": WACO_CAP_AND_REPLACE})
    for direction in ("NB", "SB"):
        mine = np.sort(cands[cands["direction"] == direction]["chainage_m"].to_numpy())
        assert np.diff(mine).min() >= SPACING - 1e-6


def test_candidates_only_come_from_open_stretches() -> None:
    waco = _cities(("Waco", (-500, 7000, 500, 9000)))
    _, _, cands = _candidates(cities=waco, certified={"Waco": WACO_CAP_AND_REPLACE})
    assert not cands.geometry.within(box(-500, 7000, 500, 9000)).any()
    assert set(cands["regulatory_status"]) == {"REVIEW"}
    assert cands["reason"].str.contains("§21.162").all()


def test_no_candidate_sits_on_a_city_line_next_to_a_ramp() -> None:
    """Real-data bug: a spot on the city line itself is outside the city, so the ramp rule applies."""
    town = _cities(("Smallville", (-500, 3500, 500, 6000)))
    ramp = LineString([(40, 3300), (40, 3450)])  # just outside the city
    _, _, cands = _candidates(cities=town, ramps=[ramp])
    outside = ~cands.geometry.within(box(-500, 3500, 500, 6000))
    assert (cands[outside].distance(ramp) >= RAMP).all()


def test_candidate_ids_use_mileposts_when_given() -> None:
    refs, _, screened = _screen()
    stretches = merge_stretches(screened, refs, STEP)
    markers = _gdf([Point(0, 0), Point(0, 10_000)], mp=[300.0, 300 + 10_000 / MILE_M])
    scale = build_milepost_scale(refs, markers, marker_col="mp")
    cands = place_candidates(stretches, refs, TX_FREEWAY_SPACING, id_prefix="IH35", mileposts=scale)
    first_east = cands[cands["side"] == "E"].sort_values("chainage_m").iloc[0]
    assert first_east["candidate_id"] == "IH35-E-MP300.00"
    assert cands["candidate_id"].is_unique
