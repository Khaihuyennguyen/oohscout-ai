# OOHScout Global Context & Rules

You are an AI assistant helping to build OOHScout, an enterprise-grade geospatial AI platform for billboard site selection in Texas.

## 1. Project Architecture (The Secure Middleware)
The foundational plumbing is already built inside `backend/src/oohscout/`. It relies on three strict pillars:
* **The Data Layer (`project.py`, `authoring.py`):** Uses Pydantic for strict schemas and `psycopg3` (async) for parameterized PostgreSQL writes.
* **The API Layer (`api/`):** A FastAPI server managing an async database connection pool. It uses HMAC to verify `X-API-Token` headers and scrubs database passwords from 500 crash logs.
* **The MCP Layer (`mcp/`):** Uses `mcp` 2.x (`MCPServer`) to expose our secure Python functions as tools to the AI. It features a strict Read-Only Sandbox (`workspace.py`) that uses `pathlib.Path.resolve()` to block path traversal.

## 2. Strict Engineering Directives (Do Not Violate)
* **Dependency Management:** We use `uv` exclusively. Do not recommend `pip install`. Look at `pyproject.toml` for optional dependency groups (e.g., `[vector]`, `[postgis]`).
* **The "LEGAL" Ban:** You must never assign or suggest assigning a `regulatory_status` of `"LEGAL"`. This is a strict liability issue. The only acceptable statuses are `PASS`, `FAIL`, or `REVIEW`.
* **Read-Only Sandbox:** The database is the single source of truth. The AI is mathematically restricted from writing, modifying, or saving local files in the `data/` directory.

## 3. Current Focus (Domain Engineering)
We are currently focusing on:
* **Track A (Spatial Engine):** Using GeoPandas, Shapely, and PostGIS to measure 500-foot radial setbacks from highways.
* **Track B (Legal RAG):** Using `pgvector` and HuggingFace embeddings to chunk and search 400-page zoning PDFs.

When asked to write code, always adhere to these architectural rules and ensure any new database queries strictly use parameterized bindings.
