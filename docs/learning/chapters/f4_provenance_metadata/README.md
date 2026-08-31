# F4 — Data Provenance Metadata

**Status:** ⏳ In progress on `feature/f4-provenance-metadata`
**Feature:** F4 — attach a `.source.yaml` sidecar to every cached dataset

## What F4 is (plain English)

Every file we save to `backend/data/processed/` gets a small YAML file next to it that answers:
- Where did this data come from? (URL)
- Under what license?
- Can we use it commercially?
- When did we download it?
- Who verified it?

## Why F4 matters

Without provenance:
- You can't legally sell a corridor report without opening yourself to a licensing complaint from TxDOT / OSM contributors.
- Six months from now nobody remembers whether a file was TxDOT's official data or scraped from a forum.
- Every new data source becomes another unmarked bottle in the medicine cabinet.

With provenance:
- Every claim traces back to a source.
- Any audit passes cleanly.
- Adding new data sources becomes a habit, not a scavenger hunt.

## 5-file convention (same as F1 and F2)

| # | File | Purpose |
|---|---|---|
| 01 | [01_milan_original.ipynb](01_milan_original.ipynb) | Short pointer — F4 is not a Milan chapter |
| 02 | [02_milan_explanation.md](02_milan_explanation.md) | Short pointer + link to Milan's related discipline |
| 03 | [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb) | **Runnable end-to-end** — writes real sidecars for F1 and F2 outputs |
| 04 | [04_adaptation_explanation.md](04_adaptation_explanation.md) | Deep WHAT / WHY / HOW walkthrough per cell |
| 05 | [05_code_along.ipynb](05_code_along.ipynb) | Blank practice — retype from memory |

Because F4 isn't a Milan chapter, 01 and 02 are short pointers. 03, 04, 05 are the real learning artifacts.

## F4 completion gate

- [ ] Every `.gpkg` / `.geojson` file in `backend/data/processed/` has a matching `.source.yaml` sibling
- [ ] YAML schema documented (see [04_adaptation_explanation.md § Cells 3-4](04_adaptation_explanation.md))
- [ ] Pytest at `backend/tests/data/test_provenance.py` fails the build if any data file is missing its sidecar
- [ ] Production module `backend/src/oohscout/data/provenance.py` provides `write_source_yaml()` + `audit_provenance()` helpers

## What you do now (Phase 2 — learning)

1. Open [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb) and run it cell by cell.
2. Read [04_adaptation_explanation.md](04_adaptation_explanation.md) alongside for the WHY behind each cell.
3. When you feel you own it, try [05_code_along.ipynb](05_code_along.ipynb) — retype the pattern from memory with prompts as your guide.
4. When done, tell me **"done learning"** and I'll build the production module + pytest.
