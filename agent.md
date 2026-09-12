# OOHScout Global Context & Rules

You are an AI assistant helping to build OOHScout, an AI-assisted geospatial development desk for billboard site selection in Texas.

## 1. Project Architecture (Target Shape)

The authoritative architecture is [docs/PRODUCTION_ARCHITECTURE_V2.md](docs/PRODUCTION_ARCHITECTURE_V2.md). Read it before making architecture decisions. The current tree under `backend/src/oohscout/` matches V2's target shape but is **scaffolded, not production-verified**. Ground truth for what is actually shipped is `git log main` + a ✅ in [docs/FEATURES.md](docs/FEATURES.md).

Three-layer authoring stack (V2 §A1):
* **Data layer (`project.py`, `authoring.py`):** Pydantic schemas for `Candidate` / `Corridor` / `RegulatoryStatus`; sync `psycopg` with parameterized writes. **Per-request connections** for MVP — no async pool yet (V2 §A5).
* **API layer (`api/`):** FastAPI sidecar. Sidecar-token auth via `hmac.compare_digest` on the `X-OOHScout-Token` header (or `Authorization: Bearer …`). Global exception handler scrubs DB passwords from error messages via `sanitize_error()`.
* **MCP layer (`mcp/`):** `mcp` SDK exposes secure Python functions as tools. Read-only sandbox in `workspace.py` uses `pathlib.Path.resolve()` **before** the containment check to catch symlink escapes; extension allowlist for writes.

## 2. Strict Engineering Directives (Do Not Violate)

* **Dependency Management:** We use `uv` exclusively. Do not recommend `pip install`. `pyproject.toml` uses optional-extras (V2 §A3): `api`, `notebook`, `vector`, `raster`, `science`, `ml`, `postgis`, `agent`. `all` includes everything; `test = ["oohscout-ai[all]"]` so tests never lie by silently skipping.
* **The "LEGAL" Ban:** Never assign or suggest a `regulatory_status` of `"LEGAL"`. This is a strict liability issue. The only acceptable statuses are `PASS`, `FAIL`, or `REVIEW`. The `field_validator` on `RegulatoryStatus` in `project.py` enforces this at the schema boundary.
* **Read-Only Sandbox:** The database is the single source of truth for candidate data. Agent tools mathematically cannot write files inside the workspace root except to the allowlisted extensions (`.json`, `.oohscout.json`).
* **SQL confinement:** Every LLM-supplied SQL must pass `check_sql_safety()` — SELECT/WITH only, rejects INSERT/UPDATE/DELETE/DDL/session-mutations, including inside CTEs and after masking string literals + comments. Enforced by `backend/tests/test_security.py` (28 tests).

## 3. Current Focus (Where Work Is Actually Happening)

* **Track A (Spatial Engine — in progress):** F1 study area, F2 highway centerline, F3 ingestion, F4 provenance sidecars, F5 DEV_MODE bbox and F6 corridor buffer all shipped to `main`. **Next: F7 candidate sampling.** Legal setbacks in the domain are tiered per **43 TAC Chapter 21** (do NOT quote a flat "500 ft" — that figure is the geosign-ai legacy that CLAUDE.md flags as wrong).
* **Track B (Regulatory RAG — not started):** Planned for Phase 3. `pgvector` + citation-required retrieval on county zoning PDFs. 0 / 6 features built.
* **Track C (Agent — not started):** Planned for Phase 4. ReAct loop wrapping Track A + Track B as tools. `backend/src/oohscout/track_c_agent/` currently contains only `__init__.py`.

When asked to write code, always adhere to these architectural rules and ensure any new database queries strictly use parameterized bindings.
