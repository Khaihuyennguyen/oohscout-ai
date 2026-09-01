# F5 Adaptation — Deep Walkthrough (Mentor Mode)

**Feature:** F5 — DEV_MODE test bbox around Waco urban core
**Notebook:** [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb)
**Production module (built after learning phase):** `backend/src/oohscout/track_a_spatial/dev_mode.py`

Same WHAT / WHY / HOW pattern as F1, F2, F4. F5 is short because it's a discipline, not new math — but the discipline matters.

---

## Cell 0 — Header

**WHAT.** Names the notebook, pins scope to F5, describes end-to-end deliverable.

**WHY.** Every future feature that says "give me POIs" or "sample candidates" will want to run against the bbox during development and the full county in production. Anchoring the pattern here means F6, F7, F10, F16 all know where to import the bbox constant from — no copy-paste drift.

---

## Cells 1-2 — Imports

Nothing new versus F1/F2 except `time.perf_counter` and `shapely.geometry.box`.

**WHY `time.perf_counter` and not `time.time`.** `perf_counter` is monotonic and has nanosecond resolution — the right tool for measuring elapsed time. `time.time` can jump backwards during NTP sync and rounds to milliseconds on some platforms.

**WHY `shapely.geometry.box(minx, miny, maxx, maxy)` and not `Polygon([...])`.** `box` builds a 5-vertex closed rectangle from 4 numbers. Building it by hand from Polygon coordinates is error-prone (wrong vertex order → invalid polygon, wrong closure → holes). `box` is the "there's one obvious way" tool.

---

## Cells 3-4 — Load F1 + F2 outputs

**WHAT.** Calls `load_or_build_study_area()` and `load_or_build_highway_centerline()` — both cache-first, so no network. Times the whole thing.

**WHY time it.** The whole point of F5 is "make iteration faster." If you can't measure baseline speed, you can't prove F5 helps. The `full_load_secs` number is the number F5 competes against.

**HOW the numbers roll up.** `full_area_km2` = 2,747 km², `full_length_km` ≈ 131, `full_segments` = 245. Those are the "before" numbers.

---

## Cells 5-6 — Define the Waco bbox

```python
WACO_URBAN_BBOX = (-97.20, 31.48, -97.05, 31.62)
```

**WHAT.** A 4-tuple of `(minx, miny, maxx, maxy)` in WGS 84 degrees. Roughly a 15 km × 15 km rectangle covering downtown Waco, Baylor, and the IH-35 mainline through the city.

**WHY these specific coordinates.**
- **West edge -97.20°** — just past West Waco (I-35 mainline is around -97.14°)
- **South edge 31.48°** — includes Bellmead and industrial south
- **East edge -97.05°** — past Bellmead / east industrial park
- **North edge 31.62°** — past Elm Mott suburbs
- These are eyeballed from a satellite view. Not optimal — that's fine. F5 is a dev tool, not a scientific claim.

**WHY WGS 84 degrees and not metric meters.** The bbox constant is what a human types when redefining it. Nobody thinks "the meter coordinate of downtown Waco is X." They think "37th and Franklin is roughly 31.55°N, -97.15°W." Storing the constant in WGS 84 matches how humans reason about places.

**WHY convert to metric before use.** All F1/F2 output lives in EPSG:32614 meters. Spatial predicates (`intersects`, `within`, etc.) require both geometries share the same CRS. Converting the bbox once at the top is cheap; converting the corridor (245 segments) every time you filter is not.

**Sanity check:** `bbox_area_km2 / full_area_km2 * 100` — should show ~7-8%. If it's 100%, you accidentally defined a McLennan-sized bbox. If it's 0.001%, you accidentally used meters as degrees.

---

## Cells 7-8 — Clip the corridor

```python
corridor_clipped = corridor.corridor_gdf_metric[
    corridor.corridor_gdf_metric.intersects(bbox_metric)
].reset_index(drop=True)
```

**WHAT.** Boolean-mask the corridor GeoDataFrame to only rows whose geometry touches the bbox.

**WHY `intersects` and not `within`.**
- `within(bbox)` — TRUE only if the entire geometry is inside. A highway segment poking one meter outside the bbox → dropped. Wrong for lines.
- `intersects(bbox)` — TRUE if the geometry touches the bbox at all. A segment crossing the edge → kept whole. Right for lines.

This distinction is the F5-specific trap. `within` looks safer ("stay inside the box"), but for line features it silently discards the very segments you're trying to study.

**WHY `.reset_index(drop=True)`.** After filtering, the index gaps (`0, 3, 7, 42, ...`) confuse downstream code that expects `0, 1, 2, ...`. Reset the index and drop the old one.

**WHY time this separately.** Two different questions: "how long to LOAD data?" (fixed cost, F1/F2 caches solve it) vs "how long to CLIP data?" (variable cost, scales with data size). The clip is typically <100 ms even for large layers — the takeaway is *it's essentially free*, so downstream features should feel free to call it.

**Expected output:** `clipped_length_km` ≈ 30-40 km (out of 131), `len(corridor_clipped)` ≈ 60-80 (out of 245). ~4x fewer segments to process per iteration.

---

## Cells 9-10 — Visual side-by-side

**WHAT.** Two matplotlib subplots — left shows full county + IH-35, right shows the bbox + clipped IH-35 — both over Esri satellite imagery.

**WHY side-by-side.** A single "here's the bbox" plot doesn't convey the reduction. The two-panel layout makes the "this is what we cut down to" story obvious at a glance. Anyone reviewing the branch understands what F5 does in three seconds.

**WHY save the PNG before `plt.show()`.** Same Jupyter gotcha we hit in F1: `plt.show()` closes the figure in Jupyter, so `savefig` after it produces a blank canvas. Save first, show second.

---

## Cell 11 — Completion gate

Same shape as F1/F2/F4. Items 1-4 are user-executable inside the notebook; items 5-6 are what I build after "done learning."

---

## What this notebook does NOT do

- **Doesn't clip F1's boundary.** Deliberate — the boundary is a static reference frame. Clipping it would make the bbox look like the whole world.
- **Doesn't sample candidates or fetch POIs inside the bbox.** Those are F6/F7/F10. F5 just proves the clipping mechanism works.
- **Doesn't introduce a `DEV_MODE` global flag or environment variable.** Deliberately postponed — global flags are opt-in complexity. Better to have callers pass a `bbox=None` parameter and default to full-county when omitted.

---

## What the production module will add

After you say "done learning," I'll write `backend/src/oohscout/track_a_spatial/dev_mode.py` with:

- `WACO_URBAN_BBOX_WGS84 = (-97.20, 31.48, -97.05, 31.62)` — the constant, exported
- `waco_urban_bbox(crs_metric: int) -> Polygon` — returns the bbox projected to any metric CRS
- `clip_to_bbox(gdf, bbox)` — the intersects+reset_index helper

And a pytest at `backend/tests/track_a/test_dev_mode.py` that verifies clipped output has fewer rows than input and preserves CRS.

---

## The one-line mental model

**F5 turns "wait 60 seconds every time you re-run" into "wait 3 seconds every time you re-run" by scoping the work to ~7% of the county area during development.**
