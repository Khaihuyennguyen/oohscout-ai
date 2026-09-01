# OOHScout AI — Production Architecture (GeoLibre-informed)

**Purpose:** turn the current notebook-and-scripts prototype into a real production application with RAG, AI agents, and multiple front doors (notebook widget, CLI, MCP server, hosted web) — modeled on the patterns GeoLibre has already proven at production scale.

**Reading order:** this doc, then `docs/FEATURES.md` (which stays the feature-level plan). This adds the *how the code is organized and shipped* layer that FEATURES.md doesn't cover.

**Status of the GeoLibre read:** I read the top-level structure, all seven `packages/*`, the `apps/geolibre-desktop/` layout, both FastAPI backends (sidecar + share/store), the Python widget package (`python/src/geolibre/` — 15 modules, ~14,700 lines), the MCP server (1,084 lines), the Cloudflare Worker AI proxy (679 lines), `docker-compose.yml`, root `Dockerfile`, `nginx.conf`, all key architecture docs (`architecture.md`, `mcp.md`, `python.md`, `agent-skill.md`, root `CLAUDE.md`), the `skills/geolibre/` distribution, and the 24-workflow `.github/workflows/`. I read the whole assistant folder (`agent.ts`, `tools.ts`, `provider.ts`) end-to-end. I did **not** read every line of every file in `packages/*/src/` or every test — I read package.json + index.ts and 3–5 sample modules per package. That was enough to see the pattern; deeper reads happen when a specific piece is being ported.

---

## Part 1 — The five GeoLibre production patterns you don't have yet

These are the non-negotiables. Every one is a *specific* architectural choice GeoLibre made that OOHScout's current scaffolding will hit as a problem within the next 30 days.

### 1.1 The three-layer authoring stack — the biggest missing piece

**GeoLibre's Python package** (`python/src/geolibre/`) has this exact layering. Read it in this order:

- **`project.py` (1,312 lines)** — pure functions that *build* pieces: `build_geojson_layer(...)`, `build_raster_layer(...)`, `build_legend(...)`. No I/O, no widget, no MCP, no LLM.
- **`authoring.py` (1,119 lines)** — pure functions that *apply* pieces to a whole project dict: `add_layer(project, layer)`, `restyle_layer(project, layer_id, ...)`, `move_camera(project, ...)`. Reads and writes `.geolibre.json` files. No widget.
- **`geolibre.py` (3,071 lines)** — the `Map` class (Jupyter widget). Delegates every write to `authoring.py`.
- **`mcp/server.py` (1,084 lines)** — the MCP server. Delegates every write to `authoring.py`.

The invariant this creates: **the notebook widget and the MCP server cannot drift apart**, because they call the same `authoring.py` functions. If a new tool is added to `authoring.py`, it appears in both places. If a bug is fixed there, it's fixed in both places. From the GeoLibre README verbatim: *"nothing here duplicates: `project.py` builds pieces, `authoring.py` applies them to a whole project, and both `Map` and the MCP tools delegate to `authoring.py`."*

**What OOHScout has today**: `track_a_spatial/study_area.py` and `corridor.py` — each is doing its own I/O, caching, and file writing. There's no shared `authoring.py`. There's no shared `project.py` for the concept of a "scouting project."

**What to add — concrete file plan:**

```
backend/src/oohscout/
├── authoring/                  # ← NEW. The layer everything shares.
│   ├── __init__.py
│   ├── project.py              # build_corridor(), build_candidate(), build_rule_binding()
│   ├── operations.py           # add_candidate(project), rerank(project), apply_rule_gate(project, rule_id)
│   ├── io.py                   # load_project(path), save_project(path, project) — with the schema-marker guard
│   └── schema.py               # OohscoutProject TypedDict; PROJECT_MARKERS = ("corridor_id", "oohscout_version")
```

Every downstream surface — notebook widget, CLI, FastAPI, MCP — imports from `authoring/`. **Nothing else imports data-mutating logic.** This is the rule.

### 1.2 The project file format — the on-disk contract

GeoLibre defines `.geolibre.json` as the *portable, forever* representation of a map. A project written by the notebook widget opens in the desktop app, in the MCP server, and in the web app. Every version of GeoLibre has to be able to read every version of that file.

**OOHScout equivalent — `.oohscout.json`** (name it now, freeze the shape at 0.1.0):

```json
{
  "oohscout_version": "0.1.0",
  "corridor_id": "ih-35-mclennan-2026-08",
  "created_at": "2026-08-30T14:22:00Z",
  "corridor": {
    "name": "IH-35 Hillsboro → Waco",
    "highway": "IH-35",
    "county": "McLennan",
    "state": "TX",
    "bbox": [-97.25, 31.40, -96.95, 31.80],
    "centerline_source": "osm://relation/12345 @ 2026-08-29",
    "buffer_m": 500
  },
  "rule_bindings": [
    {"jurisdiction": "TX-TXDOT", "rule_set_id": "43-tac-ch-21@2026-08-15", "status": "verified"},
    {"jurisdiction": "Waco",     "rule_set_id": "waco-sign-ord@2026-08-15", "status": "review"}
  ],
  "candidates": [
    {
      "id": "cand-0001",
      "geom": {"type":"Point","coordinates":[-97.10, 31.50]},
      "parcel_id": "mclennan/12345",
      "eligibility": {"status":"PASS","checked_at":"...","evidence_ids":["ev-0001","ev-0007"]},
      "score": {"total": 0.78, "factors": {"traffic":0.9,"visibility":0.7,"demand":0.6,"gap":0.8,"parcel":0.9,"econ":0.5}}
    }
  ],
  "score_config": {"weights": {"traffic":0.30,"visibility":0.20,"demand":0.15,"gap":0.15,"parcel":0.10,"econ":0.10}, "version": "v1"},
  "output": {"ranking_csv_path": "outputs/ih-35-ranking.csv", "packet_pdf_path": null}
}
```

Two rules borrowed verbatim from GeoLibre's MCP server:

1. **PROJECT_MARKERS check.** Refuse to overwrite a JSON file unless it has both `oohscout_version` AND `corridor_id`. Copy the pattern from [`mcp/server.py:79-98`](../references/GeoLibre/python/src/geolibre/mcp/server.py). Prevents an agent from being tricked into writing a scouting report over `package.json`.

2. **Credential redaction on serialize.** GeoLibre's `to_project(keep_credentials=False)` strips API keys, tokens, auth headers, geocoder keys, and credential URL parameters before serializing. OOHScout must do the same for TxDOT keys, Regrid API keys, Groq/Anthropic keys, county-portal credentials.

### 1.3 Optional-extras pattern — do not force every user to install torch

GeoLibre's `backend/geolibre_server/pyproject.toml` has: `[dev]`, `[whitebox]`, `[conversion]`, `[vector]`, `[raster]`, `[postgis]`, `[sedona]`, `[ml]`, `[notebook]`, `[test]`. A user installing to *just look at a map* pulls none of them. A user running the SAM3 segmentation server pulls `[ml]`. The wheel installs cleanly on any machine — the heavy geodeps only download when opted into.

**OOHScout's current `pyproject.toml`** installs `torch`, `torchvision`, `open-clip-torch`, `segment-geospatial`, `earthengine-api`, `geotessera`, `anthropic`, `groq`, `psycopg[binary]`, `pgvector`, `pandana`, `libpysal`, `esda`, `spreg` **all as hard dependencies**. That's ~5 GB and 40 min of install on a fresh machine. **A prospect trying it will bounce.**

**Refactor pyproject.toml into extras:**

```toml
[project]
dependencies = [
    # The lean core: what "hello world" needs
    "geopandas", "shapely", "pyproj", "pandas", "numpy", "pyyaml", "pydantic",
]

[project.optional-dependencies]
notebook  = ["jupyterlab", "ipykernel", "ipywidgets", "python-dotenv", "folium", "matplotlib", "contextily"]
osm       = ["osmnx"]
network   = ["pandana"]                                     # UA Ch 3
spatial-stats = ["libpysal", "esda", "spreg", "statsmodels", "mapclassify"]  # UA Ch 6
raster    = ["rasterio", "pystac-client"]
ml        = ["torch", "torchvision", "torchinfo", "open-clip-torch", "scikit-image", "scikit-learn", "opencv-python", "pillow"]
sam       = ["segment-geospatial", "huggingface-hub"]
db        = ["psycopg[binary]", "pgvector"]
rag       = ["anthropic"]                                   # Track B
agent     = ["groq", "anthropic"]                           # Track C
mcp       = ["mcp>=2.0"]                                    # OOHScout MCP server
ee        = ["earthengine-api", "geotessera"]               # optional overlays
dev       = ["pytest", "pytest-cov", "ruff", "mypy"]
test      = ["oohscout-ai[dev,notebook,osm,network,spatial-stats,raster,db,rag,agent,mcp]"]
all       = ["oohscout-ai[notebook,osm,network,spatial-stats,raster,ml,sam,db,rag,agent,mcp,ee]"]
```

**Rule from GeoLibre** (verbatim from their `pyproject.toml`): *"Everything required to run the FULL backend test suite. Without these extras the vector/raster/SQL/ML tests skip themselves (via skipif/importorskip), so a `[dev]`-only install reports a misleadingly green, near-empty run."* — copy the `[test]` extras discipline. It's the difference between real coverage and green-but-hollow.

### 1.4 The FastAPI sidecar — actually build it, and copy the security posture

GeoLibre's `backend/geolibre_server/geolibre_server/app/` has 7 routers (`whitebox.py`, `conversion.py`, `raster.py`, `vector.py`, `postgis.py`, `sql.py`, `ml.py`) plus `main.py` (203 lines that are almost entirely security posture).

**Read those 203 lines.** They set the model for a production Python service that an untrusted AI agent will call:

- **Token auth middleware** ([main.py:44-84](../references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L44-L84)) — every request must carry `X-GeoLibre-Token` or `Authorization: Bearer <token>`. Constant-time compare on **bytes** (to avoid Starlette's latin-1 decode raising `TypeError`, which would turn 401 into 500). Exempt `/health` and `OPTIONS` preflight. The token is generated fresh on every launch by the parent process and injected via env var.
- **TrustedHostMiddleware** ([main.py:94-97](../references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L94-L97)) — only `localhost`, `127.0.0.1`, `testserver`. Blocks DNS rebinding. Note their explicit comment about IPv6 loopback needing special handling.
- **CORS regex, not wildcard** ([main.py:101-110](../references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L101-L110)) — `r"^(http://localhost:5173|http://127\.0\.0\.1:5173|tauri://localhost|http://tauri\.localhost)$"`. A random local web app cannot hit the sidecar from a browser.
- **Graceful shutdown that works on Windows** ([main.py:140-148](../references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L140-L148)) — raises `SIGINT` not `SIGTERM` because Windows maps SIGTERM to uncatchable `TerminateProcess`.

**And their PostGIS router** ([postgis.py](../references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py)) has three specific patterns you need:
- Identifier quoting with `psycopg.sql.Identifier` for every schema/table/column name resolved against the DB catalogs
- 60-second statement timeout on every session (`_STATEMENT_TIMEOUT_MS = 60_000`) so a bad LLM-generated query cannot pin a FastAPI worker
- Regex-based password redaction in error messages (`_PASSWORD_URL_RE`, `_PASSWORD_KV_RE`) so a malformed connection string can't leak back to the caller
- Host allowlist via `GEOLIBRE_POSTGIS_HOSTS` env var; without it the sidecar refuses external hosts

**What OOHScout needs — file plan:**

```
backend/src/oohscout/
├── api/                          # ← Currently empty. Build this next.
│   ├── __init__.py
│   ├── main.py                   # FastAPI app + the exact main.py security posture above
│   ├── routers/
│   │   ├── corridor.py           # /corridor/{id}/rank, /corridor/{id}/status
│   │   ├── rules.py              # /rules/check?jurisdiction=&sign_type=&…
│   │   ├── rag.py                # /rag/query?q=  → {answer, citations[], confidence}
│   │   ├── enrich.py             # /enrich/parcel/{id}, /enrich/aadt/{lat,lng}
│   │   ├── candidate.py          # /candidate/{id}/score, /candidate/{id}/explain
│   │   └── packet.py             # /packet/generate?corridor_id= → PDF/HTML url
│   ├── deps.py                   # PostgresPool, PgvectorClient, TxDOTClient, RulesEngine — injected
│   ├── auth.py                   # token middleware (mirror geolibre_server/app/main.py)
│   └── errors.py                 # ValueError → HTTPException translator (analogue of _reports_its_errors)
```

**Rule:** every router imports only from `authoring/`, `data/`, and `deps.py` — never directly from `track_a_spatial/`, `track_b_rag/`, or `track_c_agent/`. Those are the *implementation* layer; the routers are the *API* layer.

### 1.5 The second front door: an MCP server, shipped as a wheel

GeoLibre's `python/src/geolibre/mcp/` has 4 files: `__init__.py` (64 lines that gracefully report the missing extra), `__main__.py` (8 lines — the `python -m geolibre.mcp` entrypoint), `server.py` (1,084 lines), `workspace.py` (141 lines — the path-confinement sandbox).

The `pyproject.toml` registers `geolibre-mcp = "geolibre.mcp:main"` as a console script. A user runs `pip install "geolibre[mcp]"` then `geolibre-mcp --root ~/maps`. Claude Desktop / Cursor / Claude Code point at it via `mcpServers` config, and now those agents can author `.geolibre.json` files.

**This is the single fastest OOHScout distribution mechanism.** Operators who use Claude Desktop for research already exist. `pip install oohscout-ai[mcp]` + `oohscout-mcp --root ~/scouting`, then they ask Claude: *"Score IH-35 through McLennan County for a 14x48 static bulletin. Return the top 10 candidates as a report."* Zero-UI, zero-frontend product-market fit signal.

**Six patterns to copy verbatim from `geolibre/mcp/server.py`:**

1. **`_reports_its_errors` wrapper** ([server.py:159-206](../references/GeoLibre/python/src/geolibre/mcp/server.py#L159-L206)) — MCP swallows exception messages by default; wrap every tool so `ValueError` → `ToolError` with the original message. Without this, agents cannot self-correct because they see *"Error executing tool X"* instead of *"add_ogc_layer requires a non-empty layers parameter."*

2. **`_require_project` schema marker check** ([server.py:82-98](../references/GeoLibre/python/src/geolibre/mcp/server.py#L82-L98)) — refuse to rewrite a JSON file that isn't a real project.

3. **`INSTRUCTIONS` string at the top** ([server.py:34-68](../references/GeoLibre/python/src/geolibre/mcp/server.py#L34-L68)) — an MCP server's `instructions` field is the equivalent of a chat agent's system prompt. It tells the *calling* LLM when to prefer these tools over hand-written code. For OOHScout: *"Use these tools whenever someone asks to evaluate, score, or shortlist billboard locations along a highway corridor. Reach for them before writing hand-rolled parcel-scoring code..."*

4. **`workspace.py` path confinement** ([workspace.py](../references/GeoLibre/python/src/geolibre/mcp/workspace.py)) — every path in every tool call resolves against `--root` allowlist. Symlinks that escape are refused. Copy the whole file, rename `Workspace` to `ScoutingWorkspace`, done.

5. **Async guard on the wrapper** — GeoLibre's `_reports_its_errors` refuses `async def` tools because the ValueError would fire after the try-block exits. All tools synchronous, or the wrapper explicitly handles both branches.

6. **Optional-import graceful failure** ([mcp/__init__.py](../references/GeoLibre/python/src/geolibre/mcp/__init__.py)) — `mcp[mcp]` is an extra, so `mcp/__init__.py` catches the `ImportError` and prints an actionable *"install with `pip install oohscout-ai[mcp]`"* message, not a stack trace.

---

## Part 2 — The updated OOHScout production folder layout

This is the target. Every folder maps to a specific GeoLibre pattern.

```
billboardAI/
├── CLAUDE.md                           # (exists — keep)
├── docs/                               # (exists — keep + expand)
│   ├── PRODUCTION_ARCHITECTURE.md      # ← THIS FILE (new)
│   ├── FEATURES.md                     # (exists — keep, add "Section 1.x" refs)
│   ├── PRD.md, MASTER_PLAN.md          # (exist)
│   ├── project-format.md               # NEW — the .oohscout.json schema, mirrors GeoLibre's project-format.md
│   ├── mcp.md                          # NEW — how to install/configure oohscout-mcp
│   ├── agent-skill.md                  # NEW — the SKILL.md distribution story
│   ├── architecture.md                 # NEW — hand-drawn mermaid + prose of the three-layer stack
│   └── learning/…                      # (exists — keep)
├── backend/
│   ├── pyproject.toml                  # REFACTOR — split hard deps into [notebook,osm,network,…]
│   ├── src/oohscout/
│   │   ├── __init__.py                 # (exists)
│   │   ├── authoring/                  # ← NEW. THE shared layer.
│   │   │   ├── project.py              # build_corridor, build_candidate, build_rule_binding
│   │   │   ├── operations.py           # add_candidate, apply_rule_gate, rerank
│   │   │   ├── io.py                   # load_project, save_project (with PROJECT_MARKERS)
│   │   │   ├── schema.py               # OohscoutProject TypedDict, redact_credentials
│   │   │   └── security.py             # assert_public_http_url, is_read_only_sql, read_capped
│   │   ├── track_a_spatial/            # (exists — keep, purely spatial functions)
│   │   │   ├── study_area.py           # ✅
│   │   │   ├── corridor.py             # ✅
│   │   │   ├── candidates.py           # F6, F7 — buffer + interpolate
│   │   │   ├── spacing.py              # F8 — LRS spacing engine
│   │   │   ├── demand.py               # F10-F15 — POI clustering
│   │   │   ├── accessibility.py        # F16-F17 — Pandana isochrones
│   │   │   ├── zoning.py               # F19-F22
│   │   │   ├── visibility.py           # F23-F24 — LiDAR nDSM
│   │   │   └── scoring.py              # F25-F27
│   │   ├── track_b_rag/                # (exists — empty; build this)
│   │   │   ├── corpus.py               # F31 — regulatory PDFs + provenance
│   │   │   ├── chunk.py                # F32 — section-metadata-preserving chunker
│   │   │   ├── embed.py                # F33 — Claude embeddings, pgvector store
│   │   │   ├── retrieve.py             # F34 — hybrid BM25 + vector + reranker; enforce citation
│   │   │   ├── extract.py              # F35 — LLM → structured rule JSON
│   │   │   └── review.py               # F36 — draft/reviewed/verified state machine
│   │   ├── track_c_agent/              # (exists — empty; build this)
│   │   │   ├── session.py              # AssistantSession class (mirror geolibre agent.ts:171-line shape)
│   │   │   ├── grounding.py            # describe_corridor(), lastContext dedupe
│   │   │   ├── system_prompt.py        # ONE constant. The rulebook.
│   │   │   ├── tools/
│   │   │   │   ├── __init__.py         # create_scouting_tools(deps)
│   │   │   │   ├── deps.py             # ToolDeps: db, txdot, rules, rag, approve
│   │   │   │   ├── corridor.py         # list_corridors, describe_corridor, load_corridor
│   │   │   │   ├── query.py            # run_postgis (read-only)
│   │   │   │   ├── rules.py            # check_regulatory_eligibility (HARD GATE)
│   │   │   │   ├── scoring.py          # rank_candidates, explain_score
│   │   │   │   ├── enrichment.py       # get_txdot_permits, fetch_aadt, get_parcel_owner
│   │   │   │   └── packet.py           # generate_site_packet
│   │   │   └── providers.py            # groq | anthropic dynamic-import
│   │   ├── api/                        # (exists — empty; build this)
│   │   │   ├── main.py                 # FastAPI app + full security posture
│   │   │   ├── routers/{corridor,rules,rag,enrich,candidate,packet}.py
│   │   │   ├── deps.py                 # injected clients
│   │   │   ├── auth.py                 # token middleware
│   │   │   └── errors.py               # ValueError → HTTPException translator
│   │   ├── mcp/                        # ← NEW. Ship as oohscout-mcp console script.
│   │   │   ├── __init__.py             # Graceful ImportError message for missing extra
│   │   │   ├── __main__.py             # `python -m oohscout.mcp`
│   │   │   ├── server.py               # ALL tools; delegates to authoring/
│   │   │   ├── workspace.py            # Path confinement (--root, OOHSCOUT_MCP_ROOTS)
│   │   │   └── errors.py               # _reports_its_errors wrapper
│   │   ├── db/                         # (exists — empty; build this)
│   │   │   ├── pool.py                 # asyncpg pool, read-only role helper
│   │   │   ├── migrations/             # Alembic — one folder, one truth
│   │   │   ├── schema.sql              # jurisdictions, regulation_chunks, verified_rules, candidate_sites, site_scores…
│   │   │   ├── seed.py                 # load small fixtures for tests
│   │   │   └── read_role.sql           # CREATE ROLE oohscout_ro; …
│   │   └── data/                       # (exists — keep, expand)
│   │       ├── provenance.py           # ✅ F4
│   │       ├── txdot.py                # verified TxDOT client from earlier session
│   │       ├── osm.py                  # OSMnx wrapper with cache
│   │       └── parcels.py              # county/Regrid adapter
│   └── tests/                          # (exists — expand)
│       ├── authoring/                  # tests for the shared layer
│       ├── track_a/                    # (exists)
│       ├── track_b/                    # NEW — RAG tests with real citations
│       ├── track_c/                    # NEW — agent evals (golden cases)
│       ├── mcp/                        # NEW — MCP tool contract tests
│       └── api/                        # NEW — FastAPI integration tests
├── skills/                             # ← NEW. Mirrors GeoLibre's skills/.
│   └── oohscout/
│       ├── SKILL.md                    # Teaches Claude Code / Desktop how to use oohscout-mcp
│       └── references/{project-json.md, mcp-tools.md, rules-catalog.md}
├── frontend/                           # (exists as stub — build Phase 5+)
│   └── (Next.js + MapLibre GL app, only after Phase 6 payment signal)
├── workers/                            # NEW, IF you go hosted
│   └── ai-proxy/                       # Cloudflare Worker — hosted-key path for BYO-Claude users
├── docker/                             # NEW, IF you go hosted
│   ├── nginx.conf                      # same-origin /api /rag /sidecar routing
│   └── entrypoint.sh
├── docker-compose.yml                  # NEW — postgres + api + (optional) worker
├── Dockerfile                          # NEW — mirrors GeoLibre root Dockerfile
├── .github/workflows/                  # NEW — ci.yml (lint + typecheck + test + build) at minimum
├── notebooks/                          # (exists — keep)
├── references/GeoLibre/                # (exists — the study material)
└── graphify-out/                       # (auto)
```

---

## Part 3 — Updated 90-day roadmap (feature-numbers preserved, phasing updated)

The FEATURES.md list of 52 items stays. The phasing changes: **you cannot build the agent (F37-F41) without the shared authoring layer**, and you cannot ship the MCP without the FastAPI-style security posture in place. Reordered:

### Phase 2.5 — Infrastructure (INSERT before Phase 3) — days 31-37

The current plan jumps from Phase 2 (candidate engine) to Phase 3 (RAG). Insert a one-week infrastructure phase:

- **F-infra-1**: Refactor `pyproject.toml` into optional-extras (§1.3). *0.5 day.*
- **F-infra-2**: Create `authoring/` package with `project.py`, `operations.py`, `io.py`, `schema.py`, `security.py`. Migrate `study_area.py` and `corridor.py` to *use* it (they become thin wrappers). *2 days.*
- **F-infra-3**: Freeze `.oohscout.json` schema at v0.1.0. Write `docs/project-format.md`. *1 day.*
- **F-infra-4**: Set up PostgreSQL + PostGIS + pgvector locally via `docker-compose.yml`. Alembic migration for the tables in `project_oohscout_architecture.md` (jurisdictions, regulation_chunks, verified_rules, candidate_sites, site_scores). Create the read-only `oohscout_ro` role. *2 days.*
- **F-infra-5**: Basic CI at `.github/workflows/ci.yml`: lint (ruff), typecheck (mypy), pytest with the `[test]` extra. Coverage floor 40% (ratchet up over time). *1 day.*

**Rationale**: without this phase, Phase 3 (RAG) will build directly against ad-hoc code and every later phase pays the debt. GeoLibre paid this cost early — you can see it in the `authoring.py` / `project.py` split. Do the same.

### Phase 3 — Regulatory RAG (F31-F36) — days 38-52

Add these implementation notes to the existing plan:

- **F32 chunking discipline**: GeoLibre's `authoring.py` teaches that shared logic goes in one file. Same here: one chunker (`track_b_rag/chunk.py`) with subsection-header preservation, used by ingestion *and* re-chunking scripts, so a schema change updates both sides.
- **F34 citation-required chain**: Copy the pattern from GeoLibre's `run_sql` tool result — return `{answer, rule_type, jurisdiction, source_section, page_range, confidence, verification_status}`. Never `str`. The API contract makes downstream code (scoring, agent) type-safe.
- **F36 human review workflow**: A rule flows `draft → reviewed → verified`. `verified_rules` table has a `verification_status` column exactly as spec'd in `project_oohscout_data.md`. **Never let the agent use a `draft` rule as a hard gate.** Copy GeoLibre's `_require_project` pattern: gate function reads status, refuses to gate on `draft`.

### Phase 4 — Agentic workflow (F37-F41) — days 53-67

**Renamed from the old plan; this is where GeoLibre gives the most direct blueprint.**

Read `agent.ts` (171 lines) as prior art. Then build in this order:

1. **`track_c_agent/system_prompt.py`** — one constant. Encodes the rules from `CLAUDE.md`: regulatory gate first, PostGIS owns distances, never label "LEGAL", always call `check_regulatory_eligibility` before `rank_candidates`.
2. **`track_c_agent/tools/deps.py`** — `ToolDeps` dataclass. Injected. GeoLibre's `AssistantToolDeps` interface at [tools.ts:23-40](../references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L23-L40) is the template.
3. **`track_c_agent/tools/security.py`** — port `assert_public_http_url` and `is_read_only_sql` from GeoLibre's [tools.ts:117-167](../references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L117-L167).
4. **`track_c_agent/tools/rules.py::check_regulatory_eligibility`** — the HARD GATE. Returns `PASS | FAIL | REVIEW` plus evidence ids. **Read-only.**
5. **`track_c_agent/tools/scoring.py::rank_candidates`** — the RANK. Requires prior successful `check_regulatory_eligibility` call in the session (enforced via `deps.session.has_gated(corridor_id)`).
6. **`track_c_agent/grounding.py::describe_corridor`** — GeoLibre's `describeLayers` pattern at [tools.ts:237-257](../references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L237-L257). Only re-inject when it changes.
7. **`track_c_agent/session.py::AssistantSession`** — thin adapter over your chosen SDK (LangGraph or Strands or `anthropic` directly). Normalizes to `{type: text|tool_call|tool_result}` events for the UI. **Mirror the 171-line shape.**
8. **`track_c_agent/tools/query.py::run_postgis`** — read-only. Under `oohscout_ro` role. Statement timeout 60s (mirror GeoLibre's `_STATEMENT_TIMEOUT_MS`).

### Phase 4.5 — MCP server + Agent Skill (INSERT before Phase 5) — days 68-74

**This is the fastest distribution mechanism you have** (§1.5). One week.

- **F-mcp-1**: Build `backend/src/oohscout/mcp/` mirroring GeoLibre's `python/src/geolibre/mcp/` file-for-file. Every tool delegates to `authoring/`. *3 days.*
- **F-mcp-2**: Add `oohscout-mcp` to `pyproject.toml` `[project.scripts]`. Test `pip install oohscout-ai[mcp] && oohscout-mcp --root ~/scouting` end-to-end. *0.5 day.*
- **F-mcp-3**: Write `skills/oohscout/SKILL.md` mirroring GeoLibre's `skills/geolibre/SKILL.md` structure. Include the *"Rules that actually bite"* section — jurisdiction naming, when to prefer `check_regulatory_eligibility` first, why the score is a proposal not a verdict. *1 day.*
- **F-mcp-4**: Post to a small OOH-industry Slack/subreddit: *"Free tool: score a highway corridor for billboard candidates from Claude Desktop. `pip install oohscout-ai[mcp]`."* First payment signal test. *0.5 day.*

### Phase 5 — Web app (F44-F45) — only after Phase 4.5 payment signal

Deferred. The MCP + notebook widget cover 80% of the value at 20% of the effort. Only build the Next.js + MapLibre frontend if a paying customer says *"I want a browser dashboard."*

If you do build it, mirror GeoLibre's structure: `apps/oohscout-desktop/src/` with `lib/`, `hooks/`, `components/`, and (critically) a Zustand store as the single source of truth. Every AI-tool result flows through the store; the map subscribes to the store; no direct MapLibre mutations from UI code. Copy [`architecture.md`](../references/GeoLibre/docs/architecture.md) §1-3 verbatim if needed.

---

## Part 4 — The specific decisions that need making NOW

These aren't in FEATURES.md yet but they'll block work within 30 days.

### 4.1 LLM provider choice for the MVP
- **Recommendation**: Anthropic Claude Opus 4.7 for the agent + reasoning; a lighter model (Haiku 4.5 or Groq's Llama) for the RAG rerank step.
- **Reason**: OOHScout's whole reason for existence is being *right* about regulations. Cost-per-query is dominated by human review time saved, not by tokens. Optimize for accuracy first.
- **Do not**: build the multi-provider abstraction yet (GeoLibre's `provider.ts` is 623 lines because they support 6 providers for user choice — OOHScout is single-tenant reasoning, one provider is fine).

### 4.2 Agent SDK choice
- **Options**: LangGraph (originally planned in `project_oohscout_architecture.md`) · Anthropic Agent SDK / Managed Agents · Strands (what GeoLibre uses) · raw `anthropic` SDK with hand-rolled tool loop.
- **Recommendation**: **raw `anthropic` SDK with hand-rolled tool loop for MVP.** ~200 lines. Full control. No framework migrations. GeoLibre's `agent.ts` is 171 lines because the SDK does the loop for them — the raw `anthropic` SDK does the same via `tool_use` blocks in 30 more lines.
- Switch to LangGraph *only* when you need parallel tool execution + state persistence across turns AND the raw approach shows friction. Not before.

### 4.3 RAG stack
- **Recommendation**: Anthropic embeddings + pgvector + BM25 (Postgres `tsvector`) hybrid, with a Claude-based reranker of the top 20 hits.
- Why not FAISS/Chroma/Weaviate: you already have Postgres for scoring data. One data store, one operational surface. GeoLibre uses PostGIS + pgvector similarly — a single Postgres for spatial + vector + relational is the cleanest ops posture.

### 4.4 Deployment target
- **Recommendation, months 0-3**: local-first. `pip install oohscout-ai[all]` + `docker-compose up` starts Postgres. Ship the MCP server. **Zero cloud costs.**
- **Recommendation, months 3-6 if payment signal**: single Hetzner / Fly.io box for the hosted FastAPI + Postgres. Cloudflare Worker AI proxy only if BYO-key hosted users appear.
- **Do not**: build the Cloudflare Worker AI proxy in MVP. GeoLibre needed it because their app runs in a browser — yours runs in Claude Desktop / a notebook / a local FastAPI. No CORS problem.

### 4.5 Testing discipline
- **Copy GeoLibre's `[test]` extras rule** verbatim: `[test]` must install *every* optional extra so `pytest` sees a real coverage number, not a hollow green.
- **Add golden-case evaluation harness (F41) EARLY, not late.** 15 fixed queries with expected tool sequences, run on every PR. This is how you catch agent regressions.
- **e2e test for the MCP server**: spawn `oohscout-mcp` as a subprocess, send it a `create_project` + `check_regulatory_eligibility` + `rank_candidates` sequence, assert the resulting `.oohscout.json` matches a snapshot. Copy the e2e pattern from `references/GeoLibre/e2e/`.

---

## Part 5 — What to delete, what to leave alone

**Leave alone (already good):**
- `docs/FEATURES.md` — the feature list itself is excellent. Just add references to the new folder structure.
- `backend/src/oohscout/track_a_spatial/study_area.py` and `corridor.py` — the code is fine, just needs to *use* `authoring/` once that exists.
- `backend/src/oohscout/data/provenance.py` — F4 done well, keep.
- The notebooks in `backend/notebooks/` — those are learning artifacts, don't touch.
- Every memory file in `c:\Users\nguye\.claude\projects\c--Users-nguye-Documents-billboardAI\memory\`.

**Rewrite:**
- `backend/pyproject.toml` — split into optional-extras.

**Add (in this order):**
1. `docs/PRODUCTION_ARCHITECTURE.md` ← THIS FILE
2. `docs/project-format.md`
3. `backend/src/oohscout/authoring/` (5 files)
4. `docker-compose.yml` + Postgres migration
5. `.github/workflows/ci.yml`
6. `backend/src/oohscout/api/` scaffolding
7. `backend/src/oohscout/track_b_rag/` scaffolding
8. `backend/src/oohscout/track_c_agent/` scaffolding
9. `backend/src/oohscout/mcp/`
10. `skills/oohscout/SKILL.md`

**Deferred (do not build in MVP):**
- `workers/` (Cloudflare) — only if hosted BYO-key users appear
- `frontend/` (Next.js) — only if a paying customer asks for a browser dashboard
- Multi-LLM provider abstraction — one provider is fine
- `run_python` / `run_maplibre_js` escape hatches — OOHScout is a decision product, not an exploration tool

---

## Part 6 — The single biggest lesson from reading GeoLibre

**The `authoring.py` layer is the moat.** It's what lets GeoLibre ship the same product as three completely different applications (Jupyter widget, Tauri desktop, MCP server) without any of them drifting. It's what lets an agent, a human user, and an automated script all produce byte-identical projects.

OOHScout has **the same distribution multiplicity coming**: notebook prototyping (now), CLI (soon), FastAPI (Phase 3), MCP server (Phase 4.5), maybe web (Phase 5+). Without a shared `authoring/` layer, you will re-implement rule-gating in every one of those, and they will drift. When a jurisdiction rule changes, you'll fix it in the MCP but forget the API. When a scoring weight tunes, the notebook and the API will disagree.

**Build `authoring/` first, before any of the surfaces that depend on it.** Everything else in this document is downstream of that one decision.

---

## Appendix — Direct file-to-file mapping (GeoLibre → OOHScout)

| GeoLibre file | Lines | OOHScout equivalent | Priority |
|---|---|---|---|
| `python/src/geolibre/project.py` | 1312 | `backend/src/oohscout/authoring/project.py` | P0 |
| `python/src/geolibre/authoring.py` | 1119 | `backend/src/oohscout/authoring/operations.py` | P0 |
| `python/src/geolibre/mcp/server.py` | 1084 | `backend/src/oohscout/mcp/server.py` | P1 |
| `python/src/geolibre/mcp/workspace.py` | 141 | `backend/src/oohscout/mcp/workspace.py` | P1 |
| `python/src/geolibre/mcp/__init__.py` | 64 | `backend/src/oohscout/mcp/__init__.py` | P1 |
| `backend/geolibre_server/app/main.py` | 203 | `backend/src/oohscout/api/main.py` | P1 |
| `backend/geolibre_server/app/postgis.py` | 962 | `backend/src/oohscout/api/routers/rag.py` + `api/deps.py` (pool patterns only) | P1 |
| `apps/geolibre-desktop/src/lib/assistant/agent.ts` | 171 | `backend/src/oohscout/track_c_agent/session.py` | P1 |
| `apps/geolibre-desktop/src/lib/assistant/tools.ts` | 1080 | `backend/src/oohscout/track_c_agent/tools/*.py` (10 tools split by concern) | P1 |
| `apps/geolibre-desktop/src/lib/assistant/provider.ts` | 623 | `backend/src/oohscout/track_c_agent/providers.py` (~80 lines — single provider) | P2 |
| `workers/ai-proxy/src/index.ts` | 679 | `workers/ai-proxy/src/index.ts` — deferred to hosted phase | P3 |
| `skills/geolibre/SKILL.md` | ~200 | `skills/oohscout/SKILL.md` | P1 |
| `docker-compose.yml` | 90 | `docker-compose.yml` | P1 |
| `.github/workflows/ci.yml` | (varies) | `.github/workflows/ci.yml` | P1 |
| `pyproject.toml` optional-extras block | 40 lines | `backend/pyproject.toml` extras rewrite | P0 |

**P0 = do first, blocks everything else.**
**P1 = do next, blocks MVP.**
**P2 = do when MVP is validated.**
**P3 = do only if hosted phase is reached.**
