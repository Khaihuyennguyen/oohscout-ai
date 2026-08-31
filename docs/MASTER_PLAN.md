# OOHScout AI — Master Plan Document

**Last updated:** 2026-08-29
**Purpose:** Single source of truth combining current feature status, product user stories, technical architecture, and immediate next step. Revisit this document before starting any session.

**Companion documents:**
- `CLAUDE.md` — project rules and coding standards
- `OOHSCOUT_FEATURES.md` — full 52-feature list mapped to course chapters
- `DATA_VERIFICATION_REPORT.md` — real vs synthetic data audit

---

## SECTION 1 — Current Feature Status

### Honest count (as of 2026-08-29)

**Total features in scope:** 52 numbered + 1 infra follow-up (F1a)
**Actually shipped (working on real Waco data):** 6 (F1, F1a, F2, F3, F4, F42)
**In progress:** 0
**Queued next:** F5 (test-bbox subset for DEV_MODE fast iteration)
**Partial/prototype only:** 3 (F6, F7, F43)
**Technique learned but not applied to Waco:** 2 (F21, F23)
**Not started:** 41

### Feature-by-feature status

| # | Feature | Status | Evidence |
|---|---|---|---|
| 3 | Multi-source ingestion + cache pattern | ✅ **Shipped** | `oohscout_real_txdot_data.ipynb` — TxDOT billboards + AADT + OSM all cached |
| 42 | Folium interactive map with layer toggles | ✅ **Shipped** | Both notebooks produce clickable HTML maps |
| 23 | LiDAR obstruction (semantic segmentation technique) | 🎓 **Technique learned, not applied to Waco** | Ch 5 done on Edinburgh; needs McLennan LiDAR + one candidate application |
| 21 | NDVI vegetation buffer (technique from Ch 4) | 🎓 **Technique learned, not applied** | Ch 4 done; not integrated into Waco pipeline |
| — | GeoAI Ch 4 & 5 course techniques | 🎓 **Learned** | Explanation files in `notebooks/` |
| 43 | GeoPackage exports | ⚠️ **Partial** | Currently using GeoJSON with projected coords (RFC-noncompliant) |
| 1 | Retargetable study area | ✅ **Shipped 2026-08-29** | McLennan County resolved via OSMnx, projected to EPSG:32614, area 2,747.3 km² (0.05% off Census). Cache: `backend/data/processed/mclennan_county_study_area.gpkg`. Notebook: `docs/learning/chapters/ua_advanced_ch01_setup/03_oohscout_adaptation.ipynb`. Production module: `backend/src/oohscout/track_a_spatial/study_area.py`. Visual check: `backend/data/processed/mclennan_f1_check.png`. Module made importable by F1a. |
| 1a | Make `backend/src/oohscout/` installable + smoke test | ✅ **Shipped 2026-08-29** | `pyproject.toml` uses hatchling; `uv sync` installs `oohscout-ai==0.0.1` editable; `from oohscout.track_a_spatial import load_or_build_study_area` works; 5 pytests pass in `backend/tests/track_a/test_study_area.py`. Notebook and module both compute area = 2,747.33 km². Branch: `feature/f1a-installable-package`. |
| 2 | Base geometry — IH-35 centerline for McLennan | ✅ **Shipped 2026-08-29** | 245 LineString segments, 131 km, `osmid` unique. Cache: `backend/data/processed/mclennan_ih35_centerline.gpkg`. Chapter folder: `docs/learning/chapters/ua_advanced_ch01_ih35/`. Production module: `backend/src/oohscout/track_a_spatial/corridor.py`. 7 pytests pass. |
| 5 | Test-bbox subset | ❌ **Not started (proper form)** | Waco urban subset for fast iteration; will use F1 admin_poly + F2 corridor as inputs |
| 4 | Provenance metadata | ✅ **Shipped 2026-08-30** | `SourceRecord` + `write_source_yaml` + `audit_provenance` in `backend/src/oohscout/data/provenance.py`. F1 + F2 datasets each have `.source.yaml` sidecars. 7 pytests. Branch: `feature/f4-provenance-metadata`. |
| 6, 7 | Corridor buffer, candidate sampling | ⚠️ **Prototype only** | In `oohscout_texas_corridor.ipynb` but techniques come from unstudied chapters |
| 8, 9 | LRS spacing engine, 43 TAC rule table | ❌ **Not started** | Blocked on rule research |
| 10–18 | UA Ch 2 + Ch 3 features | ❌ **Not started** | Need to study chapters |
| 19–30 | UA Ch 4 + 5 + 6 features | ❌ **Not started** | Need to study chapters |
| 31–36 | Track B (RAG) | ❌ **Not started** | Locked in its own box until Track A ships |
| 37–41 | Track C (Agent) | ❌ **Not started** | Full integration locked until Track A + B ship; experimental Track-A-only Scout shell allowed after F7 |
| 44–52 | Delivery + optional exhibits | ❌ **Not started** | Phase 5+ |

### The next feature you should do

**F2 — Base Geometry: IH-35 highway centerline for McLennan County.**

**Why this one:**
- F1 + F1a are shipped. `admin_poly` from F1 is the input; the production module now sits in an installable package so F2's `corridor.py` will be importable from day one.
- Buildings-example pattern maps directly: swap `tags={"building": True}` for `tags={"highway": ["motorway"]}`, swap polygon-filter for LineString-filter.
- Same 5-file convention in a new chapter folder (probably `ua_advanced_ch01_ih35/`).
- Unlocks F6 (buffer) and F7 (candidate sampling).

**Branch to create:** `feature/f2-ih35-centerline` (branch off `main` after merging F1a).

**Completion gate:**
1. IH-35 centerline downloaded via `ox.features_from_polygon(admin_poly, tags={"highway": ["motorway"]})`.
2. Filtered to LineString-only.
3. Projected to EPSG:32614.
4. `assert osmid.is_unique` passes.
5. Total length within 10% of Google Maps' IH-35-through-McLennan reference.
6. Cached as `backend/data/processed/mclennan_ih35_centerline.gpkg`.
7. Production module `backend/src/oohscout/track_a_spatial/corridor.py` with `load_or_build_highway_centerline(admin_poly, cache_dir)` importable.
8. Pytest `backend/tests/track_a/test_corridor.py` passes with LineString-only + length + unique-osmid assertions.

**Early-agent decision:** After F7, build an experimental read-only Scout shell around Track A for motivation and Chapter 14 practice. It returns existing-market facts and unverified scouting points only. It does not recommend sites, call Track B, or complete F37/F39. Full Track A + Track B integration remains Phase 4.

---

## SECTION 2 — Product Manager View: The Whole App as User Stories

### Primary user persona

**Marcus, Regional Billboard Developer**
- Works for a mid-size Texas billboard operator (~30 boards in Central Texas)
- Age 42, 15 years in OOH industry, comfortable with maps but not GIS software
- KPI: add 3-5 profitable new sites per year to his pipeline
- Pain today: spends 2 weeks per site in windshield surveys + county records + phone calls
- Budget: $5-15K per corridor analysis

### Epic: "Find and evaluate new billboard sites on a Texas highway corridor"

### User stories (in order of user journey)

**Story 1 — Corridor scoping**
> As Marcus, I want to specify a highway + county so I can bound my search area.

*Acceptance:* Types "IH-35 through McLennan County" → system loads corridor geometry + jurisdiction.

**Story 2 — Automated candidate discovery**
> As Marcus, I want the system to propose ~20-40 candidate locations along the corridor so I don't have to drive it myself.

*Acceptance:* Candidates appear on a map, each with a unique ID (WA-000 through WA-039). Each candidate has coordinates I can pull up on Google Street View.

**Story 3 — Preliminary spacing screening**
> As Marcus, I want each candidate flagged as "passed" or "failed" preliminary spacing rules so I don't waste time on locations that would never get permitted.

*Acceptance:* Each candidate carries `reg_status = PASS | FAIL | REVIEW` with the spacing rule cited. The word "LEGAL" never appears — always "passed preliminary screening."

**Story 4 — Advertiser demand signal**
> As Marcus, I want each candidate scored by nearby advertiser demand (fuel stations, QSRs, hotels) so I can prioritize revenue-generating sites.

*Acceptance:* Each candidate shows a demand score based on POI density within a 5-minute drive-time isochrone. I can see which QSRs are near (Buc-ee's, McDonald's, etc.).

**Story 5 — Real traffic verification**
> As Marcus, I want each candidate matched to real TxDOT AADT so I can defend traffic numbers to my acquisitions committee.

*Acceptance:* Each candidate shows nearest TxDOT AADT station ID, current-year AADT, and 5-year trend. Numbers are hyperlinked to TxDOT's official site so anyone can verify.

**Story 6 — Regulatory question in plain English**
> As Marcus, I want to ask "what's the minimum spacing for a 14×48 static bulletin on IH-35 in unincorporated McLennan?" and get an answer with a legal citation.

*Acceptance:* Chat interface returns answer + 43 TAC Chapter 21 subsection citation + confidence level. "Passed preliminary screening; final eligibility requires municipal verification" language is always included.

**Story 7 — Landowner identification**
> As Marcus, I want to know who owns the parcel under a candidate so I can send an offer.

*Acceptance:* Each candidate shows parcel owner name + mailing address + property tax value. Data sourced from MCAD with license attribution.

**Story 8 — Lease estimate**
> As Marcus, I want a rough monthly lease estimate range so I can plan my offer.

*Acceptance:* Each candidate has a lease range (e.g. "$800-$1,400/month") with the model + inputs shown, not a single fake number. Uncertainty band displayed.

**Story 9 — Ranked shortlist**
> As Marcus, I want to see the top 10 candidates ranked by combined opportunity score so I can focus my week.

*Acceptance:* Sortable table with candidates ranked 1-10. Each row shows the factor breakdown (traffic 30% × demand 30% × landuse 25% × spacing 15%).

**Story 10 — Site packet export**
> As Marcus, I want to export a one-page site packet (map + numbers + rules + owner) so I can share with my acquisitions team.

*Acceptance:* PDF download per candidate. Includes map, key metrics, rule citations, landowner contact, disclaimer that final eligibility requires attorney review.

**Story 11 — Natural language query (agent capstone)**
> As Marcus, I want to type "find candidates near clusters of QSRs with AADT ≥ 80,000 that pass spacing" and get results without navigating menus.

*Acceptance:* Agent parses the query, calls the right tools in sequence, returns map + ranked table + reasoning trace showing which tools it used.

### Secondary personas (Phase 6+)

- **Regulatory Compliance Officer** — evaluates a single proposed site against rules
- **Investor / Analyst** — evaluates a portfolio for acquisition due diligence
- **Landowner** (inbound) — receives a lease offer with market context

### What the app is NOT (scope discipline)

- **Not** a nationwide SaaS. MVP is McLennan County only.
- **Not** a real-time ad-serving platform. Focus is site development, not advertising.
- **Not** a legal advisor. Always "passed preliminary screening" language.
- **Not** a foot-traffic analytics tool. POIs proxy for demand; not real footfall.
- **Not** a replacement for a Waco billboard attorney. Complement, not substitute.

---

## SECTION 3 — Senior Architect View: How the Code Connects

### Three-tier architecture with three tracks

```
┌───────────────────────────────────────────────────────────┐
│                      USER INTERFACE                        │
│                                                            │
│  MVP:  Jupyter notebooks + Folium HTML maps                │
│  P5+:  FastAPI backend + React/MapLibre frontend + PDF    │
└─────────────────────────┬─────────────────────────────────┘
                          │  (natural language OR structured query)
                          ▼
┌───────────────────────────────────────────────────────────┐
│         TRACK C — AGENT ORCHESTRATION LAYER                │
│                     (GeoAI Ch 14 pattern)                  │
│                                                            │
│  ┌───────────────────────────────────────────────────┐    │
│  │  ReAct Loop                                        │    │
│  │  ┌──────┐  ┌───────┐  ┌─────────┐  ┌──────────┐  │    │
│  │  │Query │→ │Thought│→ │ Action  │→ │Observ.   │→ │    │
│  │  └──────┘  └───────┘  └─────────┘  └──────────┘  │    │
│  │      ↑                                     │      │    │
│  │      └─────────────(loop)──────────────────┘      │    │
│  └───────────────────────────────────────────────────┘    │
│                                                            │
│  LLM: Claude Sonnet (or Groq/Llama per Ch 14)              │
│  Tool Registry: Pydantic-typed function schemas            │
└──────────┬────────────────────────────┬───────────────────┘
           │                            │
           │ calls spatial tools        │ calls regulatory tools
           ▼                            ▼
┌──────────────────────────┐   ┌───────────────────────────┐
│  TRACK A — SPATIAL       │   │  TRACK B — REGULATORY RAG  │
│  ENGINE                  │   │                            │
│                          │   │  ┌──────────────────────┐  │
│  Pure deterministic GIS  │   │  │ Retriever            │  │
│                          │   │  │ (pgvector + BM25)    │  │
│  Tools:                  │   │  └──────────┬───────────┘  │
│  - tool_get_corridor()   │   │             ▼              │
│  - tool_find_candidates()│   │  ┌──────────────────────┐  │
│  - tool_score_candidate()│   │  │ Reranker             │  │
│  - tool_get_isochrone()  │   │  │ (cross-encoder)      │  │
│  - tool_check_spacing()  │   │  └──────────┬───────────┘  │
│  - tool_get_owner()      │   │             ▼              │
│  - tool_predict_lease()  │   │  ┌──────────────────────┐  │
│                          │   │  │ Citation Extractor   │  │
│  Returns: strict JSON    │   │  │ (always w/ subsec)   │  │
│                          │   │  └──────────────────────┘  │
│                          │   │                            │
│                          │   │  Tool:                     │
│                          │   │  - tool_query_regulation() │
│                          │   │                            │
│                          │   │  Returns: {answer,         │
│                          │   │    citation, confidence}   │
└─────────────┬────────────┘   └────────────┬──────────────┘
              │                              │
              ▼                              ▼
┌──────────────────────────┐   ┌───────────────────────────┐
│  DATA LAYER              │   │  CORPUS LAYER              │
│                          │   │                            │
│  PostgreSQL + PostGIS +  │   │  pgvector table            │
│  pgvector                │   │  (shared with data layer)  │
│                          │   │                            │
│  Tables:                 │   │  Documents:                │
│  - corridors             │   │  - 43 TAC Ch 21 Subch I    │
│  - road_segments         │   │  - 23 CFR Part 750         │
│  - candidate_sites       │   │  - Waco sign ordinance     │
│  - billboards (TxDOT)    │   │  - McLennan County ord.    │
│  - aadt_stations         │   │                            │
│  - business_pois         │   │  Structured extract:       │
│  - land_use              │   │  - verified_rules JSON     │
│  - parcels (MCAD)        │   │                            │
│  - site_scores           │   │                            │
│                          │   │                            │
│  Cache:                  │   │                            │
│  - GeoPackage files on   │   │                            │
│    disk for offline use  │   │                            │
└─────────────┬────────────┘   └────────────┬──────────────┘
              │                              │
              └──────────────┬───────────────┘
                             ▼
┌──────────────────────────────────────────────────────────┐
│  INGESTION LAYER (batch + scheduled)                     │
│                                                          │
│  - TxDOT REST API (billboards, AADT)                    │
│  - OSM Overpass API (POIs, roads, buildings, land use)  │
│  - Sentinel-2 STAC (NDVI, land use context)             │
│  - MCAD parcel data (pending request)                    │
│  - City of Waco zoning (pending request)                │
│  - USGS 3DEP LiDAR (visibility analysis, Phase 5)       │
└──────────────────────────────────────────────────────────┘
```

### Architectural rules (never violate)

1. **Data flows one way, top to bottom:** UI → Agent → Tools → Track A/B → Data → Ingestion. Never the reverse.
2. **Track A never asks Track B, and vice versa.** They only communicate through the Agent.
3. **Track A never calls the LLM.** Spatial calculations are deterministic. If a Track A tool needs interpretation, it returns raw data and the Agent interprets.
4. **Track B always returns `{answer, citation, confidence}`.** No answer without a citation. If retrieval fails, return `{answer: null, reason: "no matching regulation found"}` — never hallucinate.
5. **The Agent orchestrates but never calculates.** No spatial math in LLM prompts. No lease pricing in LLM prompts.
6. **PostGIS is the source of truth.** GeoPackage files on disk are cache/offline artifacts, not primary storage. When they diverge from PostGIS, PostGIS wins.
7. **Every tool has a Pydantic schema.** Input and output. This is what makes tool-calling deterministic.
8. **The word "LEGAL" appears nowhere.** Always "preliminary screening; final eligibility requires municipal verification."

### Repository layout (target state)

```
billboardAI/
├── CLAUDE.md                          # project rules
├── OOHSCOUT_FEATURES.md               # 52-feature master list
├── OOHSCOUT_MASTER_PLAN.md            # this file
├── DATA_VERIFICATION_REPORT.md        # data audit
│
├── notebooks/                         # Track A learning + prototyping
│   ├── phase0_intro/                  # Urban Analytics Intro exercises
│   ├── phase1_ch1_setup_waco.ipynb    # Feature 1, 2, 5, 43
│   ├── phase1_ch2_demand.ipynb        # Features 10-15
│   ├── phase1_ch3_isochrones.ipynb    # Features 16-18
│   ├── phase1_lrs_spacing.ipynb       # Features 6-8
│   ├── phase2_ch4_landuse.ipynb       # Features 19-24
│   ├── phase2_ch5_scoring.ipynb       # Features 25-27
│   ├── phase2_ch6_lease.ipynb         # Features 28-30
│   ├── phase2_visibility_lidar.ipynb  # Feature 23 applied to Waco
│   └── phase1_spacing_rules.md        # Feature 9 — legal research doc
│
├── src/
│   ├── oohscout/
│   │   ├── data/                      # Data ingestion + caching
│   │   │   ├── txdot.py               # TxDOT REST API client
│   │   │   ├── osm.py                 # OSMnx wrappers
│   │   │   ├── sentinel.py            # STAC + rasterio
│   │   │   ├── mcad.py                # MCAD parcel client
│   │   │   └── provenance.py          # source.yaml sidecar handling
│   │   │
│   │   ├── track_a_spatial/           # Track A functions
│   │   │   ├── corridor.py            # get_corridor, buffer, sample
│   │   │   ├── demand.py              # DBSCAN, KMeans, isochrones
│   │   │   ├── spacing.py             # LRS engine
│   │   │   ├── scoring.py             # persona-weighted opportunity score
│   │   │   ├── lease.py               # spatial lag lease model
│   │   │   └── visibility.py          # LiDAR U-Net raycast
│   │   │
│   │   ├── track_b_rag/               # Track B regulatory RAG
│   │   │   ├── corpus.py              # document ingestion
│   │   │   ├── chunker.py             # section-metadata chunking
│   │   │   ├── retriever.py           # pgvector + BM25 hybrid
│   │   │   ├── reranker.py            # cross-encoder
│   │   │   ├── extractor.py           # structured rule extraction
│   │   │   └── verified_rules.py      # human review workflow
│   │   │
│   │   ├── track_c_agent/             # Track C ReAct agent
│   │   │   ├── tools.py               # tool registry with Pydantic schemas
│   │   │   ├── react_loop.py          # Thought/Action/Observation loop
│   │   │   ├── llm_client.py          # LLM wrapper (Claude default)
│   │   │   └── evaluations.py         # golden test cases
│   │   │
│   │   ├── db/                        # PostGIS schema + migrations
│   │   │   ├── schema.sql
│   │   │   ├── migrations/
│   │   │   └── postgis_helpers.py
│   │   │
│   │   └── delivery/                  # Phase 5+ delivery layer
│   │       ├── api/                   # FastAPI endpoints
│   │       ├── pdf/                   # WeasyPrint site packets
│   │       └── ...
│
├── tests/
│   ├── track_a/
│   ├── track_b/
│   └── golden_cases/
│
├── data/                              # cached artifacts (gitignored)
│   ├── raw/                           # untouched downloads
│   ├── processed/                     # normalized GeoPackages
│   └── corpus/                        # RAG documents
│
└── deploy/                            # Phase 6+ infrastructure
    ├── docker/
    └── terraform/
```

### How a single query flows through the system (concrete example)

**Query:** *"Show me the top 3 candidates on IH-35 in McLennan County with AADT above 80,000 that pass preliminary spacing screening."*

1. **UI** captures query, sends to Agent endpoint.
2. **Agent** receives query with tool registry in system prompt.
3. **Agent Thought 1:** "I need corridor geometry first."
4. **Agent Action:** `tool_get_corridor(highway="IH-35", county="McLennan")`
5. **Track A** loads corridor from PostGIS (or GeoPackage cache).
6. **Agent Thought 2:** "Now find candidate sites."
7. **Agent Action:** `tool_find_candidates(corridor_id="ih35-mclennan")`
8. **Track A** samples every 1km, returns 40 candidates.
9. **Agent Thought 3:** "Filter by AADT ≥ 80,000."
10. **Agent Action:** `tool_get_aadt_for_candidates(ids=[...], min_aadt=80000)`
11. **Track A** joins to nearest AADT station, filters, returns 18 survivors.
12. **Agent Thought 4:** "Check spacing eligibility."
13. **Agent Action:** `tool_check_spacing_eligibility(candidate_ids=[...])`
14. **Track A** runs LRS engine, returns 12 with `preliminary_status: PASS`.
15. **Agent Thought 5:** "Score and rank."
16. **Agent Action:** `tool_score_candidates(candidate_ids=[...])`
17. **Track A** returns 12 candidates with opportunity scores.
18. **Agent Thought 6:** "User wants top 3."
19. **Agent Answer:** Top 3 with map, table, per-factor breakdown, citation to 43 TAC Ch 21 for the spacing rule (via `tool_query_regulation` if needed).

**No hallucination, no LLM math, every number traceable to a Track A tool, every rule to a Track B citation.**

---

## SECTION 4 — Immediate Next Step

**F1 is shipped as of 2026-08-29.** Next branch is F2 (IH-35 centerline for McLennan County).

**Step 1 — Close out F1:** Commit the F1 branch (Milan retype + adaptation + explanation + code-along + production module + docs), open PR into `main`, merge.

**Step 2 — Add production backend for F1:** The notebook is the learning artifact; the app-facing code is `backend/src/oohscout/track_a_spatial/study_area.py`. Its `load_or_build_study_area(place, crs_metric, cache_dir)` function is what FastAPI, agent tools, and tests import. The notebook is not called from production.

**Step 3 — Start F2 on a new branch (`feature/f2-ih35-centerline`):** Same three-notebook flow inside the same chapter folder (or a new `ua_advanced_ch01_ih35/`). Milan's building-fetch pattern applied to `tags={"highway": ["motorway"]}`. Filter LineString-only. Assert `osmid.is_unique`. Cache as `.gpkg`. Add production module `backend/src/oohscout/track_a_spatial/corridor.py` with `load_or_build_highway_centerline(admin_poly, cache_dir)`.

**Step 4 — Do not start the Scout shell until F7 is complete.**

---

*End of master plan. Update this document at every phase gate.*
