# F5 — Test-BBox Subset for Fast Iteration

**Status:** ⏳ In progress on `feature/f5-test-bbox`
**Feature:** F5 — DEV_MODE bounding box around Waco urban core so pipelines run in seconds during development

## What F5 is (plain English)

McLennan County is ~2,747 km². Loading POIs, computing buffers, and sampling candidates for the whole county takes minutes. When you're debugging code, you want a much smaller area so a re-run is fast.

F5 defines a small bounding box around downtown Waco (~50 km²) and provides a helper that clips any GeoDataFrame to it. When `DEV_MODE=True`, downstream features scope their work to that bbox instead of the full county.

## Why F5 matters

Without a DEV_MODE bbox:
- Every iteration on F6/F7/F10/etc. loads the whole county → slow feedback loop
- You catch bugs 30 seconds later instead of 3 seconds later
- Development stalls when the network is slow

With DEV_MODE:
- Full pipeline runs in <30 seconds while iterating
- Flip a single flag when you're ready for the full-county run
- CI can use it to test fast

## 5-file convention

| # | File | Purpose |
|---|---|---|
| 01 | [01_milan_original.ipynb](01_milan_original.ipynb) | Pointer to F1's Milan Ch 1 TEST_BBOX section |
| 02 | [02_milan_explanation.md](02_milan_explanation.md) | Pointer to F1's Milan explanation of TEST_BBOX pattern |
| 03 | [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb) | Runnable — defines Waco bbox, clips F1 + F2 outputs, times before/after |
| 04 | [04_adaptation_explanation.md](04_adaptation_explanation.md) | Deep WHAT / WHY / HOW walkthrough |
| 05 | [05_code_along.ipynb](05_code_along.ipynb) | Retype from memory |

## F5 completion gate

- [ ] `WACO_URBAN_BBOX` constant defined with reasoning
- [ ] `clip_to_bbox(gdf, bbox)` helper works on any projected GeoDataFrame
- [ ] With DEV_MODE on, the full F1 → F2 → clip pipeline runs in <10 seconds
- [ ] Production module `backend/src/oohscout/track_a_spatial/dev_mode.py` importable
- [ ] Pytest verifies clipped output is a proper subset of the full output

## What you do now

1. Open [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb) and run it cell by cell.
2. Read [04_adaptation_explanation.md](04_adaptation_explanation.md) alongside.
3. Try [05_code_along.ipynb](05_code_along.ipynb) to prove you own the pattern.
4. When done, tell me **"done learning"** and I'll build the production module + pytest.
