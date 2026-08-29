# OOHScout AI — Product Requirements Document

**Version:** 0.1
**Last updated:** 2026-08-29
**Status:** Draft — pre-development
**Owner:** Nguyen Khai Huyen

---

## 1. Product Overview

### 1.1 One-line thesis
OOHScout AI is an AI-assisted OOH (out-of-home advertising) development desk that turns fragmented regulations, geospatial data, traffic, parcels, and market signals into a ranked billboard-acquisition pipeline for one highway corridor at a time.

### 1.2 What it is NOT
- Not a map of existing billboards
- Not a generic GIS dashboard
- Not a chatbot guessing legality
- Not a nationwide SaaS at MVP
- Not a legal advisor — always "passed preliminary screening"

### 1.3 MVP scope
**One corridor** (IH-35 through McLennan County, TX), **5-20 ranked candidate sites** an experienced billboard operator agrees are worth investigating.

### 1.4 First commercial milestone
An operator pays for a second corridor analysis.

---

## 2. Goals & Non-Goals

### 2.1 Goals
- **G1** — Ship a ranked candidate list for IH-35 McLennan that a Waco operator agrees is worth their time
- **G2** — Build the regulatory RAG moat (structured verified_rules per jurisdiction)
- **G3** — Demonstrate a working ReAct agent that orchestrates spatial tools with citations
- **G4** — Portfolio-quality GitHub artifact demonstrating GeoAI + RAG + agents
- **G5** — Convert one Waco operator to a paying customer for corridor #2

### 2.2 Non-Goals (v0.1)
- Nationwide SaaS
- Real-time ad-serving integration
- Landowner outreach automation
- Programmatic DOOH connections
- Mobile app
- Second state (Texas only)
- Second county in Texas before Waco is validated

---

## 3. Users & Personas

### 3.1 Primary — "Marcus, Regional Billboard Developer"
- Works for a mid-size Texas OOH operator (~30 boards in Central Texas)
- Age 42, 15 years in OOH, comfortable with maps but not GIS software
- KPI: add 3-5 profitable new sites per year
- Pain today: 2 weeks per site in windshield surveys + county records + phone calls
- Budget: $5-15K per corridor analysis
- Primary success measure: "I'd investigate WA-015 in the field"

### 3.2 Secondary — "Priya, Regulatory Compliance Officer"
- Reviews proposed sites for permit-eligibility risk
- Needs citations to state administrative code (43 TAC Ch 21)
- Success measure: RAG citation matches actual code section

### 3.3 Secondary — "Chen, Portfolio Analyst / Investor"
- Evaluating a competitor's portfolio for acquisition due diligence
- Needs quantitative site quality scoring at scale
- Success measure: score correlates with actual billboard revenue (Phase 6+)

### 3.4 Tertiary — "Sarah, Landowner"
- Receives a lease offer; needs comparison to market
- Success measure: lease offer contextualized with local comparables

---

## 4. Success Metrics

### 4.1 MVP metrics (Track A complete)
| Metric | Target | Measurement |
|---|---|---|
| Ranked candidates on IH-35 McLennan | 5-20 | Count in `candidate_sites` output |
| Real TxDOT permit spacing accuracy | 100% | Verified against live API |
| AADT per candidate | Non-null for ≥90% | TxDOT AADT snap |
| Operator agreement on top 10 | ≥1 candidate flagged "worth investigating" | Interview validation |

### 4.2 Track B metrics (RAG complete)
| Metric | Target |
|---|---|
| Golden queries answered with correct citation | ≥90% of 10 test queries |
| Retrieval precision @ 5 | ≥80% |
| Structured verified_rules extracted | ≥50 rules across corpus |

### 4.3 Track C metrics (Agent complete)
| Metric | Target |
|---|---|
| Golden test case pass rate | ≥12/15 |
| Median tool calls per query | ≤6 |
| Agent hallucination rate on spatial claims | 0 (spatial claims must trace to Track A) |

### 4.4 Commercial metrics
| Metric | Target |
|---|---|
| First paid corridor report | 1 by end of Phase 4 |
| Portfolio: GitHub stars | ≥50 after portfolio launch |
| Portfolio: technical blog post views | ≥1000 |

---

## 5. Users Stories (Acceptance Criteria)

Reference: `docs/MASTER_PLAN.md` Section 2 for the full 11-story list.
Key story summaries:

| # | Story | Acceptance |
|---|---|---|
| US-1 | Corridor scoping | User inputs highway + county → system loads geometry + jurisdiction |
| US-2 | Candidate discovery | 20-40 candidates auto-generated with unique IDs |
| US-3 | Preliminary spacing screening | Each candidate flagged PASS/FAIL/REVIEW with rule citation. Word "LEGAL" never appears |
| US-4 | Advertiser demand signal | Each candidate scored on nearby QSRs, fuel, hotels via drive-time isochrones |
| US-5 | Real traffic verification | Each candidate shows TxDOT AADT + link to source |
| US-6 | Regulatory Q&A | Plain English question → answer + 43 TAC subsection citation |
| US-7 | Landowner identification | Parcel owner name + address + tax value from MCAD |
| US-8 | Lease estimate | Monthly range with uncertainty band + model shown |
| US-9 | Ranked shortlist | Top 10 sortable table with per-factor breakdown |
| US-10 | Site packet export | Per-candidate PDF |
| US-11 | Natural language agent | Type free-text query, get ranked answer with reasoning trace |

---

## 6. Feature Specifications

Each feature carries: **ID · Name · Chapter · Priority · Input · Output · Dependencies · Acceptance**.

Priority scale:
- **P0** = MVP critical path
- **P1** = MVP nice-to-have
- **P2** = Post-MVP portfolio exhibit

### LAYER 1 — Foundation & Data

---

**F1. Retargetable Study Area**
- **Chapter:** UA Advanced Ch 1
- **Priority:** P0
- **Status:** IN PROGRESS on `feature/f1-retargetable-study-area`
- **Input:** `PLACE = "McLennan County, Texas"`, `CRS_METRIC = 32614`, `CRS_GEOGRAPHIC = 4326`
- **Output:** `admin_gdf` (GeoDataFrame with 1 polygon), `study_area` polygon in metric CRS
- **Dependencies:** None (foundational)
- **Acceptance:** Editing the study-area configuration block (`PLACE`, matching `CRS_METRIC`, and the county's published reference area) retargets the study area to another county. Boundary plots on Esri satellite basemap. Reported total administrative area (in km²) matches a published Census/Wikipedia reference within 5%.

---

**F2. Base Geometry — IH-35 Highway Centerline**
- **Chapter:** UA Advanced Ch 1 (adapted from buildings to highway)
- **Priority:** P0
- **Input:** `admin_poly` from F1, `tags={"highway": ["motorway"]}`
- **Output:** `mclennan_ih35_centerline.gpkg` — LineString geometries + `osmid` unique key + `length_m`
- **Dependencies:** F1
- **Acceptance:** `assert osmid.is_unique` passes. Total IH-35 length in km matches Google Maps within 10%. LineString-only (no accidental polygons).

---

**F3. Multi-Source Ingestion + Cache Pattern**
- **Chapter:** UA Advanced Ch 1 + existing prototype
- **Priority:** P0
- **Input:** Data source URLs (TxDOT ArcGIS endpoints, OSM Overpass, Sentinel-2 STAC)
- **Output:** Cached local files with `if path.exists(): load; else: download+save` pattern
- **Dependencies:** F1
- **Acceptance:** Re-running any notebook second time completes in <10 seconds (no network calls).

---

**F4. Data Provenance Metadata**
- **Chapter:** `CLAUDE.md` rule + UA Ch 4 discipline
- **Priority:** P0
- **Input:** Every dataset ingested
- **Output:** `source.yaml` sidecar per dataset with `source_url, license_type, commercial_use_allowed, redistribution_allowed, freshness, verified_by`
- **Dependencies:** F3
- **Acceptance:** Every file in `data/processed/` has a `.source.yaml` sibling. Missing metadata = build failure.

---

**F5. Test-BBox Subset for Fast Iteration**
- **Chapter:** UA Advanced Ch 1 + Ch 3 (DEV_MODE)
- **Priority:** P0
- **Input:** `DEV_MODE=True` + `TEST_BBOX = (-97.20, 31.48, -97.05, 31.62)` (Waco urban)
- **Output:** All downstream layers scoped to this bbox when flag is on
- **Dependencies:** F1, F2
- **Acceptance:** With `DEV_MODE=True`, full pipeline runs in <30 seconds.

---

### LAYER 2 — Corridor Engine

---

**F6. Corridor Buffer (Search Zone)**
- **Chapter:** UA Intro fundamentals (Shapely `.buffer()`)
- **Priority:** P0
- **Input:** F2 output + `CORRIDOR_BUFFER_M = 500`
- **Output:** `mclennan_ih35_buffer.gpkg` — single polygon (unary_union + buffer)
- **Dependencies:** F2
- **Acceptance:** Buffer polygon area ≈ 500m × 2 × length_km (within 10%). Renders as a ribbon on Folium map.

---

**F7. Candidate Site Sampling**
- **Chapter:** UA Intro fundamentals (Shapely `.interpolate()`)
- **Priority:** P0
- **Input:** F2 line + `CANDIDATE_INTERVAL_M = 1000`
- **Output:** `mclennan_candidates.gpkg` — Point geometries + `candidate_id` (WA-000 through WA-039)
- **Dependencies:** F2
- **Acceptance:** 20-40 candidates produced for IH-35 through McLennan. Each has unique `candidate_id` and `dist_along_km`.

---

**F8. LRS Spacing Engine**
- **Chapter:** External (Milan omits line ops from course)
- **Priority:** P0
- **Input:** F2 line, F7 candidates, F9 rule table, real TxDOT permits (from F3)
- **Output:** Each candidate gets `spacing_status: PASS | FAIL | REVIEW` + `spacing_rule_cited` + `spacing_evidence`
- **Dependencies:** F2, F7, F9
- **Acceptance:** Projected 1D distances match Shapely `line.project()`. Side-of-road logic correctly excludes opposite-direction signs. Rule tier selected matches sign size input.

---

**F9. 43 TAC Chapter 21 Rule Table**
- **Chapter:** External research
- **Priority:** P0
- **Input:** Legal source documents (43 TAC Ch 21 Subch I + 23 CFR 750 + Waco sign ordinance + McLennan county ord.)
- **Output:** `phase1_spacing_rules.json` — structured rules with `{tier_id, sign_size_sqft_min, sign_size_sqft_max, road_class, min_spacing_ft, side_of_road, jurisdiction, source_section, effective_date}`
- **Dependencies:** None (research task)
- **Acceptance:** All rules cite specific 43 TAC subsections (not §391.031). Reviewed by a Waco attorney (Phase 3+).

---

### LAYER 3 — Demand & Accessibility

---

**F10. Advertiser POI Taxonomy**
- **Chapter:** UA Advanced Ch 2 (persona-driven category collapse)
- **Priority:** P0
- **Input:** OSM tag dict `ADVERTISER_TAGS` (amenity + shop + tourism)
- **Output:** `waco_advertiser_pois.gpkg` with `category` column (fuel_hub / qsr / hotel / auto / bank)
- **Dependencies:** F1
- **Acceptance:** Categories cover the top 6 billboard-advertising verticals. Each POI has exactly one category.

---

**F11. DBSCAN Commercial Agglomerations**
- **Chapter:** UA Advanced Ch 2
- **Priority:** P0
- **Input:** F10 POI points in metric CRS + `EPS_M` (chosen by eye from 4-value panel) + `MIN_CLUSTER_SIZE = 10`
- **Output:** Named clusters (Waco South, Bellmead, Elm Mott, West Waco) with cluster ID + POI count + top-3 categories by lift
- **Dependencies:** F10
- **Acceptance:** Cluster count sensible for corridor (5-15 clusters). Each named cluster corresponds to a real Waco commercial area visible on satellite basemap.

---

**F12. KMeans Functional Typology (Per Cell)**
- **Chapter:** UA Advanced Ch 2
- **Priority:** P1
- **Input:** F11 clusters + corridor grid + standardized 9-feature matrix (density + shares + diversity + isolation)
- **Output:** Each grid cell labeled with type name (fuel_hub / mixed_commercial / residential_edge / rural)
- **Dependencies:** F11, F13, F14
- **Acceptance:** Silhouette score > 0.3 at chosen k. Type names inspected and validated against centroid profiles.

---

**F13. Data-Driven Grid Size**
- **Chapter:** UA Advanced Ch 2 (mean cluster span → cell size)
- **Priority:** P1
- **Input:** F11 clusters
- **Output:** `CELL_M` value (rounded from mean cluster span)
- **Dependencies:** F11
- **Acceptance:** Grid cell size matches the scale of real Waco commercial districts (200-500m range expected).

---

**F14. Cell Features (Density + Diversity + Isolation)**
- **Chapter:** UA Advanced Ch 2
- **Priority:** P0
- **Input:** F10 POIs joined to F13 grid
- **Output:** Per-cell features: `total`, `share_{category}`, `diversity` (Shannon entropy), `nn_dist_m`
- **Dependencies:** F10, F13
- **Acceptance:** Feature distributions match Milan's expected ranges (median diversity > 0.5 for commercial cells).

---

**F15. Three-Screen Candidate Funnel**
- **Chapter:** UA Advanced Ch 2 (matcha-shop pattern)
- **Priority:** P0
- **Input:** F7 candidates + F11 clusters + F12 types + advertiser lift per cluster
- **Output:** Filtered candidate shortlist — passes (a) target type, (b) inside cluster, (c) cluster has advertiser-lift > 1.0
- **Dependencies:** F7, F11, F12
- **Acceptance:** Funnel counts printed at each screen. Final shortlist size 5-20.

---

**F16. 5-Min Drive-Time Isochrones Around IH-35 Exits**
- **Chapter:** UA Advanced Ch 3 (adapted walk → drive)
- **Priority:** P0
- **Input:** F1 area, `network_type='drive'`, `SPEED_KMH = 65`, `ISO_MINUTES = [3, 5, 10]`
- **Output:** Polygon isochrones per exit
- **Dependencies:** F1
- **Acceptance:** Isochrone polygons follow road network (not circles). Rendered on Folium map.

---

**F17. Per-Candidate Drive-Time to Advertiser Categories**
- **Chapter:** UA Advanced Ch 3 (sjoin_nearest pattern)
- **Priority:** P0
- **Input:** F7 candidates + F10 POIs + Pandana network from F16
- **Output:** Per-candidate columns: `min_fuel`, `min_qsr`, `min_hotel`, `min_bank`, `min_auto` (minutes)
- **Dependencies:** F7, F10, F16
- **Acceptance:** Nodes with no POI within `MAX_DIST_M` get `NaN`, not ceiling value. Sanity check: candidates near known Buc-ee's have `min_fuel < 1`.

---

**F18. AADT Snap-to-Nearest Candidate**
- **Chapter:** UA Advanced Ch 3 (`sjoin_nearest`)
- **Priority:** P0
- **Input:** F7 candidates + TxDOT AADT stations (from F3)
- **Output:** Per-candidate: `aadt_station_id`, `aadt_latest_qty`, `aadt_year`, `aadt_5yr_trend`
- **Dependencies:** F3, F7
- **Acceptance:** Every candidate has a snapped station. Distance to station <5km for corridor candidates. Sanity check: candidates near IH-35 mainlane have AADT > 60,000.

---

### LAYER 4 — Site Quality, Zoning, Valuation

---

**F19. Municipal Zoning Ingestion (City of Waco)**
- **Chapter:** UA Advanced Ch 4 (NYC Parks pattern)
- **Priority:** P0 (blocked on data request)
- **Input:** `Waco_Zoning_2026.gpkg` (obtained via email request to Development Services)
- **Output:** `waco_zoning.gpkg` clipped to F1 study area
- **Dependencies:** F1
- **Acceptance:** Overlay with satellite basemap shows commercial zones align with visible commercial land use.

---

**F20. Distance-to-Residential Setback Proxy**
- **Chapter:** UA Advanced Ch 4 (`sjoin_nearest` + `distance_col`)
- **Priority:** P0
- **Input:** F7 candidates + F19 residential-zone polygons
- **Output:** Per-candidate: `residential_dist_m`
- **Dependencies:** F7, F19
- **Acceptance:** Sanity check — candidates whose centroid falls in a residential zone report ~0m. If not, join is wrong.

---

**F21. NDVI Vegetation Buffer Feature**
- **Chapter:** UA Advanced Ch 4 (Sentinel-2 + buffer-mean NDVI)
- **Priority:** P1
- **Input:** F1 bbox + Sentinel-2 STAC (summer, cloud <10%) + F7 candidates
- **Output:** Per-candidate: `ndvi_10m`, `ndvi_50m`, `ndvi_100m`
- **Dependencies:** F1, F7
- **Acceptance:** NDVI robust range 2nd-98th pct within [-0.5, 0.9]. Sanity: candidate in downtown Waco `ndvi_50m < 0.3`; candidate near rural corn field `> 0.6`.

---

**F22. Sanity-Check Discipline**
- **Chapter:** UA Advanced Ch 4 (buildings-in-park must equal 0m)
- **Priority:** P0
- **Input:** Any spatial join
- **Output:** Assertion that catches silent bugs
- **Dependencies:** All spatial join features
- **Acceptance:** Every `sjoin_nearest` in Track A has a corresponding sanity check.

---

**F23. LiDAR Visibility / Obstruction Score**
- **Chapter:** GeoAI Ch 5 (learned) + GeoAI Ch 4 (learned)
- **Priority:** P1
- **Input:** McLennan LiDAR nDSM tile + F7 candidates + camera model (driver eye 1.5m, sign face 15-25m)
- **Output:** Per-candidate: `visibility_score` (0-1) + `unobstructed_seconds` at 65 mph
- **Dependencies:** F7, external LiDAR acquisition
- **Acceptance:** Proof-of-concept on one candidate. Full-corridor scale is Phase 5+.

---

**F24. Combined Visibility/Site-Quality Index**
- **Chapter:** UA Advanced Ch 4 (rank + min-max + equal-weight mean)
- **Priority:** P1
- **Input:** F21 NDVI + F23 visibility (when available) + F20 setback
- **Output:** Per-candidate: `site_quality_score` (0-1)
- **Dependencies:** F20, F21, F23 (partial ok)
- **Acceptance:** Correlation between components checked and reported.

---

**F25. Persona-Weighted Opportunity Score**
- **Chapter:** UA Advanced Ch 5
- **Priority:** P0
- **Input:** F17 demand + F18 traffic + F14 land use + F8 spacing + persona weights (sum to 1.0)
- **Output:** Per-candidate: `opportunity_score` (1-10)
- **Dependencies:** F8, F14, F17, F18
- **Acceptance:** Weights explicitly declared as hypotheses. `assert sum(WEIGHTS.values()) == 1.0`. Score matches manual eyeball rank for top 3.

---

**F26. Two-Unit Analysis (Candidates as Points vs Stretches)**
- **Chapter:** UA Advanced Ch 5 (MAUP discipline)
- **Priority:** P1
- **Input:** F7 candidates (points) + F8 preliminary_spacing_stretches (line segments)
- **Output:** Both units scored and compared
- **Dependencies:** F7, F8
- **Acceptance:** Side-by-side map with layer toggle. Documented as modeling choice.

---

**F27. Equal-Count Binning for Ranking**
- **Chapter:** UA Advanced Ch 5 (`pd.qcut`)
- **Priority:** P0
- **Input:** F25 opportunity_score
- **Output:** Per-candidate: `score_bin` (1-10, each holding equal count)
- **Dependencies:** F25
- **Acceptance:** Top 10% bin (bin 10) has correct count.

---

**F28. Land Lease Price Surface (Spatial Lag Regression)**
- **Chapter:** UA Advanced Ch 6
- **Priority:** P1
- **Input:** McLennan land sale records (from MCAD or third-party) + F17, F18, F21 features
- **Output:** Per-candidate: `predicted_monthly_lease_usd` + uncertainty range
- **Dependencies:** F17, F18, MCAD data
- **Acceptance:** OLS baseline + ML_Lag comparison. If Milan's finding replicates (lag adds nothing), report OLS as the honest model.

---

**F29. Per-Candidate Density Feature**
- **Chapter:** UA Advanced Ch 6 (KDTree radius count)
- **Priority:** P1
- **Input:** F7 candidates + TxDOT permit points (from F3)
- **Output:** Per-candidate: `existing_boards_within_500m`, `existing_boards_within_1500m`
- **Dependencies:** F3, F7
- **Acceptance:** Feeds directly into F8 spacing calculation. Assert projected CRS before counting.

---

**F30. OLS + Spatial Lag Model Comparison**
- **Chapter:** UA Advanced Ch 6
- **Priority:** P1
- **Input:** F28 target + features
- **Output:** Comparison table (R², AIC, rho) + honest verdict (which model to use for prediction)
- **Dependencies:** F28
- **Acceptance:** Milan's discipline — if spatial lag term is not statistically significant, use OLS.

---

### LAYER 5 — Regulatory RAG (Track B)

---

**F31. Regulatory Corpus Assembly**
- **Chapter:** External
- **Priority:** P0
- **Input:** 43 TAC Ch 21 + 23 CFR 750 + Waco sign ordinance + McLennan county ord.
- **Output:** `docs/corpus/` — PDFs/HTML with `source.yaml` sidecars each
- **Dependencies:** None
- **Acceptance:** 4-6 documents with attribution. F4 provenance rule applied.

---

**F32. Semantic Chunking with Section Metadata**
- **Chapter:** External
- **Priority:** P0
- **Input:** F31 corpus
- **Output:** Chunks with preserved subsection headers as metadata
- **Dependencies:** F31
- **Acceptance:** Query "spacing rule for interstate" returns chunks containing the actual rule, not headers.

---

**F33. Embedding + pgvector Storage**
- **Chapter:** External
- **Priority:** P0
- **Input:** F32 chunks + embedding model (Voyage or OpenAI text-embedding-3)
- **Output:** pgvector table with embeddings + metadata
- **Dependencies:** F32
- **Acceptance:** ANN search returns top-5 in <100ms.

---

**F34. Citation-Required Retrieval Chain**
- **Chapter:** External
- **Priority:** P0
- **Input:** Natural language question + F33 vector store
- **Output:** `{answer, citation, confidence}` — reject if no citation
- **Dependencies:** F33
- **Acceptance:** 10 golden queries return correct 43 TAC subsection citation with ≥80% precision.

---

**F35. Structured Rule Extraction**
- **Chapter:** External + LLM (Claude)
- **Priority:** P1
- **Input:** F31 corpus + rule schema from `project_oohscout_data.md`
- **Output:** `verified_rules.json` with `verification_status: draft` per rule
- **Dependencies:** F31
- **Acceptance:** ≥50 rules extracted covering: spacing tiers, height limits, setbacks, sign size classes, digital rules.

---

**F36. Human-Review Workflow**
- **Chapter:** External
- **Priority:** P1
- **Input:** F35 draft rules + human reviewer
- **Output:** Rules with `verification_status: verified` + `verified_by` + `verified_at`
- **Dependencies:** F35
- **Acceptance:** Design doc for review workflow exists. At least 5 rules verified by human.

---

### LAYER 6 — Agent Capstone (Track C)

**Early learning checkpoint (not a numbered feature):** After F7, an experimental Scout shell may wrap read-only Track A functions for Chapter 14 practice. It may report supported scope, existing signs, POIs, AADT stations, and unverified scouting points. All points remain `REVIEW`. This checkpoint does not satisfy F37 or F39, does not call Track B, and does not change the Phase 4 integration gate.

---

**F37. ReAct Loop with Tool-Calling LLM**
- **Chapter:** GeoAI Ch 14
- **Priority:** P0
- **Input:** User query + tool registry
- **Output:** Multi-step reasoning trace ending in answer + tool call sequence
- **Dependencies:** F39, F40
- **Acceptance:** Milan's Manhattan example reproduced. Swap Groq for Claude (or keep Groq for cost). Loop terminates in <10 iterations.

---

**F38. STRtree Spatial Index**
- **Chapter:** GeoAI Ch 14
- **Priority:** P1
- **Input:** F7 candidates + F10 POIs + F3 permits
- **Output:** In-memory `STRtree` indexes per layer + O(log n) radius queries
- **Dependencies:** F3, F7, F10
- **Acceptance:** Benchmark shows 10x speedup vs brute force at 10k+ points.

---

**F39. Track A Functions Wrapped as Tools**
- **Chapter:** External (Ch 14 shows pattern)
- **Priority:** P0
- **Input:** Track A modules
- **Output:** Pydantic-typed tool functions: `tool_get_corridor()`, `tool_find_candidates()`, `tool_score_candidate()`, `tool_check_spacing()`, `tool_get_isochrone()`, `tool_get_aadt()`
- **Dependencies:** F1-F30
- **Acceptance:** Every tool has Pydantic input/output schema. Every tool has ≥3 unit tests.

---

**F40. Track B RAG Wrapped as Tool**
- **Chapter:** External (Ch 14 pattern)
- **Priority:** P0
- **Input:** `tool_query_regulation(question, jurisdiction)`
- **Output:** `{answer, citation, confidence}`
- **Dependencies:** F34
- **Acceptance:** Never returns answer without citation. Confidence range [0, 1].

---

**F41. Golden-Case Evaluation Harness**
- **Chapter:** External
- **Priority:** P0
- **Input:** 15 curated NL queries with expected tool call sequences + expected answers
- **Output:** Pass/fail report per case + overall score
- **Dependencies:** F37, F39, F40
- **Acceptance:** ≥12/15 pass. Regression-tested on every agent code change.

---

### LAYER 7 — Deliverables

---

**F42. Folium Interactive Map with Layer Toggles**
- **Chapter:** UA Advanced Ch 2/3/5
- **Priority:** P0 (already partially shipped)
- **Input:** All candidate data + score
- **Output:** Standalone HTML with 4+ layers: corridor, candidates (color-coded by score), POIs, existing permits, isochrones
- **Dependencies:** F42-scoped subset of Track A features
- **Acceptance:** Layers toggle independently. Popups show per-candidate breakdown with citations.

---

**F43. CSV / GeoPackage Per-Candidate Exports**
- **Chapter:** UA Advanced Ch 1 (GeoPackage discipline)
- **Priority:** P0
- **Input:** All candidate data
- **Output:** `mclennan_candidates.gpkg` (projected coords, RFC-compliant) + `mclennan_candidates_report.csv`
- **Dependencies:** F42
- **Acceptance:** GeoPackage reads correctly in QGIS. CSV opens in Excel with human-readable column headers.

---

**F44. Landowner PDF Site Packet**
- **Chapter:** External (WeasyPrint or Puppeteer)
- **Priority:** P2 (Phase 5+)
- **Input:** Single candidate ID
- **Output:** 1-page PDF with map + numbers + rule citations + landowner info + legal disclaimer
- **Dependencies:** F7-F30, MCAD data
- **Acceptance:** Renders in Chrome preview. Landowner name/address correct.

---

**F45. Web Dashboard (React + MapLibre)**
- **Chapter:** External
- **Priority:** P2 (Phase 5+)
- **Input:** FastAPI backend + candidate data
- **Output:** React SPA with map + ranked table + chat interface
- **Dependencies:** F1-F41 all shipped
- **Acceptance:** Loads corridor + candidates in <3 seconds. Chat routes to agent.

---

**F46. Unpermitted Billboard Detection (Optional Portfolio Exhibit)**
- **Chapter:** GeoAI Ch 7
- **Priority:** P2
- **Input:** NAIP aerial imagery + hand-annotated billboard training set + TxDOT permit ground truth
- **Output:** Detected billboard boxes + confidence + mismatch list (detected without matching permit)
- **Dependencies:** External imagery, hand-annotation
- **Acceptance:** ≥50% recall on validation set. False-positive rate documented.

---

**F47. Alternative Clustering (Redundant with UA Ch 2)**
- **Priority:** SKIP (UA Ch 2 covers)

---

**F48. New Commercial Construction Radar**
- **Chapter:** GeoAI Ch 9 (Change Detection)
- **Priority:** P2
- **Input:** Multi-temporal Sentinel-2 imagery
- **Output:** Alerts on newly-cleared parcels in corridor
- **Dependencies:** F1 area
- **Acceptance:** Detects Buc-ee's-scale construction. Documented false-positive limitations.

---

**F49. Aerial Patch Classification (Where Zoning Missing)**
- **Chapter:** GeoAI Ch 6 (Patch Classification)
- **Priority:** P2
- **Input:** NAIP tiles + labeled examples
- **Output:** Per-tile: commercial / residential / rural / mixed
- **Dependencies:** External imagery
- **Acceptance:** Used only where municipal zoning unavailable.

---

**F50. Traffic Trend Forecasting**
- **Chapter:** GeoAI Ch 10 (Spatio-temporal)
- **Priority:** P2
- **Input:** TxDOT AADT 5-year history per station
- **Output:** Forecast AADT +3 years per candidate
- **Dependencies:** F18
- **Acceptance:** MAE < 10% on backtest.

---

**F51. Demand Surface Interpolation**
- **Chapter:** GeoAI Ch 12 (Spatial Interpolation)
- **Priority:** P2
- **Input:** F14 sparse cell demand values
- **Output:** Continuous demand surface between candidates
- **Dependencies:** F14
- **Acceptance:** Smooth surface. Visualized as raster overlay on Folium.

---

**F52. Zero-Shot Land-Use via SAM/CLIP**
- **Chapter:** GeoAI Ch 13 (Foundation Models)
- **Priority:** P2
- **Input:** Aerial tile + text prompt ("commercial building", "vacant lot")
- **Output:** Segmentation masks + confidence
- **Dependencies:** External imagery
- **Acceptance:** Reduces manual labeling on 10 sample tiles.

---

## 7. Feature Dependencies (Graph)

```
Foundation Layer (F1-F5):
  F1 → F2 → {F6, F7, F10, F16, F19, F21}
  F3 (independent, feeds many)
  F4 (attaches to F3)
  F5 (test-flag, orthogonal)

Corridor Engine:
  F2 → F6 (buffer)
  F2 → F7 (candidates)
  F7 + F9 → F8 (spacing engine)
  F9 (research, independent)

Demand:
  F10 → F11 → F12 → F15
  F11 → F13 → F14
  F1 → F16
  F7 + F10 + F16 → F17
  F3 + F7 → F18

Site Quality:
  F19 → F20
  F21 (Sentinel, F1 only)
  F23 (LiDAR — proof only)
  F20 + F21 + F23 → F24

Scoring:
  F8 + F14 + F17 + F18 → F25 → F26 → F27
  MCAD + F17 + F18 → F28 → F30
  F3 + F7 → F29

Track B (isolated):
  F31 → F32 → F33 → F34
  F31 → F35 → F36

Track C (integrates):
  F1-F30 → F39 (tool wrappers)
  F34 → F40 (RAG tool)
  F39 + F40 → F37 (agent) + F38 (index)
  F37 → F41 (evals)

Deliverables:
  F27 → F42 → F43
  F42 + MCAD → F44
  F41 → F45

Optional Exhibits (independent):
  F46, F48, F49, F50, F51, F52
```

---

## 8. Data Requirements

### 8.1 Required data sources (with license status)

| Source | Data | License | Blocker? |
|---|---|---|---|
| TxDOT Commercial Signs REST | 182 real permits in McLennan | Public, confirm with csrp@txdot.gov before redistribution | ✅ Working now |
| TxDOT AADT REST | 819 stations in McLennan, 5-yr history | Public | ✅ Working now |
| OSM Overpass | POIs, roads, land use, buildings | ODbL (attribution required) | ✅ Working now |
| Sentinel-2 via STAC | 10m multispectral for NDVI | Free, public | ✅ Working now |
| MCAD parcels | 116K parcels + owner data | Requires request or paid vendor | ⚠️ Pending email request |
| City of Waco zoning | Municipal zoning polygons | Requires request | ⚠️ Pending email request |
| USGS 3DEP LiDAR | 0.5-1m nDSM | Public | ⚠️ Requires tile acquisition |
| NAIP aerial | 60cm imagery | Public | ⚠️ Optional (Phase 6+) |
| 43 TAC Chapter 21 text | Legal document | Public statutes | ✅ Available |
| 23 CFR Part 750 text | Legal document | Public statutes | ✅ Available |
| Waco sign ordinance | Municipal code | Public | ✅ Available |

### 8.2 Provenance record schema (per F4)

```yaml
source_name: "TxDOT Commercial Signs"
source_url: "https://services.arcgis.com/.../Commercial_Signs_Test/FeatureServer/0"
retrieval_date: "2026-08-28"
retrieval_method: "ArcGIS REST API query"
record_count_at_retrieval: 182
license: "TxDOT ArcGIS Open Data (public, attribution recommended)"
commercial_use_allowed: "confirm with csrp@txdot.gov"
redistribution_allowed: "confirm with csrp@txdot.gov"
freshness: "TxDOT continuously updates as permits are issued/revoked"
authority: "Texas Department of Transportation, Right of Way Division"
verified_by: "OOHScout data verification 2026-08-28"
notes: "Layer name 'Commercial_Signs_Test' but contains live production data"
```

---

## 9. Regulatory & Legal Requirements

- **R1.** Never label a site "LEGAL." Always "passed automated preliminary screening; final eligibility requires municipal/professional verification."
- **R2.** Cite exact 43 TAC subsection for every spacing claim (not §391.031).
- **R3.** Every rule extracted from RAG has `verification_status: draft` until human-reviewed.
- **R4.** Legal disclaimer on every generated PDF or export.
- **R5.** TxDOT commercial reuse must be confirmed before any paid deliverable.

---

## 10. Milestones & Roadmap

Reference: `docs/MASTER_PLAN.md` Section 4 + `docs/FEATURES.md` for full ownership map.

- **M1** (Week 4): Foundation shipped (F1-F5) after UA Adv Ch 1
- **M1a** (after F7): Experimental Track-A-only Scout shell; no recommendations and no Track B integration
- **M2** (Week 10): Track A demand engine (F10-F18) after UA Adv Ch 2 + 3
- **M3** (Week 14): Spacing engine live (F6-F9)
- **M4** (Week 18): Site quality + scoring (F19-F30)
- **M5** (Week 22): Track B RAG standalone (F31-F36)
- **M6** (Week 25): Track C agent + integration (F37-F41)
- **M7** (Week 27): Portfolio polish + first paid corridor (F42-F45)

Total: ~27 weeks at ~10-12 hrs/week.

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| MCAD data request delayed/denied | Blocks F19, F20, F28 | Fallback: Regrid subscription (~$500/mo) |
| Waco zoning shapefile unavailable free | Blocks F19 | Fallback: OSM `landuse` proxy + F49 patch classification |
| 43 TAC rules ambiguous for specific cases | Blocks F9 exactness | Human legal reviewer in Phase 3 |
| Milan's Ch 14 uses Groq/Llama, we prefer Claude | Portability risk | Adapter pattern in F37 llm_client |
| Operator says "no interest" | Kills MVP | Pivot to portfolio-only launch (still valuable) |
| LiDAR tile acquisition slow | Delays F23 | Proof-of-concept on one candidate is enough for MVP |
| Portfolio launch attracts competitor attention | Copycat risk | Track B (verified_rules moat) is hard to replicate |

---

## 12. Open Questions

- **Q1.** Groq/Llama vs Claude for the agent — which does user prefer? (Deferred to F37)
- **Q2.** Portfolio launch timing — after M6 or M7?
- **Q3.** Will Waco operator agree to a 30-min feedback session at M2 gate?
- **Q4.** Do we need `verified_rules` reviewer to be a licensed attorney, or does a Milan-style disciplined reviewer suffice?

---

*End of PRD. Update per phase gate.*
