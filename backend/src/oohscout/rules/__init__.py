"""Verified-rules layer (F9) — regulatory rules as data, each with its citation.

Track A reads these tables; it never asks an LLM what the law says. Every rule
records whether a person has checked it against the full legal text
(``full_text_verified``). Until that is True, screening may say FAIL or
REVIEW, but never PASS.
"""

from oohscout.rules.texas import (
    ALL_RULES,
    ETJ_REACH_LARGE_CITY,
    FT_TO_M,
    NOT_YET_CHECKED,
    TX_CERTIFIED_CITY,
    TX_COMMERCIAL_AREA,
    TX_FREEWAY_SPACING,
    TX_HIGHWAY_FACILITIES,
    TX_PUBLIC_SPACES,
    WACO_CAP_AND_REPLACE,
    Rule,
)

__all__ = [
    "ALL_RULES",
    "ETJ_REACH_LARGE_CITY",
    "FT_TO_M",
    "NOT_YET_CHECKED",
    "TX_CERTIFIED_CITY",
    "TX_COMMERCIAL_AREA",
    "TX_FREEWAY_SPACING",
    "TX_HIGHWAY_FACILITIES",
    "TX_PUBLIC_SPACES",
    "WACO_CAP_AND_REPLACE",
    "Rule",
]
