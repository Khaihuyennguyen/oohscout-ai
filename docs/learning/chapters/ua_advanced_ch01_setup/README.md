# UA Advanced Chapter 1 — Setting Up

**Status:** In progress on `feature/f1-retargetable-study-area`
**Current scope:** Feature 1 only — the McLennan County study-area pattern

## Work in this chapter folder

1. `01_milan_original.ipynb` — retype Milan's purchased notebook yourself; do not copy it into Git.
2. `02_milan_explanation.md` — mentor explanation for the setup and study-area cells.
3. `03_oohscout_adaptation.ipynb` — runnable McLennan County adaptation for F1.
4. `04_adaptation_explanation.md` — cell-by-cell explanation of the F1 adaptation.

## Feature 1 completion gate

Feature 1 remains **in progress** until you run the adaptation and confirm all of the following:

- `admin_gdf` contains exactly one Polygon or MultiPolygon record.
- `study_area` is projected in EPSG:32614 before its area is measured.
- The measured administrative area is within 5% of the published reference area.
- The boundary appears in the correct place on the Esri World Imagery basemap.
- The projected boundary is cached as a GeoPackage in `backend/data/processed/`.

Do not begin Feature 2 until the previous cell in the adaptation produces sensible output.
