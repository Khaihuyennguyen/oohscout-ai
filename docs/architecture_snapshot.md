# OOHScout Architecture Snapshot

**Last Updated:** August 2026
**Current Branch:** `feature/f5-test-bbox`
**Overall Status:** ~8% Complete (On Step 1 of 10)

---

## The 7-Story Building

Think of OOHScout as a 7-story building. Each floor has a specific job. Right now you have a foundation, a partial 1st floor, and a partial 2nd floor. Everything above that is empty land.

```text
                                                             STATUS
┌──────────────────────────────────────────────────────────┐
│  🏠 ROOF — Web UI (Mapbox map, React)                    │  ⬜ 0%   deferred
├──────────────────────────────────────────────────────────┤          until first sale
│  🚪 5F — Front doors                                     │
│      • FastAPI sidecar (auth, errors, health)            │  🟨 ~20% scaffolded
│      • MCP server (3 tools for Claude Desktop)           │  🟨 ~20% mocked DB
├──────────────────────────────────────────────────────────┤
│  🧠 4F — Agent brain (Track C, "the chef")               │
│      Decides which tools to call. ReAct loop.            │  ⬜ 0%   not started
│      LangGraph + Claude/Groq                             │
├──────────────────────────────────────────────────────────┤
│  ⚖️ 3F — Legal brain (Track B, "the lawyer")             │
│      Reads county PDFs, answers with § citations.        │  ⬜ 0%   not started
│      pgvector + retrieval + citation gate                │
├──────────────────────────────────────────────────────────┤
│  📏 2F — Spatial brain (Track A, "the ruler")            │  🟨 ~17%  ← YOU ARE HERE
│      F1 study area  ✅                                   │           building
│      F2 highway     ✅                                   │           F5 next
│      F3 ingestion   ✅                                   │
│      F4 provenance  ✅                                   │
│      F5 dev bbox    ⏳ ← you are working on this         │
│      F6–F30         ⬜                                   │
├──────────────────────────────────────────────────────────┤
│  🛡️ 1F — Security cage + authoring                       │  🟨 ~30% scaffolded
│      SSRF ✓  SQL guard ✓  error sanitizer ✓              │           14 patterns
│      Missing: atomic writes, PROJECT_MARKERS,            │           missing
│      NaN guard, credential redactor, token auth wired… │
├──────────────────────────────────────────────────────────┤
│  🗄️ BASEMENT — Data storage                              │  ⬜ 0%   not installed
│      Postgres + PostGIS + pgvector                       │           still using
│      Currently: only .gpkg files on disk                 │           local files
└──────────────────────────────────────────────────────────┘
```

---

## What happens when a customer asks "find me sites on IH-35"

```text
USER: "find sites on IH-35 in Waco"
   │
   ▼
[⬜ not built]  Web UI receives the question
   │
   ▼
[🟨 scaffolded] API/MCP entry point takes the request
   │
   ▼
[⬜ not built]  Chef (ReAct agent) plans the steps
   │
   ├─► [✅] "load study area"     → Track A · F1 works
   ├─► [✅] "load highway"        → Track A · F2 works
   ├─► [⏳] "clip to dev bbox"    → Track A · F5 you're on this
   ├─► [⬜] "buffer 500m"         → Track A · F6 not built
   ├─► [⬜] "sample candidates"   → Track A · F7 not built
   ├─► [⬜] "check zoning"        → Track B · F31–36 not built
   ├─► [⬜] "check legal rule"    → Track B · F9 needs RAG first
   ├─► [⬜] "score candidates"    → Track A · F25 not built
   │
   ▼
[⬜ not built]  Save PASS/FAIL/REVIEW to Postgres
   │
   ▼
[⬜ not built]  Return ranked list to user
```
*Of the 8 things that need to happen in a single request, 3 work, 1 is in progress, and 4 don't exist yet.*

---

## The 10 Milestones to an MVP

This is the exact sequence to get to a working MVP in ~8 to 10 weeks. 

| # | Milestone | What "done" looks like | Est. |
|---|---|---|---|
| **1** | **Finish F5 (dev bbox)** | **[YOU ARE HERE]** | ~this week |
| 2 | Finish Track A engine (F6–F9) | corridor → buffered zone → candidate points → tiered setback | 2 weeks |
| 3 | Finish Track A demand + zoning (F10–F22) | each candidate has POI/AADT/zoning attributes | 3–4 weeks |
| 4 | Finish Track A scoring (F25, F27) | ranked list, top 10% flagged | 1 week |
| 5 | Set up Postgres + PostGIS + pgvector | basement dug, DB live locally | 3 days |
| 6 | Finish security cage (V2 §S4–S17) | atomic writes, PROJECT_MARKERS, credential redactor, TrustedHost, token auth wired to real DB | 1 week |
| 7 | Build Track B RAG (F31–F36) | ask "what does 43 TAC Ch 21 say about setbacks?" and get an answer with a § citation | 2 weeks |
| 8 | Build Track C agent (F37–F41) | agent orchestrates Track A + Track B tools, one ReAct loop, golden tests | 2 weeks |
| 9 | Wire FastAPI + MCP to real DB | Claude Desktop can call OOHScout and get real ranked candidates for IH-35 Waco (remove MagicMock) | 3 days |
| 10 | Sell one corridor analysis | commercial milestone | — |
