# OOHScout AI — Master Feature List (Chapter-Mapped)

**Last updated:** 2026-08-29
**Purpose:** Single source of truth for every feature in the OOHScout AI product, mapped to the specific course chapter that teaches the technique, plus honest flags for what neither course covers.

**Course sources:**
- **UA Advanced** — Urban Analytics with Python: Advanced Methods (Milan Janosov) — `C:\Users\nguye\Downloads\files (1)\files\`
- **GeoAI Essentials** — GeoAI Essentials (Milan Janosov) — `C:\Users\nguye\Documents\billboardAI\GeoAI_Essentials_Chapters\code\`
- **UA Intro** — Urban Analytics Intro (Milan Janosov) — not yet purchased; Milan's explicit recommendation
- **Sat DS** — Satellite Data Science in Python (Milan Janosov) — optional, for visibility/obstruction depth
- **External** — not covered by any Milan course; you build from first principles or other sources

**Legend:**
- ✅ = feature technique already learned
- ⏳ = feature technique is in the next planned chapter
- ⚠️ = feature requires work outside both courses
- 🔒 = feature belongs to Track B (Regulatory RAG) — locked in its own box per Milan's advice

---

## LAYER 1 — Foundation & Data (Track A)

| # | Feature | Primary Chapter | Status | Notes |
|---|---|---|---|---|
| 1 | Retargetable study area with one `PLACE` + `CRS_METRIC` block | UA Advanced Ch 1 | ✅ | Shipped 2026-08-29 on `feature/f1-retargetable-study-area`. Area 2,747.3 km² (0.05% off Census reference); boundary visually verified on Esri; cached to `backend/data/processed/mclennan_county_study_area.gpkg`. Production module `backend/src/oohscout/track_a_spatial/study_area.py` importable via F1a. |
| 1a | Make `backend/src/oohscout/` an installable package + smoke test | Project infra (external) | ✅ | Shipped 2026-08-29 on `feature/f1a-installable-package`. Hatchling build backend added; `uv sync` installs `oohscout-ai==0.0.1` in editable mode; `from oohscout.track_a_spatial import load_or_build_study_area` works; 5 pytests in `backend/tests/track_a/test_study_area.py` pass. Notebook and module now produce identical area (2,747.33 km²). |
| 2 | Base geometry = IH-35 highway centerline with unique key | UA Advanced Ch 1 | ✅ | Shipped 2026-08-29 on `feature/f2-ih35-centerline`. 245 LineString segments, ~131 km (both directions of the motorway mainlanes; no frontage roads), `osmid` unique after OSMnx-duplicate dedupe. Cache: `backend/data/processed/mclennan_ih35_centerline.gpkg`. Production module: `backend/src/oohscout/track_a_spatial/corridor.py`. 7 pytests pass. |
| 3 | Multi-source ingestion + cache pattern | UA Adv Ch 1 + your existing notebook | ✅ | TxDOT REST, OSM, later MCAD |
| 4 | Data provenance metadata (license, source, freshness) | `CLAUDE.md` rule + UA Ch 4 discipline | ✅ | Shipped 2026-08-30 on `feature/f4-provenance-metadata`. `SourceRecord` dataclass + `write_source_yaml()` / `audit_provenance()` in `backend/src/oohscout/data/provenance.py`. McLennan boundary + IH-35 centerline have sidecars. 7 pytests pass (roundtrip + audit + real-folder integrity gate). |
| 5 | Test-bbox subset for fast iteration (DEV_MODE) | UA Adv Ch 1, UA Adv Ch 3 | ✅ | Waco urban bbox subset of McLennan |

## LAYER 2 — Corridor Engine (Track A)

| # | Feature | Primary Chapter | Status | Notes |
|---|---|---|---|---|
| 6 | Corridor buffer (500m search zone around IH-35) | How to Think Spatially Ch 3 ("near is a choice") + GeoAI Ch 14 Step 98 (metric buffer) | ✅ | Shipped 2026-09-11 on `feature/f6-corridor-buffer`. `build_corridor_buffer()` (pure: union → buffer → clip; refuses degrees, feet, mismatched CRS, bad distance, empty zone) + `load_or_build_corridor_buffer()` (cache name includes the distance) in `backend/src/oohscout/track_a_spatial/corridor.py`. McLennan IH-35 at 500 m = 65.37 km², one polygon. 15 pytests in `backend/tests/track_a/test_corridor_buffer.py`. |
| 7a | Reference line per direction of travel + milepost scale | Shapely `line_merge(directed=True)` / `project` / `interpolate` (external) | ✅ | Built 2026-09-12 on `feature/mvp-screening`. `build_reference_lines()` (245 segments → 2 lines of ~65.5 km, refuses gaps, stray branches, one-direction data), `locate_on_reference()` (side, chainage, offset), `build_milepost_scale()` (TxDOT reference markers → roadside mileposts, e.g. MP 331.42) in `backend/src/oohscout/track_a_spatial/reference.py`. |
| 7b | Existing signs on the highway (TxDOT permits + certified-city permits) | External | ✅ | Built 2026-09-12. `select_highway_signs()` (regex over messy highway names) + `prepare_existing_signs()` (side + chainage, strays dropped, back-to-back permits merged) in `existing_signs.py`. Loads signs past the county line (2 km margin) so spacing has no edge effect. McLennan IH-35: 128 structures (113 TxDOT + 15 Waco city permits). |
| 7 | ~~Candidate sampling every 1 km~~ → replaced by the F8 sieve | — | ✅ | A dot every 1 km is not a candidate: availability depends on existing signs, the law and the land. Candidates now come out of F8. |
| 8 | Preliminary screening sieve along each side (FAIL / REVIEW, never PASS or "LEGAL") | External | ✅ | Built 2026-09-12. `probe_points()` (10 m steps) → `screen_probes()` (spacing §21.180 same side along the road; ramps §21.179 outside cities; ±15 m REVIEW band; certified city → city rules; possible ETJ) → `merge_stretches()` → `place_candidates()` (≥ 1,500 ft from signs and from each other; IDs like `IH35-E-MP318.46`) in `screening.py`. McLennan IH-35: ~21 km open, 59 candidates (all REVIEW). Runner: `backend/scripts/run_ih35_screening.py`. |
| 9 | 43 TAC Chapter 21 rule table (tiered, side-of-road, size-based) | External research (Track B input) | ⚠️ | Partly built 2026-09-12: rules as data with citations in `backend/src/oohscout/rules/texas.py` (spacing, highway facilities, commercial area, public spaces, certified city, Waco cap-and-replace, ETJ). `full_text_verified=False` on every rule until a person checks the full text — so screening can never say PASS. Commercial-area and public-space checks not automated yet. |

## LAYER 3 — Demand & Accessibility (Track A)

| # | Feature | Primary Chapter | Status | Notes |
|---|---|---|---|---|
| 10 | Advertiser POI taxonomy (fuel/QSR/hotel/bank/auto/car_wash) | UA Advanced Ch 2 | ⏳ | Persona-driven category collapse |
| 11 | DBSCAN commercial agglomerations along corridor | UA Advanced Ch 2 | ⏳ | Named clusters (Waco South, Bellmead, Elm Mott) |
| 12 | KMeans functional typology per candidate cell | UA Advanced Ch 2 | ⏳ | Types: `fuel_hub`, `mixed_commercial`, `residential_edge` |
| 13 | Grid sized from mean cluster span (not arbitrary) | UA Advanced Ch 2 | ⏳ | Data-driven cell size |
| 14 | Cell features: density + Shannon entropy diversity + NN isolation | UA Advanced Ch 2 | ⏳ | Every cell has demand fingerprint |
| 15 | Three-screen candidate funnel (type + extent + character/lift) | UA Advanced Ch 2 | ⏳ | Milan's matcha-shop pattern |
| 16 | 5-min drive-time isochrones around IH-35 exits | UA Advanced Ch 3 | ⏳ | Pandana network → isochrone polygons |
| 17 | Per-candidate walking/driving minutes to advertiser POIs | UA Advanced Ch 3 | ⏳ | `min_fuel`, `min_qsr`, `min_hotel` per candidate |
| 18 | AADT snap-to-nearest candidate | UA Advanced Ch 3 (`sjoin_nearest`) | ⏳ | Real TxDOT AADT per candidate |

## LAYER 4 — Site Quality, Zoning, Valuation (Track A)

| # | Feature | Primary Chapter | Status | Notes |
|---|---|---|---|---|
| 19 | Land-use / zoning ingestion from official source | UA Advanced Ch 4 (NYC Parks pattern) | ⏳ | City of Waco zoning replaces NYC Parks |
| 20 | Distance-to-residential (setback proxy) | UA Advanced Ch 4 (`sjoin_nearest` + distance_col) | ⏳ | Sanity check: inside-residential must equal ~0m |
| 21 | NDVI vegetation buffer per candidate | UA Advanced Ch 4 | ⏳ | Sentinel-2 STAC → buffer-mean NDVI 10/50/100m |
| 22 | Sanity-check pattern (inside-park → 0m) | UA Advanced Ch 4 | ⏳ | Critical discipline for any nearest-neighbor join |
| 23 | LiDAR-based visibility/obstruction score | GeoAI Ch 4 ✅ + GeoAI Ch 5 ✅ | ✅ | McLennan LiDAR + U-Net; proof-of-concept scale |
| 24 | Combined greenery/visibility index (min-max blend) | UA Advanced Ch 4 | ⏳ | Rank-transform + min-max + equal-weight mean |
| 25 | Persona-weighted opportunity score | UA Advanced Ch 5 | ⏳ | "Billboard operator" persona; weights sum to 1.0 |
| 26 | Two-unit analysis (candidate stretches vs points) | UA Advanced Ch 5 | ⏳ | MAUP discipline |
| 27 | Equal-count binning for candidate ranking (`pd.qcut`) | UA Advanced Ch 5 | ⏳ | Top 10% / next 10% / etc. |
| 28 | Land lease price surface (Spatial Lag regression) | UA Advanced Ch 6 | ⏳ | `ML_Lag` from spreg, KNN weights |
| 29 | Per-candidate density feature (KDTree radius count) | UA Advanced Ch 6 | ⏳ | `bld_density_500m` around each candidate |
| 30 | OLS baseline + Spatial Lag comparison + AIC | UA Advanced Ch 6 | ⏳ | Honest "does spatial lag earn its term?" test |

## LAYER 5 — Regulatory RAG (Track B) — 🔒 NOT in either Milan course

| # | Feature | Source | Notes |
|---|---|---|---|
| 31 | Regulatory corpus (43 TAC Ch 21, 23 CFR 750, Waco sign ordinance, McLennan ord.) | External | Assemble PDFs/HTML with provenance |
| 32 | Semantic chunking with section-metadata preservation | External | Not naive 512-token; keep subsection headers |
| 33 | Embedding + pgvector storage | External | Anthropic/pgvector knowledge |
| 34 | Citation-required retrieval chain | External | Reject any answer that can't cite subsection |
| 35 | Structured rule extraction to `verified_rules` JSON | External + LLM | Schema per `project_oohscout_data.md` |
| 36 | Human-review workflow (draft → verified) | External | The moat sits here, not in the LLM |

## LAYER 6 — Agent Capstone (Track C) — GeoAI Ch 14

**Early learning checkpoint:** after F7, build a Track-A-only Scout shell for Chapter 14 practice. It is not a numbered feature, cannot make site recommendations, and does not count as F37/F39 completion. Track A and Track B remain decoupled until Phase 4.

| # | Feature | Primary Chapter | Status | Notes |
|---|---|---|---|---|
| 37 | ReAct loop with tool-calling LLM (Llama or Claude) | GeoAI Ch 14 | ⏳ | Study Milan's example verbatim first |
| 38 | STRtree spatial indexing for fast candidate retrieval | GeoAI Ch 14 | ⏳ | Not needed until dataset grows |
| 39 | Track A functions wrapped as tools with Pydantic schemas | External — Ch 14 shows pattern | ⏳ | `tool_get_corridor()`, `tool_score_candidate()` |
| 40 | Track B RAG wrapped as `tool_query_regulation()` | External — Ch 14 pattern | ⏳ | Returns `{answer, citation, confidence}` |
| 41 | Golden-case evaluation harness | External | ⏳ | 15 test queries, expected tool sequences |

## LAYER 7 — Deliverables & Optional Extensions

| # | Feature | Chapter | Status | Notes |
|---|---|---|---|---|
| 42 | Folium interactive map with layer toggles | UA Advanced Ch 2, 3, 5 | ✅ | You already know this |
| 43 | CSV / GeoPackage per-candidate exports | UA Advanced Ch 1 (GeoPackage discipline) | ⏳ | `.gpkg` for projected coords, not GeoJSON |
| 44 | Landowner PDF deck | External (WeasyPrint/Puppeteer) | ⚠️ | Phase 5+, after operator validation |
| 45 | Web dashboard (React + MapLibre) | External | ⚠️ | Only if Phase 6 reached |
| 46 | Unpermitted billboard detection from aerial | GeoAI Ch 7 (Object Detection) | ⚠️ | Optional exhibit — TxDOT already gives real permits |
| 47 | Alternative clustering methods | GeoAI Ch 11 | ⚠️ | Optional cross-check on UA Ch 2 DBSCAN |
| 48 | New commercial construction radar | GeoAI Ch 9 (Change Detection) | ⚠️ | High-value lead generation — Phase 6+ exhibit |
| 49 | Aerial patch classification (commercial/residential/rural) | GeoAI Ch 6 (Patch Classification) | ⚠️ | Zoning proxy where municipal zoning missing |
| 50 | Traffic trend forecasting per corridor | GeoAI Ch 10 (Spatio-temporal) | ⚠️ | Long-term extension |
| 51 | Demand surface interpolation between candidates | GeoAI Ch 12 (Spatial Interpolation) | ⚠️ | Smooth demand between sample points |
| 52 | Zero-shot land-use tagging via SAM/CLIP | GeoAI Ch 13 (Foundation Models) | ⚠️ | Reduces manual labeling when zoning data missing |

---

## Ownership summary

| Chapter | Features it primarily unlocks | Sessions | Status |
|---|---|---|---|
| UA Advanced Ch 1 | 1, 2, 3, 5, 43 | 1 | ⏳ next |
| UA Advanced Ch 2 | 10, 11, 12, 13, 14, 15, 42 | 2 | ⏳ |
| UA Advanced Ch 3 | 16, 17, 18, 42 | 2 | ⏳ |
| UA Advanced Ch 4 | 19, 20, 21, 22, 24 | 2 | ⏳ |
| UA Advanced Ch 5 | 25, 26, 27, 42 | 1 | ⏳ |
| UA Advanced Ch 6 | 28, 29, 30 | 2 | ⏳ |
| UA Intro (recommended purchase) | 6, 7, plus GeoPandas/OSMnx fluency | 3-4 | ⏳ before Advanced |
| GeoAI Ch 4 | Foundation (already integrated) | 0 | ✅ |
| GeoAI Ch 5 | 23 (LiDAR obstruction) | 1 | 1 more session to apply to Waco |
| GeoAI Ch 6 | 49 (optional) | 2 | ⚠️ Phase 6+ |
| GeoAI Ch 7 | 46 (optional) | 3 | ⚠️ Phase 6+ |
| GeoAI Ch 9 | 48 (optional) | 2 | ⚠️ Phase 6+ |
| GeoAI Ch 10 | 50 (optional) | 2 | ⚠️ Phase 6+ |
| GeoAI Ch 11 | 47 (redundant with UA Ch 2) | 0 | Skip |
| GeoAI Ch 12 | 51 (optional) | 1 | ⚠️ Phase 6+ |
| GeoAI Ch 13 | 52 (optional) | 2 | ⚠️ Phase 6+ |
| GeoAI Ch 14 | 37, 38 | 1 preview after F7; 2 study + 4 build | ⏳ Full adaptation Phase 4 |
| External Track A | 6, 7, 8, 9 | 2-3 | ⚠️ |
| External Track B | 31-36 | 3-5 | 🔒 Phase 3 |
| External Track C | 39, 40, 41 | 2 | ⏳ Phase 4 |
| External Delivery | 44, 45 | Phase 5+ | ⚠️ |

**Total features:** 52
**Directly covered without substantial external adaptation:** ~21 (~40%)
**External or substantial adaptation work:** ~31 (~60%)
