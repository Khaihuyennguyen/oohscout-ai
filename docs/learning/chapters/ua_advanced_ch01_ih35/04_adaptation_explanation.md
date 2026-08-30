# F2 Adaptation — Deep Walkthrough (Mentor Mode)

**Feature:** F2 — Base Geometry: IH-35 Highway Centerline for McLennan County
**Notebook:** [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb)
**Production module:** [backend/src/oohscout/track_a_spatial/corridor.py](../../../../backend/src/oohscout/track_a_spatial/corridor.py)

Same shape as [F1's deep walkthrough](../ua_advanced_ch01_setup/04_adaptation_explanation.md): WHAT / WHY / HOW per cell. The story is shorter because F2 delegates most work to the production module — the notebook is thin by design.

---

## Cell 0 — Header

**WHAT.** Names the notebook, pins scope to F2 only, links to F1's boundary and the production module.

**WHY.** Same reason as F1's header: scope creep is what kills feature branches. F2 does **not** compute a buffer (F6), does **not** sample candidates (F7), does **not** score anything. Every temptation to "just add one more thing" moves to a different PRD feature.

---

## Cells 1-2 — Imports

**WHAT.** Load the four libraries F2 needs plus two functions from the production module.

**WHY the import from `oohscout.track_a_spatial`.** This is the whole reason F1a existed. Before F1a, `study_area.py` and `corridor.py` were orphan files nobody could reach. After F1a, they're a real installed package. The notebook now imports them the same way it would import geopandas or matplotlib — no path hacks, no `sys.path.insert`.

**HOW.** `load_or_build_study_area` and `load_or_build_ih35_centerline` are both cache-first — if the `.gpkg` file already exists on disk, they read it and skip the network round-trip. First run downloads; every run after is nearly instant.

---

## Cell 3 — Repo-root detection + configuration

**WHAT.** Walks the current directory up to find `pyproject.toml`; anchors `DATA_DIR` to `<repo>/backend/data/processed/`. Sets `PLACE` and `CRS_METRIC`.

**WHY unchanged from F1.** The Jupyter-launch-dir bug is real and the same fix applies. If you launched Jupyter from the chapter folder rather than the repo root, `Path("data")` would create a new cache in the wrong place. This walk anchors us regardless.

---

## Cell 4 — Load F1's boundary

**WHAT.** Calls `load_or_build_study_area()` and stores the result in `study`.

**WHY it doesn't re-geocode.** F1 already cached the McLennan polygon to `backend/data/processed/mclennan_county_study_area.gpkg`. This call hits that file and skips Nominatim entirely. On a fresh clone (no cache), it would call Nominatim once and then cache.

**HOW `study.admin_poly` becomes F2's input.** `admin_poly` is the WGS 84 union of the county boundary. F2 hands it to `ox.features_from_polygon()` which uses it as the "give me everything inside this shape" filter. Two features linked through one polygon — no coordinate juggling.

---

## Cells 5-6 — Fetch IH-35

**WHAT.** One function call: `load_or_build_ih35_centerline(admin_poly=study.admin_poly, cache_dir=DATA_DIR, crs_metric=CRS_METRIC)`. Prints segments, geometry types, unique-osmid check, total length, cache path.

**WHY it's one line here but 200 lines in the module.** The module does the work; the notebook proves it works. If we ever change what "IH-35 centerline" means (e.g., exclude frontage roads), we change one file — the module — and every notebook and test picks it up automatically.

**What the module actually does inside (five steps):**

1. **Overpass query** — `ox.features_from_polygon(admin_poly, tags={"highway": ["motorway"]})`. Returns every OSM way inside the county tagged as a motorway. This is the raw dataset.

2. **Geometry filter** — keep only `LineString` and `MultiLineString`. Some OSM motorway records are `Point` (a numbered exit marker with the motorway tag). Points have no length; if we left them in, the total-length calculation would silently be wrong. Filter fast.

3. **Ref filter** — keep rows whose `ref` starts with `"I 35"`. OSM tags IH-35 with `ref="I 35"` (space between "I" and "35"). Some segments have multi-refs like `"I 35;US 77"` (shared with US-77). The `_matches_ref` helper accepts either.

4. **Dedupe on osmid** — OSMnx occasionally returns the same way twice with byte-identical geometry. I verified this against the actual McLennan data — 4 osmids appeared twice, `.geometry.equals()` returned `True` for every pair. The dedupe is safe: it drops exact duplicates, not distinct data. Without it, the `osmid.is_unique` assertion fires and F2 refuses to ship.

5. **Project + cache** — convert to EPSG:32614 (metric) and write to `mclennan_ih35_centerline.gpkg`. The projected representation is what gets cached because that's what downstream features (F6 buffer, F7 candidate sampling, F8 spacing) will read.

**WHY the result is ~130 km, not the ~55 km Google Maps shows.** OSM stores IH-35 as **separate ways per direction**. Northbound + southbound each contribute their own ~55 km. Add ~20 km of frontage roads / ramps that carry the `I 35` ref, and you land at ~130 km. This is the right number for OOHScout: billboard sites exist on both sides of the highway, so counting both directions is what we want. If a future feature needs "one-direction length," we'd add a `direction` filter — not a project-wide decision.

---

## Cell 7 — Markdown: visual-check preamble

**WHAT.** Explains what "success" looks like in the plot: red lines through Waco, diagonal orientation.

**WHY the human eye still matters.** The assertions catch "wrong shape" bugs (geometry type mismatch, empty result, non-unique key). They cannot catch "correct shape, wrong place" — Nominatim returning the wrong `admin_poly` would still produce a plausible-looking LineString set, just not for McLennan. The visual is the belt to the assertions' suspenders.

---

## Cell 8 — Plot with basemap + savefig

**WHAT.** Draws the county boundary in blue and the corridor in red on top of Esri satellite imagery. Saves the figure to `mclennan_ih35_f2_check.png` before `plt.show()`.

**WHY save-before-show.** Same Jupyter gotcha we hit in F1: `plt.show()` closes the figure in Jupyter, so `savefig` after it writes an empty PNG. Save first, show second. This is why the F1 code-along notebook explicitly asks you to name this trap.

**WHY draw the boundary too.** Because a red line in the middle of a satellite tile has no obvious spatial context — you need something to say "this is McLennan." The blue boundary is the frame; the red highway is the subject.

---

## Cell 9 — Markdown: completion gate

**WHAT.** Six-item checklist that flips F2 from ⏳ to ✅.

**WHY items 1-5 are automated and item 6 is manual.** The pytest at [backend/tests/track_a/test_corridor.py](../../../../backend/tests/track_a/test_corridor.py) covers items 1-5 with real assertions — you never have to check them by hand. Item 6 (visual boundary check) stays manual in the notebook and gets encoded programmatically elsewhere by verifying a known landmark on IH-35 (Waco courthouse is *not* on IH-35, but Baylor stadium or a specific mile marker could be — see the test file for the specific coordinates chosen).

---

## What this notebook does NOT do

- **No corridor buffer.** That's F6 — `ox.geometry.buffer(500)` around the merged LineString.
- **No candidate points.** That's F7 — `line.interpolate(distance_along)` every 1 km.
- **No TxDOT permit join.** That's F8's dependency, not F2's.
- **No POI join.** That's F10.

Same discipline as F1: ship the smallest thing that clears the gate.

---

## What the production module does that the notebook does not

Identical split to F1's:

| Concern | Notebook | Module |
|---|---|---|
| Interface | Two function calls, prints | `Corridor` dataclass |
| Assertions | Fail loudly with helpful messages | Same, but raised so callers can catch |
| Retargeting | Edit `PLACE` | Pass a different `admin_poly` |
| Called by | Human running Shift+Enter | FastAPI, agent tools, pytest |

---

## The one-line mental model

**F2 is F1's building fetch with one tag swap and one geometry-type swap. Everything else — cache pattern, CRS discipline, unique-key assertion, GeoPackage output — is exactly the same.**
