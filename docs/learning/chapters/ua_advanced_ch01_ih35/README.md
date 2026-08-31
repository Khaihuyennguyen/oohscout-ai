# UA Advanced Chapter 1 — IH-35 Centerline (F2)

**Status:** F2 ✅ SHIPPED 2026-08-29 on `feature/f2-ih35-centerline`
**Current scope:** Feature 2 only — IH-35 highway centerline for McLennan County
**Production module:** [backend/src/oohscout/track_a_spatial/corridor.py](../../../../backend/src/oohscout/track_a_spatial/corridor.py)

## Work in this chapter folder — the 5-file convention

Same shape as [F1's chapter folder](../ua_advanced_ch01_setup/README.md). For F2, the 01/02 files are short pointers back to F1 because the underlying Milan chapter is the same — only the OSM tag and geometry-type filter differ.

1. `01_milan_original.ipynb` — pointer to F1's Milan retype + the two-line substitution table.
2. `02_milan_explanation.md` — pointer to F1's deep Milan explanation + the F2-specific gotcha (OSMnx duplicate ways).
3. `03_oohscout_adaptation.ipynb` — runnable McLennan IH-35 adaptation.
4. `04_adaptation_explanation.md` — cell-by-cell WHAT/WHY/HOW.
5. `05_code_along.ipynb` — blank scaffold to retype F2 from memory.

## F2 completion gate — all green ✅

- ✅ 245 IH-35 segments returned from Overpass inside McLennan.
- ✅ Every geometry is `LineString` (no accidental `Point` / `Polygon`).
- ✅ `osmid` is unique after dedupe (4 exact-duplicate rows collapsed).
- ✅ Total length 131 km — includes both directions + frontage segments carrying the `I 35` ref.
- ✅ Projected to EPSG:32614.
- ✅ Cached at `backend/data/processed/mclennan_ih35_centerline.gpkg`.
- ✅ Visual check `backend/data/processed/mclennan_ih35_f2_check.png` shows red lines tracing IH-35 diagonally through Waco.
- ✅ Production module exposes `load_or_build_highway_centerline()` and the `Corridor` dataclass.
- ✅ Pytest at `backend/tests/track_a/test_corridor.py` — all tests pass.

**Next feature:** F6 (corridor buffer) or F7 (candidate site sampling) — both depend on F2's output.
