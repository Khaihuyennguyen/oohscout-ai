# OOHScout AI

**AI-assisted OOH (out-of-home advertising) development desk.** Turns fragmented regulations, geospatial data, traffic, parcels, and market signals into a ranked billboard-acquisition pipeline — one highway corridor at a time.

**Status:** Pre-development (foundation phase). Not yet public.
**MVP scope:** IH-35 through McLennan County, Texas. 5-20 ranked candidate sites.
**Product owner:** Nguyen Khai Huyen

---

## What this project is

Two goals running in parallel:
1. **OOHScout AI (the product)** — a real billboard site intelligence tool for Texas OOH operators
2. **Portfolio project** — demonstrates GeoAI + Regulatory RAG + Autonomous Agents

Both goals share the same codebase and use every technique learned from **Dr. Milan Janosov's courses**.

## Three-track architecture (per Milan's advice)

- **Track A — Spatial Engine** — deterministic GIS (corridor, spacing, demand, scoring, lease)
- **Track B — Regulatory RAG** — document retrieval over billboard rules with mandatory citations
- **Track C — Agent Capstone** — ReAct loop wrapping Track A + Track B as tools

Tracks stay decoupled until integration. See `docs/PRD.md` for detail.

---

## Repository structure

```
billboardAI/
├── README.md                    ← this file
├── CLAUDE.md                    ← rules for AI coding assistants
├── pyproject.toml               ← uv project config (Python 3.11)
├── .gitignore                   ← keeps data/, .env, and course materials out of git
├── .env.example                 ← template for API keys
│
├── backend/                     ← Python code + notebooks
│   ├── src/oohscout/
│   │   ├── data/                    Data ingestion clients (TxDOT, OSM, Sentinel, MCAD)
│   │   ├── track_a_spatial/         Track A — deterministic GIS
│   │   ├── track_b_rag/             Track B — regulatory RAG
│   │   ├── track_c_agent/           Track C — ReAct agent
│   │   ├── db/                      PostGIS schema + helpers
│   │   └── api/                     FastAPI (Phase 5+)
│   ├── tests/                       track_a/, track_b/, track_c/, golden_cases/
│   ├── notebooks/                   OOHScout notebooks (prototyping)
│   ├── data/                        Cached artifacts (gitignored)
│   ├── scripts/                     Utility scripts
│   └── geoai_utils.py               Shared utilities
│
├── frontend/                    ← Phase 5+ React + MapLibre dashboard (placeholder)
│
├── docs/                        ← All documentation
│   ├── PRD.md                       Comprehensive Product Requirements Doc (52 features)
│   ├── FEATURES.md                  Feature-to-chapter mapping
│   ├── MASTER_PLAN.md               Feature status + user stories + architecture
│   ├── DATA_VERIFICATION.md         Data source audit (real vs synthetic)
│   ├── CLAUDE.md                    AI assistant instructions
│   ├── decisions/                   Architecture decision records
│   └── learning/                    The 4-file chapter learning pattern
│       ├── README.md                Learning workflow
│       ├── template/                Template folder to copy per chapter
│       └── chapters/                Per-chapter learning artifacts
│           ├── geoai_ch04_data_prep/         ✅ Done
│           ├── geoai_ch05_segmentation/      ✅ Done
│           └── ua_advanced_ch01_setup/       ⏳ Next
│
└── (external, gitignored) reference materials
    ├── GeoAI_Essentials_Chapters/   Milan's GeoAI course (local only, not committed)
    └── ~/Downloads/files (1)/files/ Milan's Urban Analytics Advanced (local only)
```

---

## The 4-file learning pattern (per chapter)

Every chapter produces:
1. **`01_milan_original.ipynb`** — Milan's notebook, retyped by you
2. **`02_milan_explanation.md`** — line-by-line explanation (written by AI mentor)
3. **`03_oohscout_adaptation.ipynb`** — the same chapter applied to OOHScout / Waco data
4. **`04_adaptation_explanation.md`** — line-by-line for the adaptation

See `docs/learning/README.md` for the full workflow.

---

## Data sources verified

**Working right now:**
- TxDOT Commercial Signs API — 182 real billboard permits in McLennan County
- TxDOT AADT API — 819 traffic stations, 5-year history
- OpenStreetMap (roads, POIs, land use, buildings)
- Sentinel-2 STAC (NDVI)

**Pending (email requests):**
- McLennan County Appraisal District parcels
- City of Waco zoning shapefile

**Details:** `docs/DATA_VERIFICATION.md`

---

## Non-negotiable rules

1. Regulatory eligibility is a **hard gate** (PASS/FAIL/REVIEW), not a soft score
2. Never label a site "LEGAL" — always "passed preliminary screening; final eligibility requires municipal verification"
3. PostGIS owns spatial measurements — never let an LLM estimate distances/areas/geometry
4. RAG answers regulatory questions; deterministic GIS answers spatial questions; keep separate
5. No nationwide SaaS yet — MVP is one corridor (Waco)
6. Cite **43 TAC Chapter 21** for spacing rules (not §391.031)
7. Milan's course materials stay outside the git repo (copyright)

---

## Getting started

```bash
# Prerequisites: uv (https://github.com/astral-sh/uv), Python 3.11
uv sync

# Run notebooks
uv run jupyter lab backend/notebooks/

# Optional: verify environment
uv run python scripts/verify_environment.py
```

---

## Roadmap

See `docs/MASTER_PLAN.md` Section 4 for the ~27-week roadmap.

| Phase | Weeks | Deliverable |
|---|---|---|
| Phase 0 — Foundations | 1-4 | Urban Analytics Intro fluency check |
| Phase 1 — Track A Foundation | 5-8 | Retargetable corridor + demand engine |
| Phase 2 — Track A Spacing + Quality | 9-14 | LRS engine + zoning + scoring |
| Phase 3 — Track B RAG | 15-18 | Standalone regulatory intelligence |
| Phase 4 — Track C Agent | 19-22 | Integrated ReAct agent |
| Phase 5 — Portfolio launch | 23-27 | Delivery layer + GitHub polish |

---

## Learning path

Milan Janosov's courses (external — you purchase these separately):
- **Urban Analytics Intro** — foundations (GeoPandas, OSMnx) — recommended per Milan's advice
- **Urban Analytics Advanced** — Ch 1-6 provide 20+ OOHScout features
- **GeoAI Essentials** — Ch 4/5 done ✅; Ch 14 for the agent capstone
- **101 Steps to GeoAI from Scratch** — Milan says closest to this project

---

## Not-goals (scope discipline)

- ❌ Nationwide SaaS
- ❌ Real-time ad-serving integration
- ❌ Mobile app
- ❌ Second Texas county before Waco validated
- ❌ Any state other than Texas

---

## License

TBD. Course materials from Milan Janosov are not redistributed; see `CLAUDE.md` for copyright discipline.

---

## Credits

Techniques adapted from **Dr. Milan Janosov**:
- The New Science of Maps (courses): https://thenewscienceofmaps.com
- Books: *GeoAI Essentials*, *101 Steps to GeoAI from Scratch*, *Urban Analytics with Python — Advanced Methods*
