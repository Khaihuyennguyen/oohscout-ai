# F4 Adaptation — Deep Walkthrough (Mentor Mode)

**Feature:** F4 — Data Provenance Metadata
**Notebook:** [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb)
**Production module (built after learning phase):** `backend/src/oohscout/data/provenance.py`

Same shape as F1 and F2's deep walkthroughs: WHAT / WHY / HOW per cell. F4 is short because it's paperwork, not spatial math — but the *why* is the important part.

---

## Cell 0 — Header

**WHAT.** Names the notebook, pins scope to F4, describes what the notebook will do end-to-end.

**WHY.** F4 is boring. There's no map at the end, no pretty output. If the notebook doesn't open with "here's the concrete artifact we're producing," it's easy to skim past. The header locks it in: **YAML sidecars for every cached dataset.**

---

## Cells 1-2 — Imports

```python
from datetime import date
from pathlib import Path
import yaml
```

**WHAT.** Load three things: today's date, cross-platform paths, and PyYAML.

**WHY `yaml` and not just `json`.** JSON doesn't support comments and forces you to quote every key. YAML reads like plain English — a Waco attorney could inspect one of these files without any Python knowledge and understand what it says. That readability is the point of provenance metadata: it's for humans, not machines.

**WHY `date` and not `datetime`.** We only care what day we downloaded the file, not the second. Storing a full timestamp implies precision we don't have.

---

## Cells 3-4 — The 8-field schema

**WHAT.** Defines the 8 fields every sidecar must contain, and wraps them in a Python function `make_source_record()`.

**WHY 8 fields and not 20.** Two competing pressures:

1. **Too few fields** → sidecars are useless. If we only stored `source_url`, we couldn't answer "can we sell this?"
2. **Too many fields** → nobody fills them in. If we required 20 fields for every dataset, every ingestion function would have 20 arguments and half of them would be `None`.

The 8 chosen — `source_name`, `source_url`, `retrieval_date`, `retrieval_method`, `record_count`, `license`, `commercial_use_allowed`, `redistribution_allowed` — are the minimum that answer: *where, when, how, how much, and under what terms*.

**WHY a function and not a class.** A `SourceRecord` class would add ceremony without value. `make_source_record()` returns a plain dict that YAML can serialize directly. When you type-check code that consumes it, use a `TypedDict` (Python's structural typing for dicts) — but even that's overkill for the notebook.

**WHY `sort_keys=False`.** By default `yaml.safe_dump` sorts keys alphabetically. That would put `authority` first and `source_url` fourth — hostile to a human reading the file top-down. We preserve insertion order so the fields read in a natural narrative.

---

## Cells 5-6 — Write the McLennan sidecar

**WHAT.** Load the F1 output, count the records, build a source record, save it next to the `.gpkg`.

**WHY `record_count` matters.** Six months from now, if the OSM boundary changes (McLennan County isn't going to move, but this pattern will apply to every future dataset), we want to detect it. The `record_count` gives us a fast integrity check: if today the file has 1 record and tomorrow it has 3, something changed. That's a signal to re-verify.

**WHY the sidecar sits *next to* the data file (not in a central manifest).** Three reasons:

1. **Locality of reference.** If you delete `mclennan_county_study_area.gpkg`, its provenance goes with it. No stale entries in a central file.
2. **Git-friendliness.** A central manifest would generate merge conflicts every time two feature branches add data. Sidecars don't touch each other.
3. **Discoverability.** Anyone browsing `backend/data/processed/` sees the sidecar right next to the data. No hunt through a docs folder.

**WHY `Open Database License (ODbL) 1.0` specifically.** That's the actual license OSM uses. It's not "public domain" (which is a common misconception). ODbL requires attribution and share-alike for derived databases. Getting this field right is the difference between a legal paid deliverable and a licensing complaint.

**WHY `commercial_use_allowed=True` for OSM.** ODbL explicitly permits commercial use as long as attribution is preserved. The `notes` field records the exact attribution string to use.

---

## Cells 7-8 — Write the IH-35 sidecar

Same pattern, different source. IH-35 came from Overpass (a different OSM endpoint) using OSMnx's `features_from_polygon`. The `retrieval_method` field captures that so a future reader knows to re-fetch via the same API if they need to update.

**One thing that changes from cell 6:** `notes` documents the dedupe step ("Deduped on osmid"). Provenance sidecars should record any non-trivial cleaning done between the raw fetch and the cached file — those transformations are part of the data's identity.

---

## Cells 9-10 — Round-trip check

**WHAT.** Read each sidecar back and assert a few required fields exist.

**WHY.** YAML that writes successfully can still be broken (accidental tab characters, unquoted `NO` that YAML parses as boolean `False`, etc.). The round-trip is the shortest possible test that the file we just wrote is actually consumable.

**HOW.** `yaml.safe_load` is the important detail. Never use `yaml.load()` without `Loader=` — it can execute arbitrary Python code if the file was tampered with. `safe_load` limits input to plain data types.

---

## Cells 11-12 — The audit function

**WHAT.** Scan `backend/data/processed/` for all `.gpkg` and `.geojson` files, check each for a matching `.source.yaml`, return the list of files missing sidecars.

**WHY this is the F4 payoff.** The function is 8 lines. When it becomes a pytest in Phase 3, any developer (including future-you) who adds a new dataset without a sidecar breaks the build. That's how "provenance discipline" turns from *good intention* into *enforced habit*.

**HOW it becomes the pytest.** After learning phase, I'll port this function into `backend/src/oohscout/data/provenance.py` and write `test_all_data_files_have_sidecars` in `backend/tests/data/test_provenance.py`. The test calls the audit and asserts `missing == []`.

---

## Cell 13 — Completion gate

Same shape as F1/F2's completion gates. Items 1-3 are done inside this notebook by you; items 4-5 are what I'll build after you say "done learning."

---

## What this notebook does NOT do

Deliberately out of scope for F4:
- Doesn't validate license compatibility across sources (e.g. "can I combine OSM + TxDOT in one product?"). That's a legal question, not a code question.
- Doesn't auto-generate sidecars from HTTP response headers. Simpler to write them explicitly during ingestion.
- Doesn't sign or hash the data file. If we ever need tamper-detection, that's a follow-up feature.

---

## The one-line mental model

**F4 turns every cached data file from an anonymous artifact into a licensed, sourced, dated record you can defend in front of an attorney.**
