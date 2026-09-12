"""Texas outdoor-advertising rules used by the MVP screening (F9).

Sources were read on 2026-09-12 (summaries of 43 TAC Chapter 21 Subchapter I
via Cornell LII / Justia, the TxDOT certified-cities list, and the City of
Waco Code of Ordinances Ch. 28 Art. VIII). None has yet been checked
word-for-word by a person, so ``full_text_verified`` is False everywhere and
screening can only return FAIL or REVIEW.

Distances are kept in the unit the law uses (feet) and converted once, here.
"""

from __future__ import annotations

from dataclasses import dataclass

FT_TO_M = 0.3048

_LII = "https://www.law.cornell.edu/regulations/texas/43-Tex-Admin-Code-SS-21-"
_WACO = (
    "https://library.municode.com/tx/waco/codes/code_of_ordinances"
    "?nodeId=PTIICOOR_CH28ZO_ARTVIIISI"
)


@dataclass(frozen=True)
class Rule:
    """One regulatory rule, as data.

    Attributes
    ----------
    rule_id:
        Stable short name used in screening output.
    citation:
        Where the rule lives, e.g. ``"43 TAC §21.180"``.
    summary:
        Plain-English summary shown to the operator.
    distance_ft:
        The distance the rule uses, in feet, or None if it has none.
    source_url:
        Where the text was read.
    full_text_verified:
        True only after a person has checked the full legal text.
    """

    rule_id: str
    citation: str
    summary: str
    distance_ft: float | None
    source_url: str
    full_text_verified: bool = False

    @property
    def distance_m(self) -> float | None:
        """The rule's distance in metres (None if it has none)."""
        return None if self.distance_ft is None else self.distance_ft * FT_TO_M


TX_FREEWAY_SPACING = Rule(
    rule_id="TX-SPACING-FREEWAY",
    citation="43 TAC §21.180",
    summary=(
        "Permitted signs on the same side of a regulated freeway, including its frontage "
        "roads, may not be closer than 1,500 ft, measured along the right of way."
    ),
    distance_ft=1500,
    source_url="https://regulations.justia.com/states/texas/title-43/part-1/chapter-21/"
    "subchapter-i/division-1/section-21-180",
)

TX_HIGHWAY_FACILITIES = Rule(
    rule_id="TX-HIGHWAY-FACILITIES",
    citation="43 TAC §21.179",
    summary=(
        "Outside incorporated municipalities, no sign within 1,000 ft of an interchange, "
        "intersection at grade, rest area, ramp, or acceleration/deceleration lane."
    ),
    distance_ft=1000,
    source_url=f"{_LII}179",
)

TX_COMMERCIAL_AREA = Rule(
    rule_id="TX-COMMERCIAL-AREA",
    citation="43 TAC §21.162-§21.163",
    summary=(
        "A sign must stand in a zoned or unzoned commercial/industrial area "
        "(unzoned: 2+ commercial activities within 800 ft each way along the road, "
        "660 ft deep, 50% or less residential)."
    ),
    distance_ft=800,
    source_url=f"{_LII}162",
)

TX_PUBLIC_SPACES = Rule(
    rule_id="TX-PUBLIC-SPACES",
    citation="43 TAC §21.178",
    summary=(
        "A sign's centre may not be within 250 ft of a public space (park, forest, "
        "historic site…), nor within 1,000 ft along the right of way where it abuts the highway."
    ),
    distance_ft=250,
    source_url=f"{_LII}178",
)

TX_CERTIFIED_CITY = Rule(
    rule_id="TX-CERTIFIED-CITY",
    citation="43 TAC §21.200",
    summary="Inside a certified city, permission comes only from the city, under its own sign ordinance.",
    distance_ft=None,
    source_url=f"{_LII}200",
)

WACO_CAP_AND_REPLACE = Rule(
    rule_id="WACO-CAP-AND-REPLACE",
    citation="Waco Code §28-1078",
    summary=(
        "A new billboard in Waco's city limits or ETJ requires removing existing billboards "
        "totalling 2x its face area (conventional) or 4x (digital)."
    ),
    distance_ft=None,
    source_url=_WACO,
)

ETJ_REACH_LARGE_CITY = Rule(
    rule_id="TX-ETJ-5-MILES",
    citation="Tex. Loc. Gov't Code §42.021; Waco Code §28-1070",
    summary=(
        "A city of 100,000+ people can have an extraterritorial jurisdiction (ETJ) up to "
        "5 miles beyond its limits; Waco's billboard rules also apply there. The real "
        "boundary must be confirmed with the city."
    ),
    distance_ft=5 * 5280,
    source_url=_WACO,
)

# Rules the MVP cannot check automatically yet — listed on every open stretch.
NOT_YET_CHECKED: tuple[Rule, ...] = (TX_COMMERCIAL_AREA, TX_PUBLIC_SPACES)

ALL_RULES: tuple[Rule, ...] = (
    TX_FREEWAY_SPACING,
    TX_HIGHWAY_FACILITIES,
    TX_COMMERCIAL_AREA,
    TX_PUBLIC_SPACES,
    TX_CERTIFIED_CITY,
    WACO_CAP_AND_REPLACE,
    ETJ_REACH_LARGE_CITY,
)
