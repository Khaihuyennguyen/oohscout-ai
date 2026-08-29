# OOHScout AI — Real Waco Billboard Market (Chapter 4 Only)
# Explanation for: oohscout_real_txdot_data.ipynb

This document explains the notebook line by line, WHY each piece exists for
the product, and — critically — proves that **every technique came from
Chapter 4 of GeoAI Essentials**. Nothing here requires knowledge from
chapters you haven't studied yet.

**Companion documents:**
- `DATA_VERIFICATION_REPORT.md` (project root) — proof every data source is real
- `notebooks/ch04_explanation.md` — the original Chapter 4 explanation

---

## WHY THIS NOTEBOOK EXISTS

Before this rewrite, the notebook used sophisticated techniques from chapters
you hadn't studied (spatial joins, line merging, buffer polygons, weighted
scoring). That made the code hard to follow and hard to trust.

**The rewrite has three product goals:**

1. **Real billboards are the STAR of the map** — every popup shows real
   permit ID, real operator, and three ways to independently verify.
2. **AADT is available but hidden by default** — traffic data confused
   the visual because giant blue circles overwhelmed small billboard dots.
   Now it's a togglable advanced layer.
3. **Every line of code is traceable to Chapter 4** — no black boxes.

---

## THE FULL PIPELINE (visual)

```
════════════════════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────────────┐
  │  SECTION 1: SETUP                                               │
  │  Imports, WACO_BBOX, TxDOT endpoints, POI tag categories        │
  └───────────────────────────┬─────────────────────────────────────┘
                              ↓
  ┌─────────────────────────────────────────────────────────────────┐
  │  HELPER: fetch_txdot(endpoint_url, where, cache_path)           │
  │  Uses requests.get() — same as Ch4 Step 34 NYC download         │
  └────────────┬───────────────────────────────┬────────────────────┘
               ↓                               ↓
  ┌──────────────────────────────┐  ┌──────────────────────────────┐
  │  SECTION A: THE STAR         │  │  SECTION D (OPTIONAL)        │
  │  Real TxDOT Billboards       │  │  AADT Traffic Stations       │
  │  A.1 Download                │  │  D.1 Download                │
  │  A.2 Filter to IH-35 +       │  │  (hidden by default on map)  │
  │      build verify URLs       │  └──────────────────────────────┘
  │  A.3 Market intelligence     │
  └────────────┬─────────────────┘
               │
  ┌────────────┴────────────┐
  ↓                         ↓
  ┌───────────────────────────┐    ┌───────────────────────────┐
  │  SECTION B: POIs          │    │  SECTION C: IH-35 line    │
  │  ox.features_from_polygon │    │  ox.features_from_polygon │
  │  (Ch4 Step 34)            │    │  (Ch4 Step 29)            │
  └────────────┬──────────────┘    └────────────┬──────────────┘
               └────────────┬──────────────────┘
                            ↓
  ┌─────────────────────────────────────────────────────────────────┐
  │  SECTION E: THE MAP                                             │
  │  folium.Map + 4 FeatureGroups + LayerControl                    │
  │  ✅ IH-35 line          ON                                      │
  │  ✅ Real billboards     ON (with 3 verification links)          │
  │  ✅ POI advertisers     ON                                      │
  │  ☐  AADT stations       OFF (advanced toggle)                   │
  └───────────────────────────┬─────────────────────────────────────┘
                              ↓
  ┌─────────────────────────────────────────────────────────────────┐
  │  SECTION F: SUMMARY                                             │
  │  What we proved + Ch4 techniques used + what's next             │
  └─────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════════════
```

---

## THE CHAPTER 4 → OOHSCOUT MAPPING

This table proves every single technique in the notebook came from Ch4:

| Notebook line | Chapter 4 origin |
|---------------|------------------|
| `import osmnx as ox` | Ch4 Section 1 (imports) |
| `import folium` | Ch4 Section 1 |
| `import requests` | Ch4 Section 1 |
| `from shapely.geometry import box` | Ch4 Section 1 |
| `WACO_BBOX = [W, S, E, N]` | Ch4 constant `BBOX = [18.183, 45.907, ...]` |
| `box(*WACO_BBOX)` | Ch4 `box(*BBOX)` (used 6 times) |
| `ox.features_from_polygon(poly, tags={'amenity': [...]})` | Ch4 Step 34 (Manhattan amenity POIs) |
| `ox.features_from_polygon(poly, tags={'highway': ...})` | Ch4 style (Ch4 didn't do highway but same pattern) |
| `requests.get(url, params, headers, timeout)` | Ch4 Step 34 (NYC NTA download, line-by-line same) |
| `response.raise_for_status()` | Ch4 Step 34 |
| Cache pattern `if path.exists(): load else: download+save` | Ch4 Step 29 (buildings), used everywhere |
| `.to_crs('EPSG:32614')` | Ch4 Step 29 (used `.to_crs('EPSG:27700')` for Edinburgh) |
| `gpd.GeoDataFrame.from_features(features, crs=WGS84)` | Ch4 Step 34 |
| `.to_file(path, driver='GeoJSON')` | Ch4 Steps 29, 32, 34 |
| Filter `geom_type.isin(['Polygon','LineString'])` | Ch4 Steps 29, 32 |
| `folium.Map(location, zoom_start, tiles)` | Ch4 Step 34 (`fmap_edi = folium.Map(...)`) |
| `folium.GeoJson(features, style_function=...)` | Ch4 Step 34 (OSM building polygons overlay) |
| `folium.CircleMarker(location, radius, color, fill, popup)` | Ch4 Step 34 (POI markers) |
| `folium.FeatureGroup(name, show=True/False)` | Ch4 Step 34 (`show=False` for hidden layers) |
| `folium.Popup(html, max_width)` | Ch4 Step 34 (info popups) |
| `folium.LayerControl(collapsed=False)` | Ch4 Step 34 (toggle panel) |
| `.value_counts()` on a column | Ch4 Step 34 (`pois_man['amenity'].value_counts()`) |

**Techniques deliberately NOT used** (from chapters you haven't studied):

| Advanced technique | Where it comes from | Why we skip it |
|--------------------|--------------------|--------------------------------|
| `gpd.sjoin_nearest()` | Advanced GeoPandas | Ch4 doesn't cover spatial joins |
| `shapely.ops.unary_union` | Advanced Shapely | Not in Ch4 |
| `shapely.ops.linemerge` | Advanced Shapely | Not in Ch4 |
| `.buffer(distance)` on lines | Advanced Shapely | Not in Ch4 |
| `line.interpolate(distance)` | Advanced Shapely | Not in Ch4 |
| Weighted scoring / ranking | Not chapter-specific | Requires spatial joins first |

Everything advanced is deferred until you've studied the chapter that
introduces the technique honestly.

---

## SECTION-BY-SECTION EXPLANATION

### SECTION 1 — Setup

**What it does:** Imports (only Ch4-style), defines the study area,
and stores the two verified real TxDOT endpoints.

**Key variables:**

| Constant | Value | Meaning |
|----------|-------|---------|
| `WACO_BBOX` | `[-97.25, 31.30, -96.95, 31.85]` | Study area [W, S, E, N] |
| `TXDOT_BILLBOARDS_URL` | Commercial_Signs ArcGIS endpoint | 14,943 real permits in TX |
| `TXDOT_AADT_URL` | AADT Annuals ArcGIS endpoint | Real traffic counts |
| `WGS84` | `'EPSG:4326'` | Standard lat/lon for storage/display |
| `TEX_CRS` | `'EPSG:32614'` | UTM Zone 14N (meters) for area/length math |
| `ADVERTISER_TAGS` | Dict of OSM tag→categories | Billboard-relevant business types |

**Product perspective:** These constants are the "front door" of the
notebook. Every downstream cell uses them.

---

### HELPER — `fetch_txdot(endpoint_url, where, cache_path)`

**What it does:** Downloads records from any TxDOT ArcGIS FeatureServer,
with automatic pagination and caching.

**The Chapter 4 origin:** This is the SAME pattern as Ch4 Step 34:

```python
# Chapter 4 Step 34 (verbatim):
response = requests.get(url, headers=headers, params={'$limit': 1000}, timeout=30)
response.raise_for_status()
nhoods_all = gpd.GeoDataFrame.from_features(response.json()['features'], crs=4326)
```

The only additions are:
1. A while-loop for pagination (ArcGIS returns max 2000 per response)
2. The cache-file check

Both are trivial extensions to what Ch4 already taught.

**Product perspective:** This one function unlocks every state government
GIS portal in the US. All of them use ArcGIS. Learn the pattern once,
reuse across every future OOHScout expansion.

---

### SECTION A — Real Billboards (THE STAR)

**Cell A.1 — Download**
Uses `fetch_txdot(where="CNTY='McLennan'")`. Returns all 182 real permits
in McLennan County. Cached to disk on first run.

**Cell A.2 — Filter to IH-35 + build verification URLs**
Simple pandas filter (`billboards['HWY'] == 'IH 35'`). Then constructs a
`verify_url` for each billboard that opens the TxDOT public map viewer
zoomed to that exact location.

**Cell A.3 — Market intelligence**
`.value_counts()` on operator name and electronic flag reveals:
- Who dominates the Waco market (Lamar Advantage Outdoor)
- Digital vs static ratio
- Digital conversion opportunity percentage

**Product perspective:** When you sit with a Waco operator, you now have
real numbers to open with. "Lamar owns X% of McLennan permits" is a
conversation starter that proves you did the homework.

---

### SECTION B — POI Advertiser Demand

**Cell B.1 — Download from OSM**
Uses `ox.features_from_polygon()` with the `ADVERTISER_TAGS` dict —
loops through three tag categories (amenity, shop, tourism) and
concatenates the results.

This IS Chapter 4 Step 34 with more categories. Ch4 grabbed only
`amenity=True` for Manhattan. We narrow to billboard-relevant subsets
because they're more meaningful signals.

**Product perspective:** POIs are the FREE proxy for advertiser demand.
A candidate zone with 12 POIs within visual range has 12 potential
paying advertisers. A zone with 0 has none.

---

### SECTION C — IH-35 Highway Line (Context)

**Cell C.1 — Download from OSM**
Same `ox.features_from_polygon()` pattern, this time with `highway`
tag. Filter to `LineString` / `MultiLineString` (Ch4 pattern), then
to `highway == 'motorway'` (mainlane only, excludes ramps).

**Product perspective:** The highway line gives the map visual
context. Without it, the billboards look like scattered dots in
Waco. With it, the corridor is visible.

Note: We deliberately don't do anything MATHEMATICAL with the road
line (no buffer, no sample-points-along, no merge). Chapter 4 didn't
teach those operations. We just SHOW the line as a visual reference.

---

### SECTION D — AADT (Optional Advanced Layer)

**Cell D.1 — Download**
Uses `fetch_txdot()` again for AADT stations. Converts numeric fields
defensively (see the fix history — TxDOT returns some numerics as
strings).

**Product perspective:** AADT is critical for pricing but confusing
visually. This layer is downloaded and prepared but rendered on the
map with `show=False`, meaning the checkbox in the layer control
starts UNCHECKED. Advanced users toggle it on when needed.

---

### SECTION E — The Map (The Deliverable)

**Cell E.1 — Build with folium**
Every folium construct here (Map, GeoJson, CircleMarker, Popup,
FeatureGroup, LayerControl) came directly from Ch4 Step 34.

**The four layers, in intentional priority order:**

1. **IH-35 line** (ON) — pink line, visual context, drawn first
2. **Real billboards** (ON) — red dots, THE STAR, with rich popups
3. **POI advertisers** (ON) — blue small dots, demand signal
4. **AADT stations** (OFF) — big blue circles, advanced only

**Every billboard popup contains three verification links** (per your
request):

```
1. TxDOT map viewer link — opens the official map zoomed to this pin
2. TxDOT Commercial Signs program page — for context on the program
3. Raw permit ID displayed for manual search
```

An operator can click any of these to independently verify the data.
That's the difference between a demo and a product.

---

### SECTION F — Summary

**Cell F.1 — Print what we proved**
Reports counts, market intelligence, and file listing.

Also prints the "next steps" that require chapters beyond Ch4:
- Ch6+ for automated candidate ranking (spatial joins)
- Ch7 for detecting billboards in aerial imagery
- Ch8 for revenue prediction
- Ch14 for the LangGraph agent

This tells your future self exactly which chapters unlock which
product upgrades.

---

## FIX LOG (from earlier iterations — kept for reference)

Prior versions of this notebook used advanced techniques and hit these
problems. The current Ch4-only rewrite AVOIDS all of them by not using
the offending techniques:

### FIX #1 — Wrong AADT dataset (max = 30,365)
**Old symptom:** Traffic values capped at 30K, missing IH-35 mainlane.
**Old cause:** Used `TxDOT_5_Year_Statewide_AADT_Traffic_Counts`.
**Now:** Uses `TxDOT_AADT_Annuals_(Public_View)` (correct dataset, top
McLennan station = 137,451 AADT on IH-35).

### FIX #2 — Numeric fields as string dtype
**Old symptom:** `TypeError: dtype object, cannot use nlargest`.
**Old cause:** ArcGIS returns integers as JSON strings sometimes.
**Now:** Cell D.1 forces `pd.to_numeric(col, errors='coerce')` on all
AADT columns before use.

### FIX #3 — Only 4 candidates → blank map
**Old symptom:** Map appeared empty because there were only 4 tiny dots.
**Old cause:** Cache-based loader accepted any file that existed.
**Now:** Not applicable — this notebook doesn't generate candidate
points. When you learn spatial joins in later chapters, we'll do this
properly.

### FIX #4 — Map didn't auto-zoom
**Old symptom:** Map opened somewhere with no data visible.
**Old cause:** `folium.Map` uses fixed center, no auto-fit.
**Now:** Center is computed from actual billboard bounds. For the
Ch4-only notebook this is enough because the study area is a small
bounding box we already control.

### FIX #5 — Notebook file too big
**Old symptom:** File grew to 874 KB from embedded Folium outputs.
**Old cause:** Multiple runs accumulated map HTML in cell outputs.
**Now:** Rebuild script strips outputs. File is now 32 KB clean.

### FIX #6 — Column name mismatch across datasets
**Old symptom:** `KeyError: 'LATEST_AADT_YR' not in index`.
**Old cause:** Two AADT datasets use different column names.
**Now:** Only need `AADT_RPT_QTY` for the popup; year column is not
required.

### FIX #7 — Candidates in a straight line, not the curved highway
**Old symptom:** Candidate dots formed a diagonal, missing IH-35.
**Old cause:** Naive `linspace()` between bbox corners.
**Now:** Not applicable — no candidate generation in Ch4-only version.
Deferred to when you've learned the chapters that cover it properly.

**The design principle:** Rather than hack around problems with
techniques you don't understand yet, drop the problematic features and
add them back when the corresponding chapter has been studied.

---

## OOHSCOUT TRANSLATION TABLE

| This notebook | Future OOHScout system |
|---------------|-----------------------|
| `fetch_txdot()` helper | Scheduled sync job into PostGIS `billboards` table |
| `TXDOT_BILLBOARDS_URL` query | Daily refresh via TxDOT ArcGIS feed |
| `ih35_bb['OWNR'].value_counts()` | Market intelligence dashboard |
| Folium map with FeatureGroups | MapLibre GL in React frontend |
| `verify_url` in popup | "Prove it" button in operator UI |
| Manual toggle for AADT | User preferences in FastAPI |

---

## RUNNING THIS NOTEBOOK — CHECKLIST

1. **Restart kernel** (Kernel → Restart & Clear Output)
2. **Kernel → Restart & Run All**
3. First run downloads ~200 KB of data from OSM + TxDOT (~30 seconds)
4. Cell E.1 prints a file path like:
   ```
   file:///.../data/new_study/ch4_waco_billboards_map.html
   ```
5. Copy that path into your browser to see the map (more reliable than
   Jupyter's inline preview)

**Expected map:**
- Waco-centered view
- Pink IH-35 line running through the middle
- ~114 red billboard dots on and near IH-35, each clickable
- Small blue POI dots for fuel stations, restaurants, hotels, etc.
- AADT layer OFF by default — toggle in top-right control to enable

**Expected popup on any billboard:**
- Real permit ID in monospace font
- Real operator name (Lamar / Reagan / Outfront / etc.)
- Digital/Static classification
- Three verification links

---

## FILES PRODUCED

```
notebooks/data/new_study/
    ch4_txdot_billboards_mclennan.geojson   ← 182 real permits (~50 KB)
    ch4_osm_pois_waco.geojson               ← POI advertiser demand
    ch4_osm_ih35_waco.geojson               ← IH-35 road geometry
    ch4_txdot_aadt_mclennan.geojson         ← AADT (optional layer)
    ch4_waco_billboards_map.html            ← The interactive map (THE DELIVERABLE)
```

All files are prefixed `ch4_` so they don't collide with earlier attempts.

---

## HOW THIS DIFFERS FROM THE PREVIOUS VERSION

| Aspect | Old version | Ch4-only version |
|--------|-------------|------------------|
| Spatial join to nearest billboard | Yes (unclear code) | No — deferred |
| Weighted scoring | Yes (V2 formula) | No — deferred |
| Legal exclusion zones (buffer) | Yes (500ft/1500ft) | No — deferred |
| Candidate zones along corridor | Yes (broken straight line) | No — deferred |
| Billboards visible on map | Overwhelmed by AADT circles | STAR of the show |
| AADT layer | On by default | Off by default |
| Verification links per billboard | None | Three per popup |
| Techniques from chapters not yet studied | Many | Zero |
| Notebook file size | 874 KB (bloated) | 32 KB (clean) |
| Cells | 37 | 17 |

The Ch4-only version does LESS, but everything it does is correct and
you understand every line.

---

## VERSION HISTORY

**v5 (current)** — 2026-08-28 — Chapter 4 only rewrite:
  - Removed all sjoin_nearest, buffer, linemerge, interpolate, weighted
    scoring code
  - Made billboards the star of the map with rich popups
  - Added three verification links per billboard
  - Made AADT layer hidden by default
  - Every technique now traceable to Ch4

**v4** — 2026-08-28 — Candidates follow curved highway (later reverted)
**v3** — 2026-08-28 — `pick_year_col()` helper for AADT column names
**v2** — 2026-08-28 — Switched to correct AADT dataset
**v1** — 2026-08-28 — Initial with wrong AADT dataset

---

*Last updated: 2026-08-28*
