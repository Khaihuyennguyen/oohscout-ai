# OOHScout AI — Session Updates

Chronological log of what actually shipped, per session. Append newest at the top. Every entry links to concrete files so a future collaborator can reconstruct the state.

---

## 2026-09-12 — MVP preliminary screening built (F7a, F7b, F8, F9 partial)

**Branch:** `feature/mvp-screening` — merged to `main` as `a740e2e` and pushed on 2026-09-12

### Why the plan changed

The first F7 design put a candidate every 1 km. Reading the rules and the data showed that a dot on the road means nothing by itself: 43 TAC Ch. 21 requires 1,500 ft same-side spacing (§21.180), keeps signs 1,000 ft from ramps outside cities (§21.179), requires a commercial/industrial area (§21.162-163), and inside a **certified city** (Waco) the city decides — Waco runs a **cap-and-replace** system (Waco Code §28-1078). Waco's own permits were also missing from the TxDOT permit layer. Candidates are therefore produced by a **sieve**: start with every metre of each side of the road and remove what the rules forbid.

### What was built

- `track_a_spatial/reference.py` — F7a reference lines (one per direction, directed merge), `locate_on_reference` (side, chainage, offset), `build_milepost_scale` (TxDOT reference markers → roadside mileposts).
- `track_a_spatial/existing_signs.py` — F7b existing signs on the highway (regex over messy highway names, strays dropped, back-to-back permits merged).
- `track_a_spatial/screening.py` — F8 sieve: probes every 10 m → blocked (FAIL) / near_limit / city_rules / possible_etj / open (all REVIEW) → stretches → candidates ≥ 1,500 ft from signs and from each other.
- `rules/texas.py` — F9 rule table as data with citations; `full_text_verified=False` everywhere, so nothing is ever PASS.
- `data/arcgis.py` — TxDOT open-data fetcher (URL guard, 50 MB cap, paging, cache + provenance sidecar).
- `backend/scripts/run_ih35_screening.py` — the McLennan / IH-35 run: GeoPackage + CSV + interactive map.

### Evidence

- 120 tests pass (64 before + 56 new). 18 planted bugs, each caught by the tests.
- Real run: 128 existing sign structures (113 TxDOT + 15 Waco). Per side, ~41-43 km blocked (58.7 km by spacing, 25.6 km by ramps, both sides), 10.7 km Waco city rules, ~10-11 km open. **59 candidates** (32 E, 27 W), all REVIEW.
- Independent check of every candidate against the raw data: nearest same-side sign ≥ 1,551 ft (rule 1,500), nearest ramp for rural candidates ≥ 1,054 ft (rule 1,000), none inside Waco or outside the county. This check found a boundary bug (spots placed on the exact edge of a stretch) that was fixed and covered by a new test.

### Known limits (all flagged REVIEW, never hidden)

- Rule text not yet verified word-for-word; commercial-area (§21.162-163) and public-space (§21.178) checks not automated; parcels/landowners not joined.
- Ramp distance is straight-line to OSM `motorway_link` geometry — an approximation of §21.179. Ramps are fetched only inside the county-clipped 500 m zone, so a ramp just across the county line is not seen; no McLennan candidate is affected (the 6 rural candidates are ≥ 18,000 ft from the county line), but a retargeted corridor should fetch ramps with a margin like the signs.
- Waco ETJ boundary unknown (flagged as "possible ETJ" within 5 miles); Waco size-based spacing and zoning not modelled.

---

## 2026-09-11 — F6 Corridor Buffer SHIPPED

**Branch:** `feature/f6-corridor-buffer`
**Feature shipped:** F6 (the search zone every later feature works inside)

### What was built

- **Production code** in [backend/src/oohscout/track_a_spatial/corridor.py](../backend/src/oohscout/track_a_spatial/corridor.py):
  - `build_corridor_buffer(lines_metric, study_area_metric, distance_m)` — pure function: union the highway lines → buffer by `distance_m` → clip to the study area. Raises `ValueError` for a non-finite or non-positive distance, a missing CRS, degrees, non-metre units (e.g. Texas State Plane EPSG:2277 is in US survey feet), mismatched CRSs, or an empty zone.
  - `load_or_build_corridor_buffer(..., cache_dir, *, cache_slug, distance_m=500)` — cache-first wrapper; the file name includes the distance (`<cache_slug>_500m.gpkg`) so a different width never returns a stale zone. `cache_slug` has no default: callers name the corridor.
  - `CorridorBuffer` frozen dataclass (`distance_m`, `buffer_gdf_metric`, `area_km2`, `cache_path`), exported from `oohscout.track_a_spatial`.
- **Tests** [backend/tests/track_a/test_corridor_buffer.py](../backend/tests/track_a/test_corridor_buffer.py) — 15 pytests: 499 m inside / 501 m outside, overlapping segments become one polygon, clipping, every rejected input, cache naming + cache hits, and the real McLennan IH-35 zone. Real-data test caches into `tmp_path` so the F4 provenance audit never sees an unsidecarred file.
- **Real output (local, git-ignored):** `backend/data/processed/mclennan_ih35_buffer_500m.gpkg` + `.source.yaml` (derived from two ODbL datasets → ODbL).

### Evidence

| Gate item | Result |
|---|---|
| McLennan IH-35 zone at 500 m | ✅ 65.37 km², one Polygon, no holes, inside the county |
| Sanity check (≈ 65 km road × 2 × 0.5 km) | ✅ ~65 km² |
| Buffering segments separately instead (the bug F6 avoids) | 323.2 km² — 5× too large |
| Tests catch planted bugs (unit check removed, distance dropped from cache name) | ✅ both caught |
| Pytest total | ✅ **64 passed** (49 before + 15 F6) |

### Next branch

`feature/f7-candidate-sampling` — candidate spots along the corridor, one reference line per direction of travel (F7a).

---

## 2026-08-30 — F4 Data Provenance Sidecars SHIPPED

**Branch:** `feature/f4-provenance-metadata`
**Feature shipped:** F4 (`.source.yaml` sidecar per cached dataset)

### What was built

- **Production module** [backend/src/oohscout/data/provenance.py](../backend/src/oohscout/data/provenance.py) — `SourceRecord` dataclass + `write_source_yaml()` + `read_source_yaml()` + `audit_provenance()`. 8-field schema (source_name, source_url, retrieval_date, retrieval_method, record_count, license, commercial_use_allowed, redistribution_allowed) + optional `authority` and `notes`.
- **Tests** [backend/tests/data/test_provenance.py](../backend/tests/data/test_provenance.py) — 7 pytests: extension swap, write/read roundtrip, missing-sidecar raises, audit finds missing, audit passes when covered, audit ignores sidecar files themselves, real-folder integrity gate (`test_project_processed_dir_is_fully_covered`).
- **Chapter folder** [docs/learning/chapters/f4_provenance_metadata/](learning/chapters/f4_provenance_metadata/) — full 5-file convention: 01/02 short pointers (F4 not a Milan chapter), runnable 03 adaptation, deep 04 explanation, 05 code-along.
- **Real sidecars** — `mclennan_county_study_area.source.yaml` and `mclennan_ih35_centerline.source.yaml` written next to F1 + F2 outputs.
- **New dependency** — `pyyaml>=6.0.3` added to `pyproject.toml`.

### Evidence

| Gate item | Result |
|---|---|
| Every dataset in `backend/data/processed/` has a sidecar | ✅ 2/2 sidecars exist |
| Sidecars are valid YAML with required fields | ✅ Roundtrip test passes |
| Real-folder audit test | ✅ `test_project_processed_dir_is_fully_covered` passes |
| Pytest total | ✅ **19 passed** (5 F1 + 7 F2 + 7 F4) |

### Fixing a scaffolding mistake

Initial F4 scaffold shipped with only README + a prompts-only notebook. User pushed back — the "scaffold" rule meant the FULL 5-file convention (like F1 and F2 shipped). Memory `feedback_feature_pause_point.md` now has an explicit "common mistake to avoid" note pointing at this F4 slip.

### Next branch

`feature/f5-test-bbox` — DEV_MODE bbox subset for fast iteration inside Waco urban area. Depends on F1 + F2.

---

## 2026-08-29 — F2 IH-35 Centerline SHIPPED

**Branch:** `feature/f2-ih35-centerline`
**Feature shipped:** F2 (IH-35 highway centerline for McLennan County)
**PRD reference:** [docs/PRD.md § 6 F2](PRD.md)

### What was built

- **Production module** [backend/src/oohscout/track_a_spatial/corridor.py](../backend/src/oohscout/track_a_spatial/corridor.py) — `Corridor` dataclass + `load_or_build_highway_centerline(admin_poly, cache_dir)`. Filters OSM motorways by `ref` prefix, dedupes exact-duplicate ways OSMnx occasionally returns, projects to metric CRS, caches as `.gpkg`.
- **Chapter folder** [docs/learning/chapters/ua_advanced_ch01_ih35/](learning/chapters/ua_advanced_ch01_ih35/) — 5-file convention. The 01/02 files are short pointers back to F1 because the underlying Milan chapter is the same. The 03 notebook imports directly from the production module (F1a made this possible from day one).
- **Tests** [backend/tests/track_a/test_corridor.py](../backend/tests/track_a/test_corridor.py) — 7 pytests covering segment count, geometry types, unique osmid, metric CRS, plausible length range, cache existence, and wrong-reference-length negative test.

### Evidence of shipping

| Gate item | Result |
|---|---|
| Overpass returned segments | ✅ 245 LineString ways |
| Geometry filter kept only lines | ✅ `LineString` only |
| `osmid.is_unique` after dedupe | ✅ (4 exact-dupe rows collapsed) |
| Total length plausible for IH-35 through McLennan | ✅ 131.06 km (both directions + frontage) |
| Metric CRS matches EPSG:32614 | ✅ |
| `.gpkg` cache written | ✅ `mclennan_ih35_centerline.gpkg` |
| Pytest suite | ✅ **7 passed** (12 total across F1 + F2) |

### One thing I learned mid-build

OSMnx 2.x's `features_from_polygon` occasionally returns the same OSM way twice with byte-identical geometry — I hit this on the first live fetch and had to add `drop_duplicates(subset=['osmid'])` before the unique-key assertion. Verified safe: `.geometry.equals()` returned `True` for all duplicate pairs. Documented in [04_adaptation_explanation.md](learning/chapters/ua_advanced_ch01_ih35/04_adaptation_explanation.md).

### Why the length is 131 km, not the ~55 km Google Maps shows

OSM stores IH-35 as **separate ways per direction**. Northbound + southbound each contribute ~55 km. Frontage roads and access segments that carry the `I 35` ref add another ~20 km. For OOHScout the both-direction total is what we want — billboard sites exist on both sides of the highway.

### What this unlocks

- **F6 (corridor buffer)** — `unary_union(corridor_gdf_metric.geometry).buffer(500)` gives the 500m search zone as one polygon.
- **F7 (candidate sampling)** — `line.interpolate(distance_along)` every 1 km along the merged centerline produces WA-000...WA-039 candidate points.
- **F8 (spacing engine)** — projects existing TxDOT permit points onto the centerline for 1D distance math.

### Next branch

F6 or F7 (both depend on F2, both fit in the same UA Ch 1 → UA Intro Shapely-basics territory).

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

`feature/f2-ih35-centerline` — same 5-file convention in `docs/learning/chapters/ua_advanced_ch01_ih35/`, applied to IH-35 highway centerline for McLennan. Production module: `backend/src/oohscout/track_a_spatial/corridor.py` with `load_or_build_highway_centerline(admin_poly, cache_dir)`. Because F1a is done, this module will be importable + testable from day one.

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
