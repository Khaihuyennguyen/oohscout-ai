# UA Advanced Chapter 1 — Milan Original: Complete Line-by-Line Explanation

**Chapter:** *Urban Analytics with Python — Advanced Methods*, Chapter 1: Introduction & Setting Up
**Author:** Dr. Milan Janosov
**Companion Retype Notebook:** `01_milan_original.ipynb`
**Purpose:** Comprehensive line-by-line guide explaining the **Why** and **How** behind every cell, function, parameter choice, and data structure in Chapter 1.

---

## Table of Contents
1. [Core Mental Model & Spatial Philosophy](#1-core-mental-model--spatial-philosophy)
2. [OOHScout Translation Table](#2-oohscout-translation-table)
3. [Section 1.1 — Environment & Package Imports](#3-section-11--environment--package-imports)
4. [Section 1.2 — The Retargetable Study-Area Pattern](#4-section-12--the-retargetable-study-area-pattern)
5. [Section 1.3 — Base Geometries (Building Footprints)](#5-section-13--base-geometries-building-footprints)
6. [Section 1.4 — Fast Test Bounding Box (DEV_MODE)](#6-section-14--fast-test-bounding-box-dev_mode)
7. [Key Gotchas & Defensive Spatial Engineering](#7-key-gotchas--defensive-spatial-engineering)

---

## 1. Core Mental Model & Spatial Philosophy

Chapter 1 establishes the foundational scaffolding for the entire course. Everything downstream depends on three strict disciplines:

1. **The Single-Configuration Pattern:** A single block at the top defines `PLACE`, `CRS_METRIC`, and `CRS_GEOGRAPHIC`. Modifying this single block retargets all downstream data pipelines, analysis, and models to any city or county in the world.
2. **Metric vs. Geographic Coordinate Discipline:**
   - **EPSG:4326 (WGS 84):** Represents coordinates in angular degrees (latitude / longitude). Calculating distances, buffers, or polygon areas in degrees yields mathematically invalid results because degrees do not represent fixed lengths on the curved Earth.
   - **Projected UTM Metric CRS (e.g., EPSG:32618 for NYC, EPSG:32614 for Central Texas):** Flattens the Earth onto a 2D Euclidean plane where units are strictly in **meters**. All buffers, distances, and area calculations must happen in this system.
3. **Immutability of Base Geometries:**
   - Raw geometries are fetched once from OpenStreetMap (OSM), cleaned, and saved to disk.
   - Downstream chapters reload this base layer as read-only geometry and save their derived features to separate files rather than mutating the original file.

---

## 2. OOHScout Translation Table

How Milan's course concepts map 1-to-1 to OOHScout AI:

| Concept | Milan Janosov (Course Original) | OOHScout AI (Feature 1 Adaptation) | Why We Made This Choice |
| :--- | :--- | :--- | :--- |
| **Study Area (`PLACE`)** | `"Manhattan, New York"` | `"McLennan County, Texas"` | OOHScout's MVP is strictly scoped to McLennan County (Waco corridor). |
| **Projected Metric CRS** | `EPSG:32618` (UTM 18N) | `EPSG:32614` (UTM 14N) | UTM Zone 14N minimizes metric distortion across Central Texas. |
| **Published Area Benchmark** | $\sim 87.3 \text{ km}^2$ (incl. water) | $\sim 2,740 \text{ km}^2$ (US Census McLennan) | Benchmark assertion proves Nominatim returned the correct county polygon. |
| **Base Geometry** | Building Footprints (`building: True`) | IH-35 Highway Centerline (`highway: motorway`) | OOH billboards sit along highway corridors, not building walls. |
| **Test Subset (`TEST_BBOX`)** | Midtown / Bryant Park | Waco Urban IH-35 Corridor | Allows sub-second local testing (`DEV_MODE`) before running full county. |
| **Storage Format** | `.geojson` | `.gpkg` (GeoPackage) | GeoPackage natively supports metric projected CRS (RFC-compliant). |

---

## 3. Section 1.1 — Environment & Package Imports

### Code (Cell 4)

```python
import warnings
warnings.filterwarnings('ignore')

# OSM access
import osmnx as ox

# Geospatial data handling
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

# Plotting
import matplotlib.pyplot as plt
import contextily as cx

print(f"✓ geopandas {gpd.__version__}")
print(f"✓ osmnx     {ox.__version__}")
```

### Line-by-Line Explanation: Why & How

- `import warnings; warnings.filterwarnings('ignore')`
  - **Why:** Geospatial Python libraries often trigger warnings regarding future API deprecations or coordinate transformations. Suppressing them keeps notebooks readable.
- `import osmnx as ox`
  - **Why:** `osmnx` provides the interface to OpenStreetMap's Overpass and Nominatim APIs, enabling geocoding and vector feature extraction.
- `import numpy as np`, `import pandas as pd`
  - **Why:** Standard tabular and numeric computing foundations.
- `import geopandas as gpd`
  - **Why:** The primary vector geospatial library in Python. It extends `pandas.DataFrame` into a `GeoDataFrame` with a special `geometry` column backed by GEOS/C++ via Shapely.
- `from shapely.geometry import box`
  - **Why:** `box(minx, miny, maxx, maxy)` generates a clean 4-vertex rectangular polygon. Used for bounding box cropping.
- `import matplotlib.pyplot as plt`
  - **Why:** The core plotting framework in Python.
- `import contextily as cx`
  - **Why:** Downloads satellite and map tiles (e.g., Esri World Imagery, OpenStreetMap) and projects them directly behind GeoPandas plots for visual ground-truth verification.
- `print(f"✓ geopandas {gpd.__version__}")`, `print(f"✓ osmnx {ox.__version__}")`
  - **Why:** Version sanity check. Ensures environment reproducibility.

---

## 4. Section 1.2 — The Retargetable Study-Area Pattern

### Step 1: Configuration Block (Cells 6–7)

```python
# ── Study-area configuration ──────────────────────────────
PLACE          = "Manhattan, New York"
CRS_METRIC     = 32618        # WGS 84 / UTM 18N — meters, correct for Manhattan
CRS_GEOGRAPHIC = 4326         # WGS 84 — degrees; the CRS OSM data arrives in

from pathlib import Path
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

print(f"✓ Study area : {PLACE}")
print(f"✓ Metric CRS : EPSG:{CRS_METRIC}")
print(f"✓ Data dir   : {DATA_DIR}/")
```

#### Explanation: Why & How
- **`PLACE`**: A string geocodable by OpenStreetMap's Nominatim server.
- **`CRS_METRIC`**: The EPSG code corresponding to the local Universal Transverse Mercator (UTM) zone in meters.
- **`CRS_GEOGRAPHIC`**: Standard WGS 84 (`EPSG:4326`).
- **`Path("data").mkdir(exist_ok=True)`**: Safely creates the output folder on disk without throwing an error if it already exists.

---

### Step 2: Geocoding the Boundary (Cell 8)

```python
admin_gdf = ox.geocode_to_gdf(PLACE)
admin_poly = admin_gdf.geometry.union_all()
admin_poly
```

#### Explanation: Why & How
- `ox.geocode_to_gdf(PLACE)`:
  - **How:** Queries Nominatim and returns an administrative polygon boundary as a single-row GeoDataFrame.
  - **Why:** Eliminates manual shapefile downloading. Automatically fetches official legal boundaries.
- `admin_gdf.geometry.union_all()`:
  - **Why:** If the administrative query returns multiple polygons (such as islands, exclaves, or disjoint parcels), `union_all()` merges them into one single `Polygon` or `MultiPolygon` in WGS 84 coordinates.

---

### Step 3: Metric Projection and Area Verification (Cells 9–10)

```python
admin_gdf_metric = admin_gdf.to_crs(epsg=CRS_METRIC)
study_area = admin_gdf_metric.geometry.union_all()
admin_gdf_metric.crs

print(f"  administrative polygon (incl. water): {study_area.area / 1e6:,.1f} km²")
```

#### Explanation: Why & How
- `admin_gdf.to_crs(epsg=CRS_METRIC)`:
  - **How:** Performs mathematical coordinate transformation from degrees $(^{\circ})$ into projected meters $(m)$.
  - **Critical Rule:** Never use `admin_gdf.set_crs()`. `set_crs()` only changes the metadata label without recalculating coordinates, which corrupts spatial geometry. `to_crs()` recalculates the actual vertex coordinates.
- `study_area.area / 1e6`:
  - **How:** Calculates planar area in $m^2$, then divides by $1,000,000$ to output square kilometers ($km^2$).
  - **Why:** Serves as a vital sanity check against published census data to confirm the geocoder didn't fetch an incorrect boundary.

---

### Step 4: Satellite Basemap Verification (Cell 11)

```python
f, ax = plt.subplots(1, 1, figsize=(6, 6))
admin_gdf_metric.plot(ax=ax, facecolor='none', edgecolor='red', linewidth=1.5)
cx.add_basemap(ax, crs=admin_gdf_metric.crs, source=cx.providers.Esri.WorldImagery)

ax.set_title(f'{PLACE} — boundary (EPSG:{CRS_METRIC})', fontsize=13)
ax.set_aspect('equal')
ax.axis('off')
plt.tight_layout()
plt.show()
```

#### Explanation: Why & How
- `admin_gdf_metric.plot(ax=ax, facecolor='none', edgecolor='red', linewidth=1.5)`:
  - Renders the polygon boundary outline in red with a transparent interior so the satellite imagery underneath remains fully visible.
- `cx.add_basemap(ax, crs=admin_gdf_metric.crs, source=cx.providers.Esri.WorldImagery)`:
  - Fetches and renders Esri satellite aerial imagery tiles matching the spatial extent and CRS of the plot.
- `ax.set_aspect('equal')`:
  - Enforces uniform 1:1 scaling between X and Y axes to prevent map distortion.
- `ax.axis('off')`:
  - Removes unnecessary tick marks and bounding boxes for a clean cartographic presentation.

---

## 5. Section 1.3 — Base Geometries (Building Footprints)

### Step 1: Downloading Features from OSM (Cell 15)

```python
buildings = ox.features_from_polygon(admin_poly, tags={"building": True})

print(f"✓ Pulled raw building features for {PLACE}")
print(f"  raw features: {len(buildings):,}")
```

#### Explanation: Why & How
- `ox.features_from_polygon(admin_poly, tags={"building": True})`:
  - **How:** Sends an Overpass query retrieving all OpenStreetMap objects inside `admin_poly` containing the tag `building=*`.
  - **Result:** Returns $\sim 46,000$ raw geometries.

---

### Step 2: MultiIndex Normalization (Cell 16)

```python
buildings = buildings.reset_index()
if "id" in buildings.columns:
    buildings = buildings.rename(columns={"id": "osmid"})

print("✓ Index moved into columns")
```

#### Explanation: Why & How
- `buildings.reset_index()`:
  - **Why:** OSMnx returns data indexed by a composite MultiIndex (`['element_type', 'osmid']`). Calling `reset_index()` converts index levels into standard DataFrame columns so they can be filtered, queried, and saved to disk.
- `if "id" in buildings.columns: ...`:
  - **Why:** Maintains backward and forward compatibility across differing versions of OSMnx.

---

### Step 3: Geometry Type Filtering and Projection (Cell 17)

```python
is_polygon = buildings.geometry.type.isin(["Polygon", "MultiPolygon"])
buildings = buildings[is_polygon].copy()
buildings = buildings.to_crs(epsg=CRS_METRIC)

print(f"✓ Kept polygonal footprints and projected to EPSG:{CRS_METRIC}")
print(f"  footprints: {len(buildings):,}")
```

#### Explanation: Why & How
- `buildings.geometry.type.isin(["Polygon", "MultiPolygon"])`:
  - **Why:** Some OSM entries are single `Point` geometries (e.g., a simple pin labeled "office building"). For physical spatial modeling, we only want 2D polygons representing actual ground footprints.
- `.copy()`:
  - **Why:** Creates an independent memory buffer, preventing `SettingWithCopyWarning` when modifying attributes later.
- `buildings.to_crs(epsg=CRS_METRIC)`:
  - **Why:** Transforms all building vertex coordinates into meters.

---

### Step 4: Attribute Trimming & Primary Key Assertion (Cell 18)

```python
core_fields = ["building", "name", "height", "building:levels"]

columns_to_keep = ["osmid", "geometry"]

for field in core_fields:
    if field in buildings.columns:
        columns_to_keep.append(field)

buildings = buildings[columns_to_keep].reset_index(drop=True)

# Later chapters join feature files on 'osmid', so the key must be unique.
assert buildings["osmid"].is_unique

print(f"✓ Trimmed to core columns: {columns_to_keep}")
print(f"  footprints: {len(buildings):,}")
print(f"  primary key: 'osmid'")
```

#### Explanation: Why & How
- `core_fields`: Selects only essential analytical columns, dropping hundreds of sparse, irrelevant OSM metadata tags.
- `assert buildings["osmid"].is_unique`:
  - **Critical Rule:** In relational and geospatial data modeling, every feature must have a unique primary key. Downstream chapters join multiple tables against `osmid`. Non-unique keys would cause severe duplicate row explosion (Cartesian joins).

---

### Step 5: Exporting to File (Cell 19)

```python
BUILDINGS_PATH = DATA_DIR / "manhattan_buildings.geojson"
buildings.to_file(BUILDINGS_PATH, driver="GeoJSON")

print(f"✓ Saved buildings to {BUILDINGS_PATH}")
print(f"  later chapters: gpd.read_file('{BUILDINGS_PATH}').to_crs(epsg={CRS_METRIC})")
```

#### Explanation: Why & How
- Writes the cleaned dataset to `data/manhattan_buildings.geojson`.
- Downstream chapters reload this file directly, ensuring deterministic reproducibility without repeated network calls.

---

## 6. Section 1.4 — Fast Test Bounding Box (DEV_MODE)

### Code (Cells 21–25)

```python
# ── Small test bounding box within Midtown (lon/lat, WGS84) ──
TEST_BBOX = (-73.9890, 40.7520, -73.9800, 40.7580)  # (minx, miny, maxx, maxy)

# Turn the bounding box into a polygon, in WGS84, then project to the buildings' metric CRS.
box_wgs84 = gpd.GeoSeries([box(*TEST_BBOX)], crs=CRS_GEOGRAPHIC)
box_metric = box_wgs84.to_crs(epsg=CRS_METRIC)
test_poly = box_metric.iloc[0]

# Crop to footprints intersecting the box (intersects keeps edge buildings whole).
buildings_test = buildings[buildings.intersects(test_poly)].reset_index(drop=True)

TEST_PATH = DATA_DIR / "manhattan_buildings_test.geojson"
buildings_test.to_file(TEST_PATH, driver="GeoJSON")

# Plot test subset with satellite imagery
f, ax = plt.subplots(1, 1, figsize=(6, 6))
buildings_test.plot(ax=ax, facecolor='red', edgecolor='white', linewidth=0.3, alpha=0.6)
cx.add_basemap(ax, crs=buildings_test.crs, source=cx.providers.Esri.WorldImagery)
ax.set_title(f'Midtown test set — {len(buildings_test):,} buildings', fontsize=13)
ax.set_aspect('equal')
ax.axis('off')
plt.tight_layout()
plt.show()
```

### Line-by-Line Explanation: Why & How

- `TEST_BBOX = (-73.9890, 40.7520, -73.9800, 40.7580)`:
  - **Why:** A small geographic window around Midtown Manhattan (Times Square / Bryant Park).
- `box(*TEST_BBOX)`:
  - **How:** The `*` operator unpacks the 4-element tuple as arguments into `box(minx, miny, maxx, maxy)`.
- `gpd.GeoSeries([...], crs=CRS_GEOGRAPHIC).to_crs(epsg=CRS_METRIC)`:
  - **Why:** The bounding box starts in WGS 84 degrees, but the building footprints are in metric coordinates. Spatial intersection requires **both geometries to share the exact same CRS**.
- `buildings[buildings.intersects(test_poly)]`:
  - **Why `intersects` instead of `within`?** `within` drops any building that crosses the boundary line. `intersects` keeps edge buildings whole and unclipped.
- **Outcome:** Reduces 46,000 buildings down to $\sim 360$ buildings, enabling fast, iterative code development in subsequent chapters.

---

## 7. Key Gotchas & Defensive Spatial Engineering

1. **OSM is a Lower Bound:**
   - OSM data is crowdsourced. An absence of a building on OSM does not guarantee an empty lot in the real world.
2. **Ground Footprint $\neq$ Floor Space:**
   - 2D polygon area (`geometry.area`) calculates ground soil surface, not interior vertical square footage.
3. **`set_crs` vs `to_crs`:**
   - `set_crs` = labels metadata without changing coordinates (causes projection failure).
   - `to_crs` = executes mathematical re-projection of coordinates.
4. **Asserting Unique Keys:**
   - Always run `assert gdf['key'].is_unique` before saving or joining spatial layers.
5. **GeoPackage (.gpkg) for Metric CRS:**
   - Standard GeoJSON (RFC 7946) mandates WGS 84 coordinates. For metric projected workflows, `.gpkg` is the professional, robust format.
