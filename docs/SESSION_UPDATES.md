# OOHScout AI — Session Updates

Chronological log of what actually shipped, per session. Append newest at the top. Every entry links to concrete files so a future collaborator can reconstruct the state.

---

## 2026-08-29 — F1a Installable Package SHIPPED

**Branch:** `feature/f1a-installable-package`
**Feature shipped:** F1a (make `backend/src/oohscout/` a real installable Python package with pytest smoke tests)
**PRD reference:** [docs/PRD.md § 6 F1a](PRD.md)

### What was built

- **[pyproject.toml](../pyproject.toml)** — added `[build-system] requires = ["hatchling"]`; removed `[tool.uv] package = false`; added `[tool.hatch.build.targets.wheel]` with `packages = ["backend/src/oohscout"]` and a `sources` map (`"backend/src" = ""`) so the wheel installs `oohscout` as the top-level import name despite the non-standard `backend/src/` layout; added `pytest>=9.1.1` to `[dependency-groups] dev`; added `[tool.pytest.ini_options]` with `testpaths = ["backend/tests"]` and `--basetemp=.pytest_tmp` (works around a Windows AppData ACL quirk where pytest can't enumerate its default temp dir).
- **[backend/tests/track_a/test_study_area.py](../backend/tests/track_a/test_study_area.py)** — 5 pytests: one-polygon returned, metric CRS matches request, area within 5% of Census reference, Waco courthouse inside boundary (Option B), wrong reference area raises AssertionError (negative test).
- **[backend/tests/track_a/__init__.py](../backend/tests/track_a/__init__.py)** — empty package marker for pytest discovery.
- **[.gitignore](../.gitignore)** — added `.pytest_tmp/`.

### Evidence of shipping

| Gate item | Result |
|---|---|
| `pyproject.toml` build-system + hatch config | ✅ hatchling wired; `uv sync` builds `oohscout-ai==0.0.1` |
| `uv sync` completes | ✅ 1 package installed (editable) |
| `from oohscout.track_a_spatial import load_or_build_study_area` | ✅ Prints `module: importable OK` |
| Pytest McLennan area + Waco containment | ✅ **5 passed in 8.07s** |
| Notebook / module parity | ✅ Both compute 2,747.33 km² for McLennan |

### What this unlocks

Every future feature (F2 onward) can ship a real production module in `backend/src/oohscout/<track>/<feature>.py` and be imported from FastAPI, agent tools, and pytest immediately. The dual-track discipline (notebook = learning, module = production) is now enforceable — a parity test can be written for any future feature the same way `test_study_area.py` currently proves F1 works outside the notebook.

### Next branch

`feature/f2-ih35-centerline` — same 5-file convention in `docs/learning/chapters/ua_advanced_ch01_ih35/`, applied to IH-35 highway centerline for McLennan. Production module: `backend/src/oohscout/track_a_spatial/corridor.py` with `load_or_build_ih35_centerline(admin_poly, cache_dir)`. Because F1a is done, this module will be importable + testable from day one.

---

## 2026-08-29 — F1 Retargetable Study Area SHIPPED

**Branch:** `feature/f1-retargetable-study-area`
**Feature shipped:** F1 (Retargetable Study Area for McLennan County, Texas)
**PRD reference:** [docs/PRD.md § 6 F1](PRD.md)

### What was built

- **Learning notebook (Milan retype):** [docs/learning/chapters/ua_advanced_ch01_setup/01_milan_original.ipynb](learning/chapters/ua_advanced_ch01_setup/01_milan_original.ipynb) — hand-retyped Milan's Manhattan Chapter 1 setup + study-area section (through the building-fetch cell). Executed outputs confirm the pattern works end-to-end on Manhattan (86.7 km², 46,319 buildings).
- **Mentor explanation:** [docs/learning/chapters/ua_advanced_ch01_setup/02_milan_explanation.md](learning/chapters/ua_advanced_ch01_setup/02_milan_explanation.md) — full line-by-line explanation of Milan's original with a translation table (Manhattan → McLennan).
- **F1 adaptation notebook:** [docs/learning/chapters/ua_advanced_ch01_setup/03_oohscout_adaptation.ipynb](learning/chapters/ua_advanced_ch01_setup/03_oohscout_adaptation.ipynb) — McLennan County, EPSG:32614, GeoPackage cache, repo-root detection, assertions, Esri visual check with PNG save.
- **Deep code walkthrough:** [docs/learning/chapters/ua_advanced_ch01_setup/04_adaptation_explanation.md](learning/chapters/ua_advanced_ch01_setup/04_adaptation_explanation.md) — what, why, how per cell (mentor-mode).
- **Code-along companion:** [docs/learning/chapters/ua_advanced_ch01_setup/05_code_along.ipynb](learning/chapters/ua_advanced_ch01_setup/05_code_along.ipynb) — blank notebook with prompts to retype F1 from memory.
- **Production module:** [backend/src/oohscout/track_a_spatial/study_area.py](../backend/src/oohscout/track_a_spatial/study_area.py) — importable `load_or_build_study_area(place, crs_metric, cache_dir)` function. FastAPI and agent tools import from here, not the notebook.

### Evidence of shipping

| Gate item | Result |
|---|---|
| `len(admin_gdf) == 1` | ✅ 1 record |
| Geometry Polygon/MultiPolygon, valid, non-empty | ✅ Passed |
| `admin_gdf_metric.crs.to_epsg() == 32614` | ✅ EPSG:32614 |
| Area within 5% of Census reference (2,746.0 km²) | ✅ 2,747.3 km² — **0.05% off** |
| Boundary visually surrounds McLennan on Esri | ✅ [backend/data/processed/mclennan_f1_check.png](../backend/data/processed/mclennan_f1_check.png) |
| GeoPackage cached | ✅ [backend/data/processed/mclennan_county_study_area.gpkg](../backend/data/processed/mclennan_county_study_area.gpkg) |

### Bugs found in Milan retype (not blocking F1)

- Cell 12 typo: `buidings = buildings[is_polygon].copy()` — filter result discarded. Fix goes into F2 branch where buildings-equivalent (highway) work happens.
- Missing cells vs. what `02_milan_explanation.md` documents: attribute trim + `assert osmid.is_unique`, GeoJSON export, entire Section 1.4 (`TEST_BBOX` DEV_MODE). These belong to F2/F5, not F1.

### What this unlocks

F1's outputs `admin_poly` (WGS 84) and `study_area` (EPSG:32614) are the required inputs for:

- **F2** — IH-35 highway centerline via `ox.features_from_polygon(admin_poly, tags={"highway": ["motorway"]})`
- **F5** — DEV_MODE `TEST_BBOX` subset for Waco urban corridor
- **F10** — Advertiser POI query bounded by `admin_poly`
- **F16** — Drive-time isochrones inside `admin_poly`
- **F19** — Zoning polygons clipped to `admin_poly`
- **F21** — Sentinel-2 NDVI raster clipped to `admin_poly`
- **F43** — GeoPackage per-candidate exports (format already proven)

### Known gap — F1a queued next

The production module `study_area.py` was written but is **not importable** because [pyproject.toml](../pyproject.toml) sets `[tool.uv] package = false`. Verified by running `uv run python -c "from oohscout.track_a_spatial import load_or_build_study_area"` → `ModuleNotFoundError: No module named 'oohscout'`.

This means:
- The notebook is fully functional and F1's PRD acceptance is met.
- The module exists on disk but nothing outside a notebook can import it.
- Every future feature (F2+) would replicate this orphan-file problem if not fixed.

**Decision (2026-08-29):** Ship F1 per its original PRD acceptance and split the packaging fix into **F1a** (small, tightly-scoped) rather than expanding F1's scope. F1a is the next branch to open, before F2.

### Next branches, in order

1. **`feature/f1a-installable-package`** — flip `[tool.uv] package = false` → `true`, add `[build-system]` + hatch config pointing at `backend/src/oohscout/`, `uv sync`, add `backend/tests/track_a/test_study_area.py` with one pytest, verify `from oohscout.track_a_spatial import load_or_build_study_area` works.
2. **`feature/f2-ih35-centerline`** — same 5-file convention in a new chapter folder, applied to IH-35 highway centerline for McLennan. Production module: `backend/src/oohscout/track_a_spatial/corridor.py`. Because F1a will be done, this module will be importable from day one.

---
