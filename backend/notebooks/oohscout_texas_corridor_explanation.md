# OOHScout AI — Texas Corridor Analysis: Line-by-Line Explanation
# File: oohscout_texas_corridor.ipynb

This file explains every line of the Texas corridor notebook, WHY each piece exists,
how it connects to the next step, and — most importantly — what it means for OOHScout
as a real product you are trying to sell.

**Notebook purpose:** Phase 1 corridor prototype. Take a real Texas highway corridor,
automatically find and rank candidate billboard sites using open data, and produce
a deliverable (map + ranked table) that you could show to an operator TODAY.

---

## THE FULL PIPELINE (big picture first)

```
═══════════════════════════════════════════════════════════════════════════════

  INPUT: "Analyze IH-35 from Hillsboro to Waco, Texas"
         ↓
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  SETUP                                                                  │
  │  DATA_DIR, BBOX_CORRIDOR, CRS, weights, tag lists                      │
  └────────────────────────────┬────────────────────────────────────────────┘
                               ↓
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  STEP 1 — Road Geometry                                                 │
  │  OSMnx → IH-35 line features → filtered to motorway class              │
  │  Saved: ih35_waco_roads.geojson                                         │
  └────────────────────────────┬────────────────────────────────────────────┘
                               ↓
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  STEP 2 — Corridor Buffer                                               │
  │  IH-35 line → unary_union → .buffer(500m) → search zone polygon        │
  │  Saved: ih35_waco_buffer.geojson                                        │
  └────────────────────────────┬────────────────────────────────────────────┘
                               ↓
  ┌─────────────┬──────────────┴────────────────┐
  │             │                               │
  ↓             ↓                               ↓
STEP 3        STEP 4                        STEP 5
  POIs       Land Use                      Buildings
  (demand)   (zoning)                    (obstruction)
  ↓             ↓                               ↓
  └─────────────┴───────────────────────────────┘
                               ↓
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  STEP 6 — Candidate Zone Generation                                     │
  │  IH-35 line → sample every 1000m → N candidate points                  │
  └────────────────────────────┬────────────────────────────────────────────┘
                               ↓
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  STEP 7 — Feature Engineering                                           │
  │  For each candidate: count POIs within 500m, check commercial LU,      │
  │  count buildings within 200m, assign road class score                  │
  └────────────────────────────┬────────────────────────────────────────────┘
                               ↓
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  STEP 8 — Opportunity Score V0.1                                        │
  │  Normalize features → weighted sum → rank all candidates               │
  │  Saved: ih35_waco_candidates.geojson, ih35_waco_candidates_report.csv  │
  └────────────────────────────┬────────────────────────────────────────────┘
                               ↓
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  STEP 9 — Folium Interactive Map                                        │
  │  All layers → toggleable web map                                        │
  │  Saved: ih35_waco_oohscout_map.html                                     │
  └────────────────────────────┬────────────────────────────────────────────┘
                               ↓
  OUTPUT: Ranked candidate table + clickable map
          → Show to operator → Do they agree with the top 10?
          → This IS the first sellable deliverable

═══════════════════════════════════════════════════════════════════════════════
```

---

## SECTION 1 — SETUP

### Imports

```python
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from shapely.geometry import box, Point
from shapely.ops import unary_union, linemerge
import warnings
warnings.filterwarnings('ignore')
```

Every library serves a specific role in the OOHScout pipeline:

| Library | Role in this notebook |
|---------|----------------------|
| `numpy` | Array math for scoring (normalize, weighted sum) |
| `pandas` | Tabular data: candidates table, ranking, CSV export |
| `geopandas` | All vector data: roads, POIs, land use, candidates |
| `osmnx` | Downloads roads, POIs, land use, buildings from OpenStreetMap |
| `folium` | Builds the interactive HTML map (the deliverable) |
| `matplotlib` | Score distribution plots (sanity checks) |
| `shapely.geometry.box` | Creates a rectangular polygon from [W,S,E,N] coords |
| `shapely.ops.unary_union` | Merges many road segments into one geometry |
| `shapely.ops.linemerge` | Connects touching line segments into one continuous line |
| `pathlib.Path` | Safe, cross-platform file path handling |

---

### DATA_DIR

```python
DATA_DIR = Path('data/new_study')
DATA_DIR.mkdir(parents=True, exist_ok=True)
```

`Path('data/new_study')` — same rule as ALL notebooks. Relative to `notebooks/`.
`mkdir(parents=True, exist_ok=True)` — create if missing; don't crash if already there.
All saved files go here: GeoJSON, HTML map, CSV report.

---

### Corridor Definition

```python
BBOX_CORRIDOR = [-97.25, 31.40, -96.95, 31.80]
```

The bounding box for the IH-35 Waco corridor: [West, South, East, North] in WGS84 degrees.
This covers roughly Hillsboro → Waco — about 25 miles of one of Texas's busiest interstates.

**Why this corridor?**
- McLennan County is a single jurisdiction → Phase 3 only needs ONE set of regulations
- IH-35 has ~60,000–80,000 AADT (annual average daily traffic) → high-demand billboard corridor
- Mix of commercial, farmland, and urban zones → interesting candidate diversity
- Waco's growth means rising billboard rates → real operator interest

```
  [-97.25, 31.40]         [-96.95, 31.40]
  (SW corner)             (SE corner)
       ┌───────────────────────┐
       │       BBOX            │
       │   IH-35 runs through  │
       │   roughly N-S here    │
       │                       │
  [-97.25, 31.80]         [-96.95, 31.80]
  (NW corner)             (NE corner)
```

---

### Coordinate Systems

```python
WGS84   = 'EPSG:4326'
TEX_CRS = 'EPSG:32614'
```

`WGS84 (EPSG:4326)` — latitude/longitude in degrees. Used for:
- Storing all GeoJSON files (universal format)
- Displaying on web maps (Folium, MapLibre)
- OpenStreetMap downloads (always come in WGS84)

`TEX_CRS (EPSG:32614)` — UTM Zone 14N, Texas. Units are METERS. Used for:
- All distance calculations (buffer, radius, spacing)
- All area calculations (land use area in km²)
- Any measurement that must be accurate (degrees are NOT uniform in size)

**The rule:** download in WGS84, calculate in TEX_CRS, store in WGS84.

```
OOHScout CRS discipline:
  OSM download → WGS84
       ↓ .to_crs(TEX_CRS)
  Any distance/area math
       ↓ .to_crs(WGS84)
  Save to file / display
```

---

### Parameters

```python
CORRIDOR_BUFFER_M  = 500
CANDIDATE_INTERVAL_M = 1000
POI_RADIUS_M       = 500
LANDUSE_RADIUS_M   = 300
```

`CORRIDOR_BUFFER_M = 500` — How wide the search zone is. 500m each side = 1km total width.
Covers any parcel with road frontage while excluding distant backland.

`CANDIDATE_INTERVAL_M = 1000` — One candidate zone every 1km along IH-35.
A 25-mile corridor at 1km spacing = ~40 candidates. Enough to identify clusters; few enough to review.

`POI_RADIUS_M = 500` — Count POIs within 500m of each candidate.
500m ≈ 5-minute walk ≈ same retail trade area a billboard would serve.

`LANDUSE_RADIUS_M = 300` — Check for commercial land use within 300m.
Tighter than POI radius — a commercial zone that close almost certainly means commercial zoning.

---

### Opportunity Score Weights

```python
WEIGHTS = {
    'traffic_score':  0.30,
    'demand_score':   0.30,
    'landuse_score':  0.25,
    'spacing_score':  0.15,
}
```

These weights are **hypotheses**, not truths. They are V0.1 starting points.

| Factor | Weight | Why | Where the real data comes from |
|--------|--------|-----|-------------------------------|
| traffic_score | 30% | Traffic = eyeballs. No eyes = no value. | TxDOT STARS II AADT (Phase 4) |
| demand_score | 30% | Advertisers = revenue. POI density = demand proxy. | OSM POIs (NOW) → licensed data (Phase 4) |
| landuse_score | 25% | Wrong zone = permit denied. Commercial = better odds. | OSM LU (NOW) → real zoning GIS (Phase 3) |
| spacing_score | 15% | Too close to another board = permit denied or diluted value. | Permit records (Phase 4) |

**Weights will change.** When operators accept/reject candidates, you'll see which features predict good sites. That's the learning loop that builds the moat.

---

### POI Tag Definitions

```python
ADVERTISER_TAGS = {
    'amenity': ['fuel', 'restaurant', 'fast_food', 'cafe', 'hotel', 'bank', 'pharmacy', 'car_wash'],
    'shop':    ['supermarket', 'car_repair', 'auto_parts', 'convenience'],
    'tourism': ['hotel', 'motel'],
}
```

These are the OSM tag key-value pairs for billboard-relevant businesses.

`'amenity': ['fuel', ...]` — OSM tags fuel stations as `amenity=fuel`.
`'shop': ['car_repair', ...]` — auto services tagged differently from amenities.
`'tourism': ['hotel', ...]` — hotels appear in BOTH tourism and amenity tags in OSM.

**Why these categories?** These are the top billboard advertising spend categories in OOH:
1. Fuel/auto services (captive audience on highway)
2. Quick service restaurants (impulse decision + nearby)
3. Hotels/lodging (last-minute decision, high billboard ROI)
4. Financial services (banks, remittance)

---

## STEP 1 — IH-35 Road Geometry

### Product framing

The road is the foundation of everything. You cannot compute a buffer without the road line.
You cannot sample candidates without the road line. You cannot know the road class without
looking at the road's attributes. Everything downstream depends on getting this right.

### The cache pattern

```python
road_path = DATA_DIR / 'ih35_waco_roads.geojson'

if road_path.exists():
    roads = gpd.read_file(road_path)
    print(f'Loaded from cache: {road_path.name} — {len(roads)} segments')
else:
    ...download...
```

Same pattern as ALL Chapter 4 steps. Check file existence first.
- File exists → load (milliseconds, no internet needed)
- File missing → download from OSM, save for next run

**Use this pattern everywhere in OOHScout.** Data acquisition is the slow step.
Downloads that take 30 seconds today might take 3 minutes on a slow connection.
The cache ensures re-runs are instant.

### OSMnx download

```python
corridor_poly = box(*BBOX_CORRIDOR)

raw_roads = ox.features_from_polygon(
    corridor_poly,
    tags={'highway': ['motorway', 'motorway_link', 'trunk', 'primary']}
)
```

`box(*BBOX_CORRIDOR)` — unpacks [W, S, E, N] → creates a Shapely rectangle.
This is the geographic boundary for the OSM query.

`ox.features_from_polygon(polygon, tags={...})` — downloads all OSM features that:
1. Are INSIDE the polygon
2. Match the tags

`tags={'highway': ['motorway', 'motorway_link', 'trunk', 'primary']}` — OSM road hierarchy:
- `motorway` = Interstate (IH-35) — highest class
- `motorway_link` = on/off ramps of IH-35
- `trunk` = US Highways (US-84, US-77 nearby)
- `primary` = State highways (TX-6, TX-31 nearby)

We want all of these because:
- IH-35 itself = candidate corridor centerline
- Ramps = where the interchange clusters are (high-value billboard zones)
- Trunk/primary = secondary corridors worth noting as context

### Geometry filter

```python
roads = (
    raw_roads[raw_roads.geometry.geom_type.isin(['LineString', 'MultiLineString'])]
    .copy()
    .reset_index(drop=True)
)
```

OSMnx returns BOTH line features (road segments) AND point features (nodes, intersections).
We only want lines for corridor analysis. `.isin(['LineString', 'MultiLineString'])` keeps only lines.
`.copy()` prevents pandas SettingWithCopyWarning — always copy filtered subsets.
`.reset_index(drop=True)` gives clean 0-indexed row numbers after filtering.

### Motorway filter

```python
def is_motorway(h):
    if isinstance(h, list):
        return any('motorway' in str(v) for v in h)
    return 'motorway' in str(h)

ih35 = roads[roads['highway'].apply(is_motorway)].copy()
```

OSMnx sometimes returns `highway` as a Python list (when a segment has multiple tags)
and sometimes as a string. The `is_motorway` function handles both cases.
`if isinstance(h, list)` → check each element in the list.
`'motorway' in str(h)` → catches `'motorway'` and `'motorway_link'`.

**Why isolate IH-35?** It is THE corridor. Trunk and primary roads in the bbox
are context — useful for future network analysis, not for the candidate baseline.

### Metric calculation

```python
roads_tex = roads.to_crs(TEX_CRS)
total_km = roads_tex.geometry.length.sum() / 1000
```

`.to_crs(TEX_CRS)` — project to UTM Zone 14N (meters).
`.geometry.length` — compute length of each line segment in meters.
`.sum() / 1000` — sum and convert to kilometers.

**Never compute length in WGS84 degrees.** One degree of longitude at 31°N latitude
≠ one degree of longitude at the equator. Always project to meters first.

---

## STEP 2 — Corridor Buffer (The Search Zone)

### Product framing

The buffer answers: "Where should we LOOK for candidate sites?"
500m each side of IH-35 = a 1km wide ribbon running the length of the corridor.
Any parcel with road frontage falls inside this zone. Distant parcels that can't
see the highway don't matter — a billboard you can't see from the road is worthless.

### Geometry operations

```python
road_union_tex = unary_union(ih35_tex.geometry)
buffer_geom_tex = road_union_tex.buffer(CORRIDOR_BUFFER_M)
```

`unary_union(ih35_tex.geometry)` — merges all IH-35 line segments into ONE geometry.
Without this step, buffering each segment separately creates overlapping circles at every joint.
With union first, you get a single clean buffer polygon.

`.buffer(CORRIDOR_BUFFER_M)` — grows the geometry outward by 500 meters in all directions.
On a line, this creates a capsule/stadium shape running the length of the corridor.

```
Without unary_union:           With unary_union:
  ●───●───●───●               ════════════════════
  ↑   ↑   ↑   ↑         →    ────────────────────   (clean ribbon)
 overlapping circles          ════════════════════
```

### GeoDataFrame construction

```python
corridor_buffer_tex = gpd.GeoDataFrame(
    {
        'geometry':   [buffer_geom_tex],
        'corridor':   ['IH-35 Waco'],
        'state':      ['TX'],
        'county':     ['McLennan'],
        'buffer_m':   [CORRIDOR_BUFFER_M],
        'road_class': ['motorway'],
    },
    crs=TEX_CRS
)
```

Wrap the buffer geometry in a GeoDataFrame with metadata.
Every piece of metadata is a column — this is what flows into the `jurisdictions` and
`roads` tables in the future PostGIS database. The metadata tells downstream queries
WHICH corridor this buffer belongs to and what jurisdiction governs it.

### Save in WGS84

```python
corridor_buffer = corridor_buffer_tex.to_crs(WGS84)
corridor_buffer.to_file(buffer_path, driver='GeoJSON')
buffer_poly_wgs84 = corridor_buffer.geometry.iloc[0]
```

Convert back to WGS84 before saving — GeoJSON files always use WGS84 by convention.
`geometry.iloc[0]` — extract the single polygon as a Shapely geometry.
This is used as the clip polygon in ALL subsequent OSMnx downloads (Steps 3-5).

**The buffer polygon is the key.** Every call to `ox.features_from_polygon(buffer_poly_wgs84, ...)` 
in Steps 3-5 downloads data only WITHIN this corridor search zone — not the entire bbox.
This is both more accurate and more efficient.

---

## STEP 3 — POIs (Advertiser Demand Signal)

### Product framing

POIs are the heartbeat of advertiser demand. When you're siting a billboard, you want to know:
"Who on this corridor would actually pay for this ad space?"

A fuel station = captive audience, high repeat traffic, natural billboard advertiser.
A Whataburger = Texas's #1 fast food chain, buys outdoor advertising constantly.
A Holiday Inn Express = last-minute decision moment, billboard-driven bookings.

Dense POI clusters = natural commercial activity hubs = exactly where you want a billboard.

### Multi-tag download loop

```python
for tag_key, tag_values in ADVERTISER_TAGS.items():
    try:
        raw = ox.features_from_polygon(
            buffer_poly_wgs84,
            tags={tag_key: tag_values}
        )
        pts = raw[raw.geometry.geom_type == 'Point'].copy()
        ...
        all_pois.append(pts)
    except Exception as e:
        print(f'  {tag_key}: skipped — {e}')
```

We loop over three tag dictionaries (`amenity`, `shop`, `tourism`) because OSM tags
different business types differently. A hotel can be tagged as BOTH `amenity=hotel`
AND `tourism=hotel` depending on who mapped it. Querying all three catches them all.

`try/except` — if OSM has no features for a tag type in this area, don't crash.
Some rural corridors have no `shop=car_repair` in OSM — that's fine, just skip it.

### Point-only filter

```python
pts = raw[raw.geometry.geom_type == 'Point'].copy()
```

OSM POIs can be mapped as:
- Points (centroid) → what we want for distance calculations
- Polygons (building footprint) → also valid but complicates counting
- Relations → complex multi-polygon objects

For counting "how many POIs near this candidate," points are easiest.
A polygon POI's centroid is effectively its point for our purpose.
Step 7's `count_within()` uses `.intersects(circle)` which works with polygons too,
but keeping points only keeps the logic clean.

### Concatenation

```python
pois = pd.concat(all_pois, ignore_index=True)
pois = pois[pois.geometry.is_valid].copy().reset_index(drop=True)
```

`pd.concat(all_pois, ignore_index=True)` — stacks all three tag-type lists into one DataFrame.
`ignore_index=True` resets row numbers (each sub-list had its own 0-indexed numbers).
`pois.geometry.is_valid` — removes geometrically invalid features (rare but can happen in OSM).

---

## STEP 4 — Land Use (Zoning Proxy)

### Product framing

Real zoning data (from a municipal GIS portal) is the gold standard for Phase 3.
For Phase 1, OSM land use is the best free proxy available.

The key insight: Billboard regulations are almost always ZONE-BASED.
- Commercial zones: typically permitted with setback and height rules
- Residential zones: typically prohibited or extremely restricted
- Agricultural/rural: varies widely by state law and local ordinance

When you see `landuse=commercial` within 300m of your candidate, you're likely
looking at a commercially-zoned area. That's a positive signal for permit odds.

### Rare class removal

```python
vc   = landuse['landuse'].value_counts()
keep = vc[vc >= 3].index.tolist()
landuse = landuse[landuse['landuse'].isin(keep)].copy()
```

Same pattern as Chapter 4's Hungary land use step.
A land use class with only 1-2 polygons in the corridor is too rare to be meaningful.
These might be mapping errors or truly unique edge cases.
Removing them keeps the feature set clean and prevents rare-class bias in scoring.

### Area calculation

```python
lu_tex = landuse.to_crs(TEX_CRS)
lu_tex['area_m2'] = lu_tex.geometry.area
```

Area MUST be computed in meters CRS (TEX_CRS).
`.geometry.area` in WGS84 returns values in DEGREES SQUARED — meaningless.
In UTM meters, `.geometry.area` returns square meters — meaningful.

---

## STEP 5 — Buildings (Obstruction Proxy)

### Product framing

A building directly between IH-35 traffic and a proposed billboard location
can block sightlines. Dense building clusters = urban environment = potential obstruction.

For Phase 1, building COUNT within 200m is a rough proxy.
For Phase 5, we replace this with LiDAR nDSM (height above ground) — exactly what
Chapter 5 of the GeoAI book taught us. The Chapter 5 technique maps directly here:
"Which buildings and trees block the sightline from the road to the sign face?"

Building COUNT also gives a second signal: many buildings = active commercial area = demand.
Large individual buildings (warehouse, Walmart) = anchor tenants = high-demand billboard zone.

### Optional column handling

```python
keep_cols = ['geometry']
for col in ['building', 'height', 'levels']:
    if col in buildings.columns:
        keep_cols.append(col)
```

OSM `height` and `levels` data is sparse. Most buildings in Texas don't have
height/levels recorded in OSM. Rather than crashing, we keep these columns ONLY
if they exist. In Phase 5, TxDOT LiDAR replaces OSM height with actual measurements.

---

## STEP 6 — Candidate Zone Generation

### Product framing

This step answers: "Where exactly should I evaluate on this 25-mile corridor?"

We can't evaluate every square meter. We also can't pick locations randomly.
The solution: sample one candidate point every 1km along the road centerline.
This gives ~25-40 candidates — enough to cover the corridor, few enough to review.

Each candidate point represents a zone of influence: a circle of radius equal to the
minimum spacing requirement. If this zone overlaps with a competitor board, the
candidate gets penalized in the spacing score.

### build_master_line

```python
def build_master_line(road_gdf, crs_meters):
    road_tex = road_gdf.to_crs(crs_meters)
    union    = unary_union(road_tex.geometry)

    if union.geom_type == 'MultiLineString':
        merged = linemerge(union)
        if merged.geom_type == 'LineString':
            return merged
        return max(union.geoms, key=lambda g: g.length)
    return union
```

`unary_union` combines all IH-35 segments into one geometry.
The result is usually a `MultiLineString` (many disconnected segments).

`linemerge(union)` — attempts to merge touching segments into a single `LineString`.
This works when segments are connected end-to-end (which IH-35 segments usually are).
If `linemerge` still returns a `MultiLineString`, take the longest piece — that's the
main corridor. Short pieces are usually service roads or ramps.

**Why we need ONE line:** `line.interpolate(d)` (used in `sample_along_line`) only
works on a single `LineString`. You can't interpolate along a `MultiLineString` directly.

### sample_along_line

```python
def sample_along_line(line_geom, interval_m):
    total  = line_geom.length
    dists  = np.arange(0, total, interval_m)
    return [line_geom.interpolate(d) for d in dists]
```

`line_geom.length` — total length of the line in meters (in TEX_CRS).
`np.arange(0, total, interval_m)` — creates an array: [0, 1000, 2000, 3000, ...].
`line_geom.interpolate(d)` — returns the Point at distance `d` meters along the line.

```
Corridor (25km):  0m ── 1000m ── 2000m ── ... ── 25000m
Candidates:       ●      ●        ●              ●
                 WA-000  WA-001   WA-002        WA-024
```

### Candidate GeoDataFrame

```python
candidates = gpd.GeoDataFrame(
    {
        'geometry':       candidate_pts_tex,
        'candidate_id':   [f'WA-{i:03d}' for i in range(len(candidate_pts_tex))],
        'corridor':       'IH-35 Waco',
        'road_class':     'motorway',
        'dist_along_km':  [i * CANDIDATE_INTERVAL_M / 1000 for i in range(...)],
    },
    crs=TEX_CRS
)
```

`candidate_id = f'WA-{i:03d}'` — "WA" = Waco, zero-padded 3 digits.
WA-000, WA-001, ... WA-039 — this IS the OOHScout site reference number.
In the real system, this becomes the primary key in the `candidate_sites` table.

`dist_along_km` — how far along the corridor this candidate sits.
If an operator says "the site near the I-35/Loop 340 interchange" you can look up
which WA-XXX ID corresponds to that kilometer mark.

---

## STEP 7 — Feature Engineering

### Product framing

This is where raw geographic data becomes signals an operator would recognize.

An experienced billboard developer walks a corridor and mentally notes:
- "That interchange has three gas stations and a McDonald's — strong demand"
- "That stretch is all farmland — low demand but could capture rural boards"
- "That strip mall cluster — obviously commercial zoning, good permit odds"

Feature engineering automates this mental process at scale.

### The geometry

```python
pois_tex      = pois.to_crs(TEX_CRS)
landuse_tex   = landuse.to_crs(TEX_CRS)
buildings_tex = buildings.to_crs(TEX_CRS)
```

ALL data is projected to TEX_CRS before any distance calculation.
This is the most important rule in geospatial analysis.
If you forget this, `count_within` will count features "within 500 degrees" — meaningless.

### count_within

```python
def count_within(candidate_geom, feature_gdf, radius_m):
    circle = candidate_geom.buffer(radius_m)
    return int(feature_gdf.geometry.intersects(circle).sum())
```

`candidate_geom.buffer(radius_m)` — creates a circle of radius_m around the candidate point.
`feature_gdf.geometry.intersects(circle)` — boolean Series: True for each POI inside the circle.
`.sum()` — count how many Trues (= how many POIs inside the circle).

```
Candidate point ●  (in TEX_CRS meters)
Buffer circle   ○  radius = 500m

POIs inside ○ → contribute to poi_count_500m
POIs outside → ignored
```

This is a SPATIAL JOIN without calling `.sjoin()`. For counting, it's faster to
iterate over candidates and use `.intersects()` than to do a full spatial join.
When candidates number in the thousands (future corridors), switch to PostGIS ST_DWithin.

### any_within

```python
def any_within(candidate_geom, feature_gdf, radius_m):
    circle = candidate_geom.buffer(radius_m)
    return int(feature_gdf.geometry.intersects(circle).any())
```

Same as `count_within` but returns 1 (True) or 0 (False).
Used for `commercial_nearby` — we don't need to know HOW MANY commercial polygons,
just WHETHER commercial land use exists within 300m.
Binary signals are simpler to score and easier to explain to an operator.

### road_class_score

```python
candidates_tex['road_class_score'] = 1.0
```

All candidates are on IH-35 (motorway) → all get road_class_score = 1.0.
In Phase 4, when we have TxDOT AADT data, this becomes:
`road_class_score = normalize(aadt)` — a 100,000 AADT site scores higher than 40,000.
For now, the constant 1.0 reflects that IH-35 is always the highest road class.

---

## STEP 8 — Opportunity Score V0.1

### Product framing

The score collapses all features into one number so an operator can say
"show me the top 10." Without a score, you'd have to compare every feature
manually across 40 candidates — impossible to prioritize.

The score is TRANSPARENT. Every factor is shown. An operator can ask
"why is WA-015 ranked #1?" and you point to: highest POI count, commercial zone,
motorway. If they disagree with the ranking, THAT IS VALUABLE FEEDBACK.
Their disagreement tells you which weights to adjust.

### normalize()

```python
def normalize(series):
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - lo) / (hi - lo)
```

Min-max normalization: maps any range to [0.0, 1.0].
- The candidate with the MOST POIs gets demand_score = 1.0
- The candidate with the FEWEST POIs gets demand_score = 0.0
- All others fall proportionally between 0 and 1

`if hi == lo` → if ALL candidates have the same value (e.g., all zeros), return zeros.
Without this guard, you'd divide by zero → NaN → the entire score column becomes NaN.

### Regulatory gate (non-negotiable)

```python
candidates_tex['reg_status'] = 'PENDING_REVIEW'
```

**This is one of the most important lines in the notebook.**

The regulatory gate is NOT a scored factor. It is a HARD GATE:
- PASS → site is eligible (passed automated preliminary screening)
- FAIL → site is eliminated, regardless of how high the opportunity score is
- PENDING_REVIEW → Phase 3 hasn't run yet — don't show this site to operators yet

You NEVER label a site "LEGAL." You say "passed automated preliminary screening;
final eligibility requires municipal verification." This is OOHScout's core
liability protection and the reason operators will trust the product over a chatbot.

### Weighted sum

```python
candidates_tex['opportunity_score'] = (
    WEIGHTS['traffic_score']   * candidates_tex['traffic_score']
    + WEIGHTS['demand_score']  * candidates_tex['demand_score']
    + WEIGHTS['landuse_score'] * candidates_tex['landuse_score']
    + WEIGHTS['spacing_score'] * candidates_tex['spacing_score']
)
```

Each factor is multiplied by its weight, then summed.
Since all factors are normalized to [0,1] and weights sum to 1.0,
the result is always in [0.0, 1.0].

```
traffic_score  × 0.30  =  0.30 × 1.0   = 0.30   (motorway always 1.0)
demand_score   × 0.30  =  0.30 × 0.80  = 0.24   (this site has 80% of max POIs)
landuse_score  × 0.25  =  0.25 × 1.0   = 0.25   (commercial land use found)
spacing_score  × 0.15  =  0.15 × 1.0   = 0.15   (no competitor boards yet)
──────────────────────────────────────────────────
opportunity_score                       = 0.94   (very high — top candidate)
```

### Ranking

```python
candidates_tex['rank'] = (
    candidates_tex['opportunity_score']
    .rank(ascending=False, method='first')
    .astype(int)
)
```

`rank(ascending=False)` — highest score gets rank 1.
`method='first'` — ties are broken by first occurrence (not random).
`.astype(int)` — convert from float (1.0) to integer (1) for display.

---

## STEP 9 — Folium Interactive Map

### Product framing

The map IS the product for Phase 1. It's what you show an operator at a meeting.
"Here's IH-35. The green dots are the sites our algorithm ranked highest. Click any
dot to see why — POI count, land use, score. The red road is IH-35 itself."

A map immediately answers "does the algorithm make sense?" in a way a table cannot.
If the top-ranked site is in the middle of a field with no amenities, the operator
will tell you instantly. That feedback is worth more than a code review.

### Map structure

```python
fmap = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=11,
    tiles='CartoDB positron'
)
```

`location` = [lat, lon] center point (NOT [lon, lat] — Folium uses lat/lon order).
`zoom_start=11` = country-level zoom → city visible; individual buildings not yet.
`CartoDB positron` = minimal light-gray basemap. Doesn't compete visually with our overlays.

### Layer 1: Buffer

```python
folium.GeoJson(
    corridor_buffer.__geo_interface__,
    name='IH-35 Search Zone (500m buffer)',
    style_function=lambda x: {
        'fillColor': '#FFA500', 'color': '#FF6600',
        'weight': 2, 'fillOpacity': 0.08,
    },
).add_to(fmap)
```

`__geo_interface__` — converts GeoDataFrame to GeoJSON dict that Folium can render.
`fillOpacity: 0.08` — very light fill so the basemap is visible through it.
The orange buffer shows the operator exactly where we searched.

### Layer 5: Candidate zones (color-coded by rank)

```python
color  = '#00BB44' if is_top else '#FFAA00'
radius = 12 if is_top else 7
```

Top 10 candidates: large green circles.
Others: smaller orange circles.
This immediately directs the operator's eye to the priority sites.

```python
popup_html = (
    f"<b>{row['candidate_id']}</b><br>"
    f"Rank: #{row['rank']}<br>"
    f"Score: {row['opportunity_score']:.3f}<br>"
    ...
)
```

Every popup shows the EVIDENCE for the score — not just the number.
"POIs (500m): 12" tells the operator what's driving the score.
"Commercial nearby: Yes" tells them the zoning looks right.
Transparent scoring = operator trust = product credibility.

### FeatureGroup pattern

```python
lu_layer = folium.FeatureGroup(name='Land Use (zoning proxy)', show=True)
for _, row in landuse.iterrows():
    ...
    folium.GeoJson(...).add_to(lu_layer)
lu_layer.add_to(fmap)
```

`FeatureGroup` groups multiple features under one toggle in the LayerControl panel.
Without this, every land use polygon would be a separate toggle — unusable.
With it, the operator toggles ALL land use on/off with one click.

### Saving the map

```python
map_path = DATA_DIR / 'ih35_waco_oohscout_map.html'
fmap.save(str(map_path))
```

The HTML file is fully self-contained — no server needed.
Email it to an operator, open in Chrome, zoom in, click dots. That's the deliverable.

---

## STEP 10 — Final Report Table

### Product framing

The operator meeting flow:
1. Open the Folium HTML map → visual overview
2. Look at the ranked table → know the top IDs by name
3. Open the CSV → sort, filter, share with team

The CSV is the "leave-behind" — what they take after the meeting.
The `candidate_id` (WA-000, WA-015, etc.) is the reference used in all future
conversations: "Can we add WA-015 to the acquisition pipeline?"

---

## HOW EVERYTHING CONNECTS

```
OSM (free, no API key)
    │
    ├─ ox.features_from_polygon(corridor_poly, tags={'highway':...})
    │   → roads GeoDataFrame → ih35 (motorway filter) → ih35_waco_roads.geojson
    │
    ├─ ox.features_from_polygon(buffer_poly, tags={'amenity':...})
    │   → pois GeoDataFrame → ih35_waco_pois.geojson
    │
    ├─ ox.features_from_polygon(buffer_poly, tags={'landuse': True})
    │   → landuse GeoDataFrame → ih35_waco_landuse.geojson
    │
    └─ ox.features_from_polygon(buffer_poly, tags={'building': True})
        → buildings GeoDataFrame → ih35_waco_buildings.geojson

Shapely
    │
    ├─ box(*BBOX_CORRIDOR) → corridor query polygon
    ├─ unary_union(ih35 lines) → single IH-35 geometry
    ├─ .buffer(500) → corridor_buffer → search zone → ih35_waco_buffer.geojson
    └─ .interpolate(d) → N candidate points every 1000m

GeoPandas
    │
    ├─ .to_crs(TEX_CRS) → convert to meters for ALL calculations
    ├─ .buffer(radius) → search circle for each candidate
    ├─ .intersects(circle) → spatial proximity check
    └─ .to_crs(WGS84) → convert back for storage/display

Pandas + NumPy
    │
    ├─ normalize(poi_count) → demand_score [0, 1]
    ├─ weighted sum → opportunity_score [0, 1]
    └─ .rank(ascending=False) → rank 1–N

Folium
    │
    ├─ folium.Map → basemap
    ├─ folium.GeoJson → buffer, roads, land use layers
    ├─ folium.CircleMarker → POIs, candidate zones
    ├─ folium.Popup → click-for-details per candidate
    └─ .save() → ih35_waco_oohscout_map.html (the deliverable)
```

---

## OOHSCOUT TRANSLATION TABLE

| This notebook | Future OOHScout system |
|---------------|----------------------|
| `BBOX_CORRIDOR` | User inputs corridor name → system resolves to bbox |
| `ih35_waco_roads.geojson` | `road_segments` table in PostGIS |
| `corridor_buffer` | `corridors` table with buffer geometry |
| `pois` | `business_pois` table (OSM + licensed enrichment) |
| `landuse` | `zoning` table (OSM → Phase 3: real municipal zoning) |
| `buildings` | `parcels` table (Phase 2: county parcel data) |
| `candidate_id = 'WA-XXX'` | `candidate_sites.site_id` — the primary key |
| `count_within(geom, pois, 500)` | PostGIS: `ST_DWithin(candidate.geom, poi.geom, 500)` |
| `reg_status = 'PENDING_REVIEW'` | Regulatory gate — Phase 3 RAG fills this in |
| `opportunity_score` | `site_scores.opportunity_score` in the database |
| `ih35_waco_oohscout_map.html` | MapLibre GL embedded in React/Next.js frontend |
| `ih35_waco_candidates_report.csv` | FastAPI `/corridor/{id}/report` endpoint |

---

## KEY PATTERNS TO REMEMBER

### 1. Always use cache pattern for downloads

```python
path = DATA_DIR / 'my_data.geojson'
if path.exists():
    data = gpd.read_file(path)
else:
    data = ox.features_from_polygon(...)
    data.to_file(path, driver='GeoJSON')
```

### 2. Always project to TEX_CRS before any measurement

```python
data_tex = data.to_crs('EPSG:32614')
distances = data_tex.geometry.distance(point)   # now in meters
areas     = data_tex.geometry.area              # now in square meters
```

### 3. Always convert back to WGS84 before saving

```python
data.to_crs('EPSG:4326').to_file(path, driver='GeoJSON')
```

### 4. Regulatory gate is NOT a score factor

```python
# WRONG — don't do this:
score = 0.4 * traffic + 0.3 * demand + 0.3 * legal_probability

# RIGHT — regulatory is a GATE:
reg_status = 'PASS' | 'FAIL' | 'PENDING_REVIEW'
if reg_status == 'FAIL':
    eliminate_candidate()   # score doesn't matter
else:
    score = weighted_sum(features)
```

### 5. normalize() before weighted sum

```python
score = sum(weight * normalize(feature) for weight, feature in factors)
```

Without normalization, a feature with range [0, 10000] (AADT) would dominate
a feature with range [0, 1] (binary commercial flag) regardless of weights.

### 6. linemerge before interpolate

```python
merged = linemerge(unary_union(road_gdf.geometry))   # connect segments
pts = [merged.interpolate(d) for d in dists]         # then sample
```

---

## FILES PRODUCED BY THIS NOTEBOOK

```
notebooks/data/new_study/
    ih35_waco_roads.geojson          ← IH-35 road segments (all highway classes)
    ih35_waco_buffer.geojson         ← 500m search zone polygon
    ih35_waco_pois.geojson           ← advertiser-relevant POIs
    ih35_waco_landuse.geojson        ← land use polygons (zoning proxy)
    ih35_waco_buildings.geojson      ← building footprints (obstruction proxy)
    ih35_waco_candidates.geojson     ← N candidate zones with all features + score
    ih35_waco_candidates_report.csv  ← ranked table (the leave-behind)
    ih35_waco_oohscout_map.html      ← interactive map (the deliverable)
```

---

## WHAT COMES NEXT (Phase 2 → 6)

```
Phase 1 (THIS NOTEBOOK):
  Open data (OSM) → GeoPandas → ranked table + Folium map
  Status: COMPLETE with this notebook

Phase 2:
  Load candidates into PostGIS
  Run spatial queries in SQL: ST_DWithin, ST_Buffer, ST_Intersection
  Replace Python loops with PostGIS indexed spatial operations

Phase 3:
  Regulatory RAG: ingest Waco city code + Texas DOT outdoor advertising rules
  For each candidate: ask RAG "is this zone permitted for a new billboard?"
  reg_status changes from PENDING_REVIEW → PASS / FAIL / REVIEW

Phase 4:
  Join TxDOT STARS II AADT traffic counts to each candidate
  traffic_score = normalize(aadt) instead of constant 1.0
  Add competition gap: download existing permitted billboard locations

Phase 5:
  Add LiDAR nDSM visibility analysis (Chapter 5 techniques apply here)
  For each candidate: max nDSM height within sightline = obstruction score

Phase 6:
  Show the ranked list to a real Waco operator
  Do they agree the top 10 sites are worth investigating?
  One "yes, I'd investigate WA-015" = Phase 1 validated
  One payment for a second corridor = commercial milestone hit
```

---

*File generated for oohscout_texas_corridor.ipynb*
*Last updated: 2026-08-28*
*OOHScout AI — Phase 1 Corridor Prototype*
