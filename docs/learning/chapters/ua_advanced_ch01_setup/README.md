# UA Advanced Chapter 1 — Setting Up

**Status:** F1 ✅ SHIPPED 2026-08-29 on `feature/f1-retargetable-study-area`
**Current scope:** Feature 1 only — the McLennan County study-area pattern
**Production module:** [backend/src/oohscout/track_a_spatial/study_area.py](../../../../backend/src/oohscout/track_a_spatial/study_area.py)

## Work in this chapter folder — the 5-file convention

Every feature branch reuses this same file pattern inside its own chapter folder.

1. `01_milan_original.ipynb` — retype Milan's purchased notebook yourself; do not copy it into Git.
2. `02_milan_explanation.md` — mentor explanation for the setup and study-area cells.
3. `03_oohscout_adaptation.ipynb` — runnable McLennan County adaptation.
4. `04_adaptation_explanation.md` — cell-by-cell deep explanation (what/why/how) of the adaptation.
5. `05_code_along.ipynb` — blank scaffold to retype the adaptation from memory. Proves you own the pattern.

## Feature 1 completion gate — all green ✅

- ✅ `admin_gdf` contains exactly one Polygon record.
- ✅ `study_area` is projected in EPSG:32614 before its area is measured.
- ✅ Measured area (2,747.3 km²) is 0.05% off the Census reference (2,746.0 km²).
- ✅ Boundary visually confirmed on Esri World Imagery — see `backend/data/processed/mclennan_f1_check.png`.
- ✅ Projected boundary cached at `backend/data/processed/mclennan_county_study_area.gpkg`.
- ✅ Production module exposes `load_or_build_study_area()` and `assert_contains_point()` for FastAPI, agent tools, and tests.

**Next feature:** F2 — IH-35 highway centerline for McLennan County. New branch `feature/f2-ih35-centerline`. Same 5-file convention in its own chapter folder.
