# OOHScout Backend

Python code + Jupyter notebooks for OOHScout AI.

## Layout

- `src/oohscout/` — installable package
  - `data/` — ingestion clients (TxDOT, OSM, Sentinel, MCAD)
  - `track_a_spatial/` — Track A GIS engine
  - `track_b_rag/` — Track B regulatory RAG
  - `track_c_agent/` — Track C ReAct agent
  - `db/` — PostGIS + pgvector helpers
  - `api/` — FastAPI (Phase 5+)
- `tests/` — pytest suite mirroring `src/`
- `notebooks/` — chapter adaptations + prototyping
- `data/` — cached artifacts (gitignored)
- `scripts/` — utility scripts

## Run notebooks
```bash
uv run jupyter lab backend/notebooks/
```

## Run tests
```bash
uv run pytest backend/tests/
```

## Environment
Python 3.11, managed via `uv` (see root `pyproject.toml`).
