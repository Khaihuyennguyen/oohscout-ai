"""Tests — existing signs selected, located and merged."""

from __future__ import annotations

import geopandas as gpd
import pytest
from oohscout.track_a_spatial import (
    build_reference_lines,
    prepare_existing_signs,
    select_highway_signs,
)
from shapely.geometry import Point

from .test_reference import TOY_CRS, toy_highway

IH35 = r"\b(?:IH|I|INTERSTATE)[\s-]*35\b"


def _signs(rows: list[tuple[str, float, float]], crs: int = TOY_CRS) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"permit": [r[0] for r in rows]}, geometry=[Point(r[1], r[2]) for r in rows], crs=crs
    )


def test_every_spelling_of_the_highway_is_matched() -> None:
    names = ["IH 35", "IH35", "I35", "Interstate 35", "4400 N IH 35", "I-35", "US 84", "IH 350", "SH 6"]
    signs = gpd.GeoDataFrame({"HWY": names}, geometry=[Point(0, i) for i in range(len(names))], crs=TOY_CRS)
    kept = select_highway_signs(signs, hwy_col="HWY", pattern=IH35)
    assert kept["HWY"].tolist() == ["IH 35", "IH35", "I35", "Interstate 35", "4400 N IH 35", "I-35"]


def test_back_to_back_permits_become_one_structure() -> None:
    refs = build_reference_lines(toy_highway())
    signs = _signs([("A", 80, 3000), ("B", 80, 3002), ("C", -80, 3000)])
    prepared = prepare_existing_signs(signs, refs, id_col="permit")
    assert len(prepared) == 2
    east = prepared[prepared["side"] == "E"].iloc[0]
    assert east["permits"] == "A, B"
    assert prepared[prepared["side"] == "W"].iloc[0]["permits"] == "C"


def test_signs_far_from_the_highway_are_dropped() -> None:
    refs = build_reference_lines(toy_highway())
    signs = _signs([("near", 80, 3000), ("far", 2000, 3000)])
    prepared = prepare_existing_signs(signs, refs, id_col="permit", max_offset_m=400)
    assert prepared["permits"].tolist() == ["near"]


def test_bad_merge_distance_is_rejected() -> None:
    refs = build_reference_lines(toy_highway())
    with pytest.raises(ValueError, match="merge_within_m"):
        prepare_existing_signs(_signs([("A", 80, 3000)]), refs, id_col="permit", merge_within_m=float("nan"))
