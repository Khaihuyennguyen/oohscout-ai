# F5 — Milan Explanation (Pointer)

Milan Janosov's `TEST_BBOX` pattern from UA Advanced Chapter 1 Section 1.4 is what F5 adapts. Rather than retype it here, read the F1 walkthrough that already explains it in depth:

**→ [F1's Milan explanation, Section 6](../ua_advanced_ch01_setup/02_milan_explanation.md)** — covers `TEST_BBOX` cells 21-25.

## The Milan pattern in one sentence

`TEST_BBOX = (minx, miny, maxx, maxy)` in WGS 84 → wrap in a Shapely `box`, project to metric CRS, use `.intersects()` to keep any GeoDataFrame row that touches the box.

## Why `intersects` and not `within`

- `within(bbox)` → drops any feature that crosses the bbox boundary
- `intersects(bbox)` → keeps boundary-crossing features whole and unclipped

For buildings, either works. For **highway lines** (F2) and **candidate points** (F7), you must use `intersects` — otherwise a linestring that pokes out one side gets thrown away entirely.

## Why the bbox goes into a metric CRS before filtering

Because `admin_gdf_metric`, `corridor_gdf_metric`, etc. are all in EPSG:32614. Spatial predicates like `intersects` require both geometries share the same CRS. Convert the bbox once, use it many times.

## Where to go next

Open [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb) — the runnable notebook that defines the Waco bbox and clips F1's boundary + F2's corridor to it.

For the WHY behind each design choice, read [04_adaptation_explanation.md](04_adaptation_explanation.md) after you've worked through 03.
