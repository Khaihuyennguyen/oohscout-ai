# OOHScout AI — Project Instructions for AI Agents

**READ THIS FILE FIRST BEFORE WRITING ANY CODE.**

This project has two layers running simultaneously:
1. **Learning layer** — working through the GeoAI Essentials book by Milan Janosov (Jupyter notebooks in `notebooks/`)
2. **Product layer** — building OOHScout AI, a real billboard site intelligence startup

Every skill learned from the book is applied directly to OOHScout. Do not treat these as separate projects.

---

## Step 1 — Read project memory before doing anything

Memory files are at:
```
c:\Users\nguye\.claude\projects\c--Users-nguye-Documents-billboardAI\memory\
```

Read these files in order:
1. `MEMORY.md` — index of all memories
2. `project_oohscout.md` — what the product is and the core thesis
3. `project_oohscout_architecture.md` — three-brain tech stack and agent design
4. `project_oohscout_build_plan.md` — 7 phases, 90-day roadmap, MVP definition
5. `project_oohscout_scoring.md` — opportunity scoring model and moat
6. `project_oohscout_learning.md` — Milan Janosov course map, learning philosophy
7. `project_oohscout_data.md` — data sources, licensing risks, regulatory engine

**Do not write a single line of code before reading these files.**

---

## Project identity

**Product name:** OOHScout AI  
**One-sentence thesis:** Build an AI-assisted OOH development desk that turns fragmented regulations, geospatial data, traffic, parcels, and market signals into a ranked acquisition pipeline — not another GIS map.  
**Working directory:** `c:\Users\nguye\Documents\billboardAI\`  
**Notebooks:** `notebooks/` (working directory for Jupyter)  
**Shared utility module:** `geoai_utils.py` — must exist in BOTH root AND `notebooks/`

---

## Architecture rules — never violate these

1. **PostGIS owns all spatial measurements.** Never let an LLM estimate distances, areas, or geometry. LLM interprets; PostGIS calculates.
2. **Regulatory eligibility is a hard gate.** PASS / FAIL / REVIEW — not a soft weighted score.
3. **Never label a site "LEGAL."** Always say "passed automated preliminary screening; final eligibility requires municipal/professional verification."
4. **RAG answers regulatory questions.** Deterministic GIS answers spatial questions. Keep these separate.
5. **No nationwide SaaS yet.** MVP = one corridor, 5-20 ranked candidate parcels.

---

## Tech stack (do not introduce alternatives without reason)

| Role | Tool |
|------|------|
| Spatial database | PostgreSQL + PostGIS + pgvector |
| Vector Python | GeoPandas + Shapely |
| Road networks | OSMnx |
| Raster | Rasterio |
| Agent orchestration | LangGraph |
| API | FastAPI |
| Web map | MapLibre GL |
| Frontend | React / Next.js |
| Package manager | uv (NOT pip, NOT conda) |
| Python version | 3.11 |

Run notebooks with: `uv run jupyter lab`  
Run scripts with: `uv run python <script.py>`

---

## Coding standards

- Book notebooks live in `notebooks/` — do not move them to the root
- `geoai_utils.py` must be kept in sync between root and `notebooks/` — copy when updated
- Never commit `.env` — secrets go there only (GROQ_API_KEY, GEE_PROJECT_ID)
- No credentials required for Chapters 1-12
- Every dataset in production code must carry license metadata: source, commercial_use_allowed, redistribution_allowed

## CRITICAL — Data folder structure

Notebooks use `DATA_DIR = Path('data/new_study')` — NOT just `Path('data')`.

The actual data location is:
```
notebooks/data/new_study/       ← THIS is where all data files must live
```

Root `data/` folder also exists but notebooks DO NOT read from it.
When adding new data files, always place them in `notebooks/data/new_study/`.

All chapter data files confirmed present in `notebooks/data/new_study/`:
- LiDAR: NT27SE/SW_50CM_DSM/DTM_PHASE5.tif (4 files, ~1.7 GB total)
- Sentinel-2: sentinel_edi_clear_5ch.tif, sentinel_hun_*.tif, sentinel_ts_*.tif (15 files)
- Vector: osm_buildings_edinburgh.geojson, osm_landuse_hungary.geojson, osm_pois_manhattan.geojson, manhattan_nta.geojson
- Dutch aerial: 2025_110000_477000_RGB_JPEG_hrl.tif
- Derived: lidar_ndsm_crop.tif, ch13_sam_*.tif

---

## Session progress (as of Aug 28, 2026)

**Completed:**
- Chapter 4 notebooks running ✓ (data prep for all 4 study areas)
- Chapter 5 notebooks running ✓ (semantic segmentation: buildings + trees)
- `notebooks/ch04_explanation.md` — full line-by-line explanation created
- `notebooks/ch05_explanation.md` — full line-by-line explanation created
- All data files consolidated to `notebooks/data/new_study/`
- **Phase 1 Texas corridor prototype CREATED** ✓
  - `notebooks/oohscout_texas_corridor.ipynb` — full runnable notebook (10 steps)
  - `notebooks/oohscout_texas_corridor_explanation.md` — line-by-line guide with flow diagrams
  - Corridor: IH-35 Hillsboro → Waco, TX (BBOX = [-97.25, 31.40, -96.95, 31.80])
  - Produces: ranked candidates table + Folium HTML map + CSV report
- **REAL government data verified and integrated** ✓
  - `DATA_VERIFICATION_REPORT.md` (project root) — full audit of every data source, with live API verification
  - `notebooks/oohscout_real_txdot_data.ipynb` — educational notebook pulling live TxDOT data
  - Verified endpoints (no API key required):
    - TxDOT Commercial Signs: 14,943 real permits statewide, 182 in McLennan County
    - TxDOT AADT: 819 real traffic stations in McLennan County (2021-2025)
  - Also audited geosign-ai repo (`C:\Users\nguye\.gemini\antigravity\scratch\geosign-ai\`):
    - Legal citation § 391.031 is WRONG — correct rule is 43 TAC Chapter 21
    - 26 "TxDOT-OOH-XXXXX" permits are SYNTHETIC (real format is PMT-HBA-XXXXX)
    - 444 parcels are procedurally generated, not real
    - Vision agent analyzes PIL-drawn cartoons, not satellite imagery
    - Spatial engine math is genuinely good; port that logic (not the data)

**Currently on:** Feature 1 — Retargetable Study Area, started on branch `feature/f1-retargetable-study-area`. McLennan parcel and Waco zoning requests are later data dependencies; they do not block F1.

**Agent sequencing decision (2026-08-29):** After F7, an experimental Track-A-only Scout shell may expose existing signs, POIs, AADT, and unverified scouting points. It must label all points `REVIEW`, must not integrate Track B, and does not count as F37/F39 completion. The full ReAct agent still integrates Track A + Track B only in Phase 4.

**Data priority for OOHScout (focus on these):**
- RIGHT NOW: osm_pois_manhattan.geojson, osm_landuse_hungary.geojson (technique = advertiser demand + zoning)
- LATER: lidar_ndsm_crop.tif, sentinel_edi_clear_5ch.tif (visibility/obstruction)
- SKIP: cloudy scenes, time-series, Dutch aerial, SAM files (not relevant to billboard siting)

**First technical milestone:** Given a corridor, the system automatically eliminates obviously unsuitable parcels and produces 5-20 candidates an experienced billboard operator agrees are worth investigating.

**First commercial milestone:** An operator pays for a second corridor analysis.
