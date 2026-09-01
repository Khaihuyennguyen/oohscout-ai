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

## Step 2 — Read the canonical architecture reference

[docs/PRODUCTION_ARCHITECTURE_V2.md](docs/PRODUCTION_ARCHITECTURE_V2.md) is authoritative. It supersedes V1. Every pattern is verified against GeoLibre source at commit `a6fad468` (~18 kLOC + 4 kLOC docs read end-to-end).

Use it as:
- **§2 Pattern Inventory** — the recipe book for security (S1-S17), architecture (A1-A8), agent (AG1-AG6), MCP (M1-M5), distribution (D1-D5).
- **§3 Corrected folder layout** — the target shape for `backend/src/oohscout/`.
- **§5 Top 10 Files to Port** — the ordered work queue.

Do not re-derive architecture decisions. If V2 has a pattern, use it.

---

## Project identity

**Product name:** OOHScout AI
**One-sentence thesis:** Build an AI-assisted OOH development desk that turns fragmented regulations, geospatial data, traffic, parcels, and market signals into a ranked acquisition pipeline — not another GIS map.
**Working directory:** `c:\Users\nguye\Documents\billboardAI\`
**Notebooks:** `notebooks/` (working directory for Jupyter)
**Shared utility module:** `geoai_utils.py` — must exist in BOTH root AND `notebooks/`

---

## Architecture rules — never violate these

### Domain rules
1. **PostGIS owns all spatial measurements.** Never let an LLM estimate distances, areas, or geometry. LLM interprets; PostGIS calculates.
2. **Regulatory eligibility is a hard gate.** PASS / FAIL / REVIEW — not a soft weighted score.
3. **Never label a site "LEGAL."** Always say "passed automated preliminary screening; final eligibility requires municipal/professional verification." The `RegulatoryStatus` field-validator in [project.py](backend/src/oohscout/project.py) enforces this at the schema boundary.
4. **RAG answers regulatory questions.** Deterministic GIS answers spatial questions. Keep them separate.
5. **No nationwide SaaS yet.** MVP = one corridor, 5-20 ranked candidate parcels.

### Layering — three-layer authoring stack (V2 §A1)
6. **`project.py` → `authoring.py` → callers.** Pure builders (return dicts, no I/O) → pure transforms on project dicts (atomic writes, credential redaction) → `api/` and `mcp/server.py` delegate every write to `authoring.py`.
7. **The dependency direction is one-way.** `project.py` and `authoring.py` MUST NOT import from `api/` or `mcp/`. Verified by import graph — do not break it.
8. **The `.oohscout.json` file is the single source of truth.** No server-side session state. Read the file, apply a change, write it back.

### Security — do all of these on every code path (V2 §2.1)
9. **Every project write is atomic.** Temp file + `os.replace()`. Never bare `open(...).write(...)` for project data. (S16)
10. **Every project overwrite requires `PROJECT_MARKERS`.** Refuse to write if the file lacks `oohscout_version` / `corridor_id` — proves it's actually an OOHScout project, not `package.json`. (S4)
11. **Every LLM-supplied SQL must pass `check_sql_safety()`.** SELECT / WITH only. Reject INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/TRUNCATE/etc. — including inside CTEs and after masking string literals. (S8)
12. **Every URL fetched from the internet must pass `assert_public_url()`.** Resolve DNS, reject private/link-local/CGNAT/localhost/metadata endpoints. Re-check on every redirect hop. Cap response bodies at 50 MB. (S6, S13)
13. **Every DB / handler error must pass through `sanitize_error()`** before returning to any caller — strips `user:password@host` URL segments and `password=` kv pairs. Wired in [api/errors.py](backend/src/oohscout/api/errors.py). (S10)
14. **Every MCP tool must be wrapped by `_reports_its_errors`.** Bare `@server.tool()` silently masks error messages. Force every tool through the wrapper helper. (M1)
15. **Every path from a tool call must resolve inside the `Workspace` root.** Use `Path.resolve()` **before** the containment check (catches symlink escapes). Enforce an extension allowlist for writes. (S5)
16. **Every float entering the project dict must pass a `_finite()` guard.** No `NaN` / `inf` — JSON serializers disagree and it corrupts round-trips. (S15)
17. **Every project save must strip credentials.** `redact_credentials()` walks the tree; TxDOT keys, Regrid keys, Groq/Anthropic keys, county portal credentials never touch disk. (S12)
18. **Every FastAPI request needs sidecar token auth.** `X-OOHScout-Token` header, compared as bytes via `hmac.compare_digest`. `/health` is the only exempt path. Wired in [api/auth.py](backend/src/oohscout/api/auth.py). (S1)
19. **PostGIS sessions have a 60 s statement timeout.** Set `statement_timeout=60000` on every psycopg connect. Also use a read-only `oohscout_ro` role for agent SQL. (S9)

---

## Tech stack (do not introduce alternatives without reason)

| Role | Tool |
|------|------|
| Spatial database | PostgreSQL + PostGIS + pgvector |
| Vector Python | GeoPandas + Shapely |
| Road networks | OSMnx |
| Raster | Rasterio |
| Agent orchestration | LangGraph (Track C, Phase 4) |
| API | FastAPI (sidecar pattern: local-only, per-launch token) |
| MCP server | official `mcp` Python SDK (optional extra) |
| Web map | MapLibre GL (deferred until payment signal) |
| Frontend | React / Next.js (deferred until payment signal) |
| Package manager | uv (NOT pip, NOT conda) |
| Python version | 3.11 |

Run notebooks with: `uv run jupyter lab`
Run scripts with: `uv run python <script.py>`

**Dependency discipline (V2 §A3):** `pyproject.toml` uses optional-extras. Core deps stay minimal (`fastapi`, `uvicorn`, `pydantic`). Everything else (`geopandas`, `psycopg`, `rasterio`, `osmnx`, `mcp`) is an extra. The `[test]` extra installs *everything* so tests don't lie by skipping.

---

## Coding standards

- Book notebooks live in `notebooks/` — do not move them to the root
- `geoai_utils.py` must be kept in sync between root and `notebooks/` — copy when updated
- Never commit `.env` — secrets go there only (GROQ_API_KEY, GEE_PROJECT_ID)
- No credentials required for Chapters 1-12
- Every dataset in production code must carry license metadata: source, commercial_use_allowed, redistribution_allowed
- Production functions take parameters (place, highway, EPSG). Never bake `McLennan` / `IH-35` into names or bodies. Notebooks pass the concrete values.
- Add `nbstripout` to pre-commit — notebooks have API keys in cell outputs. (S17)

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

## Session progress (as of 2026-08-31)

**On branch:** `feature/f5-test-bbox`

**Shipped to `main`:**
- **F1a** — `backend/src/oohscout` installable package + smoke tests (commit `c711d4a` → merge `5d1e9b8`)
- **F1** — Retargetable study-area loader ([track_a_spatial/study_area.py](backend/src/oohscout/track_a_spatial/study_area.py))
- **F2** — IH-35 highway centerline loader ([track_a_spatial/corridor.py](backend/src/oohscout/track_a_spatial/corridor.py) — generic parameter form, commit `0c406dc`)
- **F4** — Data provenance sidecars + audit ([data/provenance.py](backend/src/oohscout/data/provenance.py), commit `07f7595` → merge `293a844`)

**In-flight on `feature/f5-test-bbox` (not yet committed):**
- **F5** — Test-bbox learning chapter scaffolded at [docs/learning/chapters/f5_test_bbox/](docs/learning/chapters/f5_test_bbox/) using the standard 5-file pattern (Milan original → explanation → OOHScout adaptation → explanation → code-along).
- **New production backend surface** landed under [backend/src/oohscout/](backend/src/oohscout/), matching V2's target layout:
  - [api/main.py](backend/src/oohscout/api/main.py), [api/auth.py](backend/src/oohscout/api/auth.py) (sidecar token), [api/errors.py](backend/src/oohscout/api/errors.py) (global handler + `sanitize_error`)
  - [mcp/](backend/src/oohscout/mcp/) — MCP tool server (`add_billboard_candidate`, `read_local_file`, `run_custom_analytics`) + `workspace.py` sandbox (`resolve_path`, `assert_safe_extension`)
  - [authoring.py](backend/src/oohscout/authoring.py) — `save_candidate`, `save_corridor`, `execute_agent_sql` (single-file per V2 §A1; split only past ~500 lines)
  - [security.py](backend/src/oohscout/security.py) — `assert_public_url`, `check_sql_safety`, `sanitize_error`
  - [project.py](backend/src/oohscout/project.py) — Pydantic `Candidate`, `Corridor`, `RegulatoryStatus` enum with `field_validator` blocking "LEGAL" at the schema boundary
  - [skills/SKILL.md](backend/src/oohscout/skills/SKILL.md) — Claude-Desktop-ready SKILL for the OOHScout agent
- [docs/PRODUCTION_ARCHITECTURE_V2.md](docs/PRODUCTION_ARCHITECTURE_V2.md) — the GeoLibre-verified architecture reference (authoritative).
- `pyproject.toml` / `uv.lock` — FastAPI + MCP dependencies added.

**Agent sequencing decision (2026-08-29):** After F7, an experimental Track-A-only Scout shell may expose existing signs, POIs, AADT, and unverified scouting points. It must label all points `REVIEW`, must not integrate Track B, and does not count as F37/F39 completion. The full ReAct agent still integrates Track A + Track B only in Phase 4.

**Data priority for OOHScout (focus on these):**
- RIGHT NOW: osm_pois_manhattan.geojson, osm_landuse_hungary.geojson (technique = advertiser demand + zoning)
- LATER: lidar_ndsm_crop.tif, sentinel_edi_clear_5ch.tif (visibility/obstruction)
- SKIP: cloudy scenes, time-series, Dutch aerial, SAM files (not relevant to billboard siting)

**First technical milestone:** Given a corridor, the system automatically eliminates obviously unsuitable parcels and produces 5-20 candidates an experienced billboard operator agrees are worth investigating.

**First commercial milestone:** An operator pays for a second corridor analysis.
