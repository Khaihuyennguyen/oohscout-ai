"""F9 tests — the Texas rule table is data with citations, in the right units."""

from __future__ import annotations

import pytest
from oohscout.rules import ALL_RULES, FT_TO_M, TX_FREEWAY_SPACING, TX_HIGHWAY_FACILITIES


def test_feet_are_converted_to_metres_once() -> None:
    assert FT_TO_M == 0.3048
    assert TX_FREEWAY_SPACING.distance_m == pytest.approx(457.2)
    assert TX_HIGHWAY_FACILITIES.distance_m == pytest.approx(304.8)


@pytest.mark.parametrize("rule", ALL_RULES, ids=lambda r: r.rule_id)
def test_every_rule_is_cited_and_sourced(rule) -> None:
    assert rule.citation and rule.summary
    assert rule.source_url.startswith("https://")
    assert "LEGAL" not in rule.summary


def test_rule_ids_are_unique() -> None:
    ids = [r.rule_id for r in ALL_RULES]
    assert len(ids) == len(set(ids))


def test_no_rule_claims_verification_it_has_not_had() -> None:
    """Flip a rule's flag only after a person checks the full legal text."""
    assert not any(r.full_text_verified for r in ALL_RULES)
