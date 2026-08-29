# Chapter 4 — Line-by-Line Code Explanation
# File: ch04_FINAL copy.ipynb

This file explains every single line of Python code in Chapter 4, why it exists,
how each piece connects to the next, and how it maps to OOHScout.

When I (AI) say "do the data prep" or you say "run the data", this file is the
reference for exactly what that means technically.

---

## HOW THE CHAPTER FLOWS (big picture first)

```
SETUP
  ↓ imports + constants + shared functions
  ↓
STEP 27 — Edinburgh LiDAR
  → manual .tif files → merge → subtract → crop → save lidar_ndsm_crop.tif
  ↓
STEP 28 — Edinburgh Sentinel-2
  → STAC API → download → reflectance → NDVI → save sentinel_edi_clear_5ch.tif
  ↓
STEP 29 — Edinburgh OSM buildings
  → osmnx → filter → save osm_buildings_edinburgh.geojson
  ↓
STEP 30 — Hungary Sentinel-2 (3 scenes)
  → STAC API → july clear + Q1 cloudy + feb reference → save 3 files
  ↓
STEP 31 — Hungary 12-month time series
  → STAC API × 12 months → align grids → stack (T,C,H,W) → save 12 files
  ↓
STEP 32 — Hungary OSM land use
  → osmnx → filter → save osm_landuse_hungary.geojson
  ↓
STEP 33 — Dutch aerial imagery
  → manual .tif → load → display only (no new file saved)
  ↓
STEP 34 — Manhattan POIs + NTA boundaries
  → osmnx + NYC API → save osm_pois_manhattan.geojson + manhattan_nta.geojson
```

Every step saves a file to `data/`. Chapters 5-14 load those files.
Nothing is downloaded twice — the code checks if the file already exists first.

---

## SECTION 1 — SETUP: Imports

```python
import numpy as np
```
NumPy = the math engine. Every satellite image is a 3D array (bands × height × width).
All pixel math (NDVI, subtraction, clipping) happens through NumPy.

```python
import matplotlib.pyplot as plt
```
The visualization library. Used to display satellite images, maps, and charts.
Does NOT save data — it only creates figures for human review.

```python
import rasterio
```
The raster I/O engine. Opens/saves GeoTIFF files. Knows about coordinate systems,
pixel sizes, and georeferencing. Think of it as "how you open an image that knows
where it is on Earth."

```python
from rasterio.merge import merge as rio_merge
```
`rio_merge` takes multiple raster tiles and stitches them into one big raster.
Used in Step 27 to combine 2 LiDAR DSM tiles and 2 DTM tiles.
Renamed `rio_merge` to avoid conflicts with other `merge` functions.

```python
from rasterio.mask import mask as rio_mask
```
`rio_mask` crops a raster to a polygon boundary.
Used everywhere to cut satellite images to just the study area box.
Renamed `rio_mask` for the same reason as above.

```python
from rasterio.warp import transform_geom
```
`transform_geom` converts a geometry (like a bounding box) from one coordinate
system to another. Example: convert WGS84 lat/lon box → UTM meters for masking.
Required because satellite scenes are stored in UTM (meters), but bboxes are
defined in WGS84 (degrees).

```python
import pystac_client
```
STAC = SpatioTemporal Asset Catalog. An open standard for finding satellite data.
`pystac_client` connects to the Element84 AWS Earth Search catalog.
Lets you search for Sentinel-2 images by location, date, and cloud cover
without needing any API key or account.

```python
import requests
```
Standard HTTP library. Used in Step 34 to download Manhattan NTA boundaries
from NYC Open Data (a REST API that returns GeoJSON).

```python
from shapely.geometry import box, mapping
```
`box(west, south, east, north)` creates a rectangular Shapely polygon from
4 coordinates — used to define study area bounding boxes as polygons.
`mapping(geometry)` converts a Shapely polygon to a dict format that rasterio
and other tools can use for masking.

```python
import osmnx as ox
```
osmnx = OpenStreetMap for Python. Downloads any map feature (buildings, roads,
land use, POIs) for any place or bounding box. The main source of vector data
in this chapter. For OOHScout: this is how you get roads, parcels, and POIs.

```python
import geopandas as gpd
```
GeoPandas = pandas + geometry. Every vector dataset (buildings, land use,
POIs, NTAs) is stored as a GeoDataFrame. Supports spatial joins, projections,
filtering by geometry. The core tool for all vector data work.

```python
from pathlib import Path
```
Modern Python way to handle file paths. `Path('data') / 'file.tif'` is safer
than string concatenation. Cross-platform (works on Windows and Mac/Linux).

```python
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)
```
Suppresses noisy warnings from third-party libraries. Does not change behavior,
just keeps the notebook output clean.

```python
from geoai_utils import apply_style, seed_everything, stretch
```
Imports three helpers from the book's companion module:
- `apply_style()` → sets matplotlib fonts/colors for consistent book figures
- `seed_everything(42)` → makes random operations reproducible (same result every run)
- `stretch(array)` → percentile contrast stretch for display (images look better)

```python
apply_style()
seed_everything(42)
```
Call both immediately. Every figure in the chapter will look consistent.
Every random sample will give the same result.
The number 42 is a convention — any fixed number works.

---

## SECTION 2 — SETUP: Constants

```python
DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)
```
`DATA_DIR` is the folder where all output files are saved.
`mkdir(exist_ok=True)` creates the folder if it doesn't exist yet.
`exist_ok=True` means: don't crash if it already exists.
ALL downstream chapters load data from this single folder.

```python
BBOX = [18.183, 45.907, 18.339, 46.015]
```
Hungary study area bounding box: [West, South, East, North] in WGS84 degrees.
This is Baranya county, Hungary — about 11 × 13 km of agricultural land.
BBOX is the DEFAULT bbox — used for Hungary unless overridden.

```python
GEOM = [mapping(box(*BBOX))]
```
`box(*BBOX)` unpacks [W, S, E, N] and creates a Shapely rectangle.
`mapping(...)` converts it to a GeoJSON-style dict.
`[...]` wraps it in a list because rasterio's mask function needs a list of geometries.
GEOM is the crop mask for Hungary satellite downloads.

```python
BBOX_EDI = [-3.206475, 55.93484, -3.1750, 55.9525]
GEOM_EDI = [mapping(box(*BBOX_EDI))]
```
Same as above but for Edinburgh city centre (~2 × 2 km).
Negative longitudes = west of the prime meridian (UK is west).
GEOM_EDI is the crop mask for Edinburgh satellite + LiDAR downloads.

```python
BAND_KEYS = ['blue', 'green', 'red', 'nir']
```
The 4 Sentinel-2 bands used in this book, in order.
These are the STAC asset keys — the exact names used by Element84 Earth Search.
The order (BGRNIR) defines what array index means what:
index 0 = blue, 1 = green, 2 = red, 3 = NIR.
This order is a CONTRACT that every downstream chapter depends on.

```python
NDVI_CMAP = 'RdYlGn'
NDVI_VMIN = -0.2
NDVI_VMAX = 0.8
```
Display constants for NDVI visualizations:
- `RdYlGn` = Red-Yellow-Green colormap (red=low vegetation, green=high)
- `-0.2` to `0.8` = the meaningful NDVI range (water/bare soil → dense forest)
- These same values are used in every NDVI plot in chapters 4-14 for consistency

---

## SECTION 3 — SHARED BUILDING BLOCK: STAC catalog connection

```python
catalog = pystac_client.Client.open(
    'https://earth-search.aws.element84.com/v1'
)
```
Opens a connection to the Element84 Earth Search API — a free public catalog
of Sentinel-2 satellite imagery hosted on AWS.
No API key needed. Returns a catalog object you search against.
Think of it as: "open the satellite image library."

```python
STAC_PIN = {
    ('edinburgh', '2024-05-01/2024-10-30'): None,
    ('hungary_jul', '2024-07-01/2024-07-31'): None,
    ...
}
```
A dictionary that can store specific scene IDs for reproducibility.
Key = (region_name, date_range), Value = a specific Sentinel-2 scene ID (or None).
When None: the code searches for the best scene live.
When set to an ID string: the code fetches that exact scene.
This ensures the book produces the same images on every run — even if new
satellite passes have been added to the catalog since the book was written.

```python
{('hungary_ts', f'2024-{m:02d}-01/2024-{m:02d}-{d}'): None
 for m, d in zip(range(1, 13), [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])}
```
Dictionary comprehension that creates 12 entries — one per month of 2024.
`m:02d` formats month as 2 digits (01, 02 ... 12).
The list `[31, 29, ...]` is the number of days in each month (2024 is a leap year).
This pins all 12 monthly time-series downloads simultaneously.

```python
def _fetch_item(item_id):
    results = catalog.search(collections=['sentinel-2-l2a'], ids=[item_id])
    items = list(results.items())
    if not items:
        raise ValueError(f'Pinned item {item_id} not found — was it withdrawn?')
    return items[0]
```
Private helper (underscore prefix = internal use).
Fetches one specific Sentinel-2 scene by its exact ID from the catalog.
`collections=['sentinel-2-l2a']` = only look in Sentinel-2 Level-2A data.
L2A = atmospherically corrected (surface reflectance), ready to use.
Raises an error if the pinned scene was removed from the catalog.

```python
def search_best(date_range, max_cloud=15, bbox=None, region_key='edinburgh'):
    pin = STAC_PIN.get((region_key, date_range))
    if pin is not None:
        item = _fetch_item(pin)
        ...
        return item
    bbox = bbox or BBOX
    results = catalog.search(
        collections=['sentinel-2-l2a'],
        bbox=bbox,
        datetime=date_range,
        query={'eo:cloud_cover': {'lt': max_cloud}},
    )
    items = list(results.items())
    if not items:
        raise ValueError(f'No scenes for {date_range}')
    best = min(items, key=lambda x: (x.properties['eo:cloud_cover'], x.id))
    ...
    return best
```
The main scene-finder. Searches for the clearest Sentinel-2 scene for a
given date range and location:
- `date_range` = e.g. '2024-05-01/2024-10-30'
- `max_cloud=15` = reject scenes with >15% cloud cover
- `bbox=None` → defaults to BBOX (Hungary) if not overridden
- `region_key` = used to look up STAC_PIN
- `min(items, key=...)` = pick scene with fewest clouds (tie-break by ID for stability)
- Prints the pin suggestion so you can copy-paste it into STAC_PIN for future runs

---

## SECTION 4 — SHARED BUILDING BLOCK: Download + save functions

```python
def download_item(item, geom=None, with_scl=False):
    geom = geom or GEOM
    bands = []
    for key in BAND_KEYS:
        with rasterio.open(item.assets[key].href) as src:
            geom_native = transform_geom('EPSG:4326', src.crs, geom[0])
            arr, _ = rio_mask(src, [geom_native], crop=True)
        bands.append(arr[0].astype(np.float32))
    stack = np.stack(bands, axis=0)
```
Downloads 4 satellite bands (B/G/R/NIR) for one Sentinel-2 scene:
- `item.assets[key].href` = URL of that band's Cloud-Optimized GeoTIFF on AWS
- `rasterio.open(...)` streams just the pixels we need (no full download)
- `transform_geom('EPSG:4326', src.crs, geom[0])` converts the WGS84 bbox to
  the scene's native CRS (UTM) so we can crop correctly
- `rio_mask(src, [...], crop=True)` crops to just the bbox
- `arr[0]` = first (only) band; `.astype(np.float32)` = use 32-bit float
- `np.stack(bands, axis=0)` stacks 4 (H,W) arrays into one (4,H,W) array
  → axis=0 means stack along the new first dimension (bands)

```python
    if not with_scl:
        return stack
```
`with_scl=False` → just return the 4-band array (default case).
`with_scl=True` → also download and return the Scene Classification Layer (SCL),
which labels each pixel as cloud, shadow, water, vegetation, etc.
Used in Step 31 for time-series cloud masking.

```python
    from rasterio.warp import reproject, Resampling
    with rasterio.open(item.assets['scl'].href) as scl_src:
        scl_out = np.zeros((ref_h, ref_w), dtype=np.uint8)
        reproject(
            source=rasterio.band(scl_src, 1),
            destination=scl_out,
            src_transform=scl_src.transform, src_crs=scl_src.crs,
            dst_transform=ref_tf, dst_crs=ref_crs,
            resampling=Resampling.nearest,
        )
    return stack, scl_out
```
SCL is at 20m resolution; the BGRNIR bands are at 10m.
`reproject` reprojects AND resamples the SCL to match the 10m grid.
`Resampling.nearest` = for class labels, nearest-neighbor is correct
(don't interpolate between class IDs — that would create nonsense values).
Returns tuple: (4-band array, SCL array) when with_scl=True.

```python
def save_geotiff(array, path, ref_item, geom=None, nodata=None):
    geom = geom or GEOM
    with rasterio.open(ref_item.assets['red'].href) as src:
        geom_native = transform_geom('EPSG:4326', src.crs, geom[0])
        _, tf = rio_mask(src, [geom_native], crop=True)
        crs = src.crs
    C, H, W = array.shape
    profile = dict(
        driver='GTiff', height=H, width=W,
        count=C, dtype=array.dtype,
        crs=crs, transform=tf,
    )
    if nodata is not None:
        profile['nodata'] = nodata
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(array)
    size_mb = path.stat().st_size / 1e6
    print(f'Saved: {path.name}  {array.shape}  {size_mb:.1f} MB')
```
Saves a NumPy array as a georeferenced GeoTIFF:
- Uses the red band from `ref_item` to get the CRS and transform (geolocation info)
- `profile` = the metadata dict that tells rasterio how to write the file
- `driver='GTiff'` = save as GeoTIFF format
- `count=C` = number of bands
- `crs=crs` = coordinate reference system (e.g. UTM zone 34N)
- `transform=tf` = the affine transform (maps pixel indices to real-world coords)
- `nodata=np.nan` → pixels with no valid data are marked NaN (for reflectance)
- `nodata=0` → pixels with no valid data are marked 0 (for raw DN integers)

---

## SECTION 5 — SHARED BUILDING BLOCK: Spectral math functions

```python
def to_reflectance(raw, item=None):
    offset = 0.0
    if item is not None:
        applied = item.properties.get('earthsearch:boa_offset_applied', False)
        if not applied:
            offset = 1000.0
    else:
        offset = 1000.0
    return np.clip((raw - offset) / 10000.0, 0, 1).astype(np.float32)
```
Converts raw Sentinel-2 Digital Numbers (DN) to surface reflectance (0.0–1.0):
- Sentinel-2 stores pixels as integers × 10000 (e.g. reflectance 0.12 = DN 1200)
- Since Jan 2022 (Processing Baseline 04.00), a +1000 offset was added to all DNs
- `earthsearch:boa_offset_applied=True` → Element84 already subtracted 1000 → just divide
- `earthsearch:boa_offset_applied=False` → must subtract 1000 first, then divide
- `np.clip(..., 0, 1)` → clamp to valid reflectance range (removes rare negative values)
- Result: float values between 0.0 and 1.0 representing fraction of reflected sunlight

```python
def ndvi(s):
    denom = s[3] + s[2]
    out = np.where(denom < 1e-5,
                   np.nan,
                   (s[3] - s[2]) / np.where(denom < 1e-5, 1.0, denom))
    return out.astype(np.float32)
```
Computes NDVI (Normalized Difference Vegetation Index):
- Formula: NDVI = (NIR - Red) / (NIR + Red)
- `s[3]` = NIR band (index 3), `s[2]` = Red band (index 2)
- `denom = s[3] + s[2]` = denominator (NIR + Red)
- `np.where(denom < 1e-5, np.nan, ...)` = protect against divide-by-zero
  When both NIR and Red are near zero (genuine no-data edge pixels), output NaN
- NDVI range: -1.0 (water/bare soil) to +1.0 (dense green vegetation)
- For OOHScout: high NDVI = trees = potential billboard obstruction

```python
def make_rgb(raw, item=None):
    s = to_reflectance(raw, item=item)
    return np.stack(
        [stretch(s[2]), stretch(s[1]), stretch(s[0])], axis=-1
    )
```
Creates a display-ready RGB image from 4-band raw data:
- `to_reflectance(raw, item)` converts DN to 0–1 reflectance first
- `s[2]` = Red, `s[1]` = Green, `s[0]` = Blue (order reversed from array order)
- `stretch(...)` = percentile contrast stretch so the image looks bright
- `np.stack([R, G, B], axis=-1)` → (H, W, 3) array as matplotlib expects
  axis=-1 means stack along the LAST axis (channels, not bands)

---

## STEP 27 — Edinburgh LiDAR: merge tiles, compute nDSM, crop

### What is LiDAR?
LiDAR shoots laser pulses from an aircraft. The pulses bounce off the surface
(DSM = tops of buildings + trees + ground) and off the ground itself (DTM = bare earth).
nDSM = DSM - DTM = height of objects above the ground (buildings, trees).

### Why nDSM for OOHScout?
A billboard needs clear sightlines. nDSM tells you what tall objects block the view.

```python
def merge_tiles(paths):
    if not paths:
        raise FileNotFoundError(
            'No LiDAR tiles found in data/ — see the Step 27 download note '
            'and place NT27*PHASE5.tif files there before running this cell.'
        )
    sources = [rasterio.open(p) for p in paths]
    mosaic, transform = rio_merge(sources)
    meta = sources[0].meta.copy()
    meta.update(
        height=mosaic.shape[1],
        width=mosaic.shape[2],
        transform=transform,
    )
    for src in sources:
        src.close()
    return mosaic[0].astype(np.float32), meta
```
Helper that merges multiple GeoTIFF tiles:
- `paths` = list of Path objects pointing to tile files
- `raise FileNotFoundError` = clear message if files not manually downloaded yet
- `[rasterio.open(p) for p in paths]` = open all tiles simultaneously
- `rio_merge(sources)` = stitch them into one mosaic, return (array, transform)
- `sources[0].meta.copy()` = start with the first tile's metadata
- `.update(height=..., width=..., transform=...)` = correct the dimensions for merged size
- `for src in sources: src.close()` = close all file handles (memory management)
- `mosaic[0]` = drop the band dimension (shape goes from (1,H,W) to (H,W))

```python
DSM_FILES = sorted(DATA_DIR.glob('NT27*DSM*.tif'))
DTM_FILES = sorted(DATA_DIR.glob('NT27*DTM*.tif'))
```
Glob pattern `NT27*DSM*.tif` finds all files whose name:
- starts with NT27 (the OSGB grid tile reference for Edinburgh)
- contains DSM
- ends with .tif
`sorted()` ensures consistent order across runs (NT27SE before NT27SW).
NT27SE = South-East tile, NT27SW = South-West tile.

```python
dsm, lidar_meta = merge_tiles(DSM_FILES)
dtm, _          = merge_tiles(DTM_FILES)
```
Merge both DSM tiles into one array, and both DTM tiles.
`_` discards the DTM metadata (we only need the DSM metadata for geolocation).

```python
assert dsm.shape == dtm.shape, (
    f'DSM/DTM shape mismatch — staggered tiles? {dsm.shape} vs {dtm.shape}'
)
```
Safety check: DSM and DTM must be the same pixel grid before subtraction.
If they don't match, the subtraction would be nonsense. `assert` crashes
immediately with a clear message rather than producing wrong results silently.

```python
ndsm = np.clip(dsm - dtm, 0, None)
```
Compute nDSM = DSM minus DTM = height above ground.
`np.clip(..., 0, None)` = floor at 0 (no negative heights — those are sensor noise).
After this, every pixel value = meters of building/tree/structure above ground.

```python
bbox_wgs84     = box(*BBOX_EDI)
study_area     = gpd.GeoDataFrame({'geometry':[bbox_wgs84]}, crs='EPSG:4326')
study_area_bng = study_area.to_crs(lidar_meta['crs'])
geom_bng       = [mapping(study_area_bng.geometry.iloc[0])]
```
Prepare the Edinburgh crop boundary in the LiDAR coordinate system:
- `box(*BBOX_EDI)` = create a rectangle from the 4 bbox coordinates
- `gpd.GeoDataFrame(...)` = wrap it as a GeoDataFrame with WGS84 CRS
- `.to_crs(lidar_meta['crs'])` = reproject to British National Grid (EPSG:27700)
  LiDAR is in EPSG:27700, so the crop geometry must also be in EPSG:27700
- `geometry.iloc[0]` = get the first (and only) geometry
- `mapping(...)` = convert to dict format for rasterio

```python
with MemoryFile() as memfile:
    with memfile.open(driver='GTiff', height=..., count=1, ...) as dst:
        dst.write(ndsm[np.newaxis])
    with memfile.open() as src:
        ndsm_crop_arr, crop_tf = rio_mask(src, geom_bng, crop=True)
```
The nDSM is currently just a NumPy array — it has no file to crop from.
`MemoryFile()` creates a temporary in-memory GeoTIFF (no disk write).
We write the nDSM into it, then immediately crop it using `rio_mask`.
This is how you crop an in-memory array using rasterio's mask function.
`ndsm[np.newaxis]` adds a band dimension: (H,W) → (1,H,W) as rasterio expects.

```python
out_path = DATA_DIR / 'lidar_ndsm_crop.tif'
with rasterio.open(out_path, 'w', driver='GTiff', height=...) as dst:
    dst.write(ndsm_crop[np.newaxis])
assert crop_meta['crs'].to_epsg() == 27700, 'LiDAR crop must be in EPSG:27700 for Ch05'
```
Save the cropped nDSM to disk as a GeoTIFF.
`ndsm_crop[np.newaxis]` adds band dimension back: (H,W) → (1,H,W).
The assert checks the CRS is EPSG:27700 (British National Grid) — Chapter 5
depends on this. If wrong, crash now with a clear message.

---

## STEP 28 — Edinburgh Sentinel-2: download + 5-channel stack

```python
item_edi = search_best(
    '2024-05-01/2024-10-30', max_cloud=3, bbox=BBOX_EDI,
    region_key='edinburgh',
)
raw_edi = download_item(item_edi, geom=GEOM_EDI)
```
Find the clearest Sentinel-2 scene over Edinburgh between May-Oct 2024
(summer, so best chance of no clouds). Max 3% cloud cover.
`download_item` downloads 4 bands (B/G/R/NIR) cropped to Edinburgh bbox.
Result: `raw_edi` is shape (4, 198, 198) — 4 bands, ~2km × 2km at 10m/px.

```python
s_edi  = to_reflectance(raw_edi, item=item_edi)
nv_edi = ndvi(s_edi)
s5_edi = np.concatenate([s_edi, nv_edi[np.newaxis]], axis=0)
```
Convert raw DN to reflectance (0–1 values).
Compute NDVI from reflectance.
`nv_edi[np.newaxis]` → adds band dimension: (H,W) → (1,H,W).
`np.concatenate([s_edi, ...], axis=0)` → stacks along bands: (4,H,W) + (1,H,W) = (5,H,W).
Final stack: Band 0=Blue, 1=Green, 2=Red, 3=NIR, 4=NDVI.

```python
save_geotiff(s5_edi, DATA_DIR / 'sentinel_edi_clear_5ch.tif', item_edi, geom=GEOM_EDI, nodata=np.nan)
```
Saves the 5-channel Edinburgh array as a GeoTIFF.
`nodata=np.nan` marks edge pixels (no valid data) as NaN.
Chapter 5 (segmentation) loads this file directly.

---

## STEP 29 — Edinburgh OSM buildings

```python
buildings_path = DATA_DIR / 'osm_buildings_edinburgh.geojson'

if buildings_path.exists():
    bldg_edi = gpd.read_file(buildings_path)[['geometry', 'building']]
    print(f'Loaded from cache: {buildings_path.name}')
else:
    ...download...
```
Cache pattern used throughout the chapter:
- Check if file already exists → load it (fast, no internet)
- If not → download and save it
This means you can re-run any cell without re-downloading everything.
For OOHScout: use this EXACT pattern for all your data downloads.

```python
edi_poly    = box(*BBOX_EDI)
raw_osm_edi = ox.features_from_polygon(edi_poly, tags={'building': True})
bldg_edi    = (
    raw_osm_edi[raw_osm_edi.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
    [['geometry', 'building']]
)
```
`ox.features_from_polygon(polygon, tags={'building': True})` downloads all OSM
features with the 'building' tag inside the polygon.
Some features come back as Points (centroid label nodes) — we only keep
Polygon and MultiPolygon (actual footprints) using `.isin(...)`.
`[['geometry', 'building']]` keeps only the 2 columns we care about.

```python
median_m2 = bldg_edi.to_crs('EPSG:27700').geometry.area.median()
```
Projects to EPSG:27700 (meters) to compute area in square meters.
Never compute areas in degrees — WGS84 degrees are not uniform in size.
This gives a sanity check: typical Edinburgh building ~100–200 m².

```python
if not buildings_path.exists():
    bldg_edi.to_file(buildings_path, driver='GeoJSON')
```
Only save if not already cached.
`driver='GeoJSON'` = save as human-readable GeoJSON (not binary Shapefile).
GeoJSON is readable, portable, and works with every GIS tool.

---

## STEP 30 — Hungary Sentinel-2: three scenes for three purposes

Why three scenes?
- July clear → Chapter 10 land-use classification (peak growing season NDVI)
- Q1 cloudy → Chapter 12 cloud detection autoencoder (needs a cloudy input)
- February clear → Chapter 12 reference (clear reference for the cloudy scene)

```python
def search_cloudy(date_range, min_cloud=20, max_cloud=60, region_key='hungary_cloudy'):
    ...
    results = catalog.search(
        collections=['sentinel-2-l2a'],
        bbox=BBOX,
        datetime=date_range,
        query={'eo:cloud_cover': {'gt': min_cloud, 'lt': max_cloud}},
    )
    best = min(items, key=lambda x: (abs(x.properties['eo:cloud_cover'] - 40), x.id))
```
Opposite of `search_best` — this finds a PARTIALLY cloudy scene.
`gt=20, lt=60` = between 20% and 60% cloud cover.
`abs(cloud - 40)` = prefer a scene closest to 40% clouds (not too clear, not too overcast).
The cloudy scene is the training INPUT for the cloud detection model.

```python
from geoai_utils import search_matched_reference
item_feb_ref = search_matched_reference(
    catalog, BBOX, reference_item=item_cloudy, ...
)
```
`search_matched_reference` finds a clear scene on the SAME MGRS tile as the cloudy scene.
This is critical: the cloudy and reference scenes must cover exactly the same pixels
so the cloud detection model can learn to reconstruct them.
MGRS = Military Grid Reference System — Sentinel-2 scenes are organized by tile.

```python
save_geotiff(s5_jul, DATA_DIR / 'sentinel_hun_jul_5ch.tif', item_jul, nodata=np.nan)

assert raw_cloudy.max() > 1000, (...)
save_geotiff(raw_cloudy, DATA_DIR / 'sentinel_hun_cloudy_raw.tif', item_cloudy, nodata=0)
```
July → save as reflectance (float, nodata=NaN) because Ch10 needs reflectance.
Cloudy → save as RAW DN (integers, nodata=0) because Ch12 needs raw values.
The assert ensures we haven't accidentally converted to reflectance before saving.
`nodata=0` because raw DN pixels with no data have value 0, not NaN.

---

## STEP 31 — Hungary 12-month time series

This step downloads one Sentinel-2 scene per month for all of 2024 over Hungary.
Result: a (12, 5, H, W) tensor — 12 months × 5 channels × height × width.
Used in Chapter 7 (ConvLSTM time-series forecasting).

```python
QUICK = False
```
Set `QUICK = True` to only download 2 months (for testing).
Set `QUICK = False` for the full 12-month series.

```python
MONTHS = [
    ('Jan', '2024-01-01/2024-01-31'),
    ('Feb', '2024-02-01/2024-02-29'),
    ...
]
months_to_run = MONTHS[:2] if QUICK else MONTHS
```
List of (label, date_range) tuples for each month.
`MONTHS[:2]` = just January and February for quick testing.

```python
H_ref, W_ref = raw_jul.shape[1], raw_jul.shape[2]
```
The July scene's height and width become the reference grid size.
All 12 monthly scenes must be the same size as July — this is enforced below.

```python
def _dl_month(label, date_range, ref_grid=None):
    cache_path = DATA_DIR / f'sentinel_ts_{label.lower()}.tif'
    return download_month(
        label, date_range, cache_path,
        catalog=catalog, bbox=BBOX, geom=GEOM,
        h_ref=H_ref, w_ref=W_ref,
        to_reflectance_fn=to_reflectance, ndvi_fn=ndvi,
        download_item_fn=download_item, save_geotiff_fn=save_geotiff,
        ref_grid=ref_grid,
        ...
    )
```
Wraps `download_month` from geoai_utils with this notebook's specific settings.
`ref_grid` = the grid parameters (CRS, origin, pixel size, shape) of the first
successfully downloaded month. All subsequent months are validated against it.

```python
ref_grid = None
for label, date_range in months_to_run:
    try:
        s5, item = _dl_month(label, date_range, ref_grid=ref_grid)
        s5_series.append(s5)
        month_labels.append(label)
        if ref_grid is None:
            ref_grid = file_grid_key(cache_path)
            # invalidate any cached months that don't match this grid
    except Exception as exc:
        s5_series.append(None)
        month_labels.append(f'{label}*')
        print(f'  {label}: NO SCENE — {exc}')
```
The grid-locking loop:
- First successful month → save its grid as `ref_grid`
- Invalidate any previously cached months that don't match
- Months with no valid scene → append None and mark with `*` in the label
- `try/except` → don't crash if one month has no clear scene; just skip it

```python
ts_5ch = np.stack(s5_series, axis=0)
```
Stack all 12 monthly arrays into one 4D tensor.
`axis=0` = stack along the new first dimension (time).
Shape: (12, 5, H, W) = 12 months × 5 channels × height × width.

```python
shared_grid, (r0, r1, c0, c1) = assert_monthly_grids_match(
    month_labels=months_to_run,
    data_dir=DATA_DIR,
    filename_pattern='sentinel_ts_{label}.tif',
)
ts_5ch = ts_5ch[:, :, r0:r1, c0:c1]
```
`assert_monthly_grids_match` verifies all 12 files have the same grid.
Returns the common valid pixel extent (r0:r1, c0:c1).
Slicing `ts_5ch[:, :, r0:r1, c0:c1]` crops all months to this common region.
This guarantees pixel (t, c, h, w) in the time series always represents
the same geographic location across all months.

---

## STEP 32 — Hungary OSM land use

```python
hun_poly = box(*BBOX)
raw_hun  = ox.features_from_polygon(hun_poly, tags={'landuse': True})
landuse_hun = (
    raw_hun[raw_hun.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
    [['geometry', 'landuse']]
)
```
Downloads all OSM land-use polygons inside the Hungary bbox.
`tags={'landuse': True}` = get everything tagged with any landuse value.
Filter to only Polygon/MultiPolygon (not point or line features).
Keep only geometry + landuse type columns.

```python
vc   = landuse_hun['landuse'].value_counts()
keep = vc[vc >= 5].index.tolist()
landuse_hun = landuse_hun[landuse_hun['landuse'].isin(keep)].copy()
```
Remove rare land-use classes (fewer than 5 polygons).
A class with 1-2 polygons creates training problems (too few examples).
`value_counts()` counts how many polygons per class.
`vc[vc >= 5]` = only classes with ≥5 polygons.
For OOHScout: use this same filter when building land-use features.

---

## STEP 33 — Dutch aerial imagery

```python
AERIAL_PATH = DATA_DIR / '2025_110000_477000_RGB_JPEG_hrl.tif'

with rasterio.open(AERIAL_PATH) as src:
    aerial_raw = src.read()
    res_m      = src.res[0]
    H_a, W_a   = src.height, src.width
    aerial_crs = src.crs
```
The Dutch tile must be manually downloaded from PDOK before running this cell.
`src.read()` = load all bands into memory (RGB, uint8, 0–255).
`src.res[0]` = pixel size in the native CRS units (meters) = 0.08 m = 8 cm.
`H_a, W_a` = height and width in pixels (12,500 × 12,500).
`aerial_crs` = EPSG:28992 (Dutch Rijksdriehoeks coordinate system).

```python
def stretch_aerial_rgb(rgb):
    out = np.zeros_like(rgb, dtype=np.float32)
    for band_idx in range(3):
        lo, hi        = np.percentile(rgb[band_idx], [2, 98])
        out[band_idx] = np.clip((rgb[band_idx] - lo) / (hi - lo + 1e-6), 0, 1)
    return out.transpose(1, 2, 0)
```
Percentile stretch separately for each RGB band.
2nd–98th percentile = ignore extreme dark/bright outliers.
`+ 1e-6` = avoid divide-by-zero if a band has zero range.
`.transpose(1, 2, 0)` converts (3,H,W) → (H,W,3) for matplotlib.
More robust than the simpler `stretch()` function because aerial imagery
can have very different brightness across bands.

---

## STEP 34 — Manhattan OSM POIs and NTA boundaries

### POIs — the most directly useful for OOHScout

```python
pois_path = DATA_DIR / 'osm_pois_manhattan.geojson'
if pois_path.exists():
    pois_man = gpd.read_file(pois_path)[['geometry', 'amenity']]
else:
    raw_pois = ox.features_from_place(
        'Manhattan, New York City, New York, USA',
        tags={'amenity': True},
    )
    pois_man = raw_pois[raw_pois.geometry.geom_type == 'Point'][['geometry', 'amenity']]
```
`ox.features_from_place(place_name, tags={'amenity': True})` downloads all OSM
amenity points (restaurants, hotels, banks, gas stations, etc.) for a named place.
This is the KEY technique for OOHScout advertiser-demand features.
For OOHScout: replace 'Manhattan...' with your corridor bbox/place name.
Filter to Point geometry only (some amenities are polygons in OSM — we want centroids).

```python
pois_man['amenity'].value_counts().head(8).to_string()
```
Shows the most common amenity types. In Manhattan: bench, bicycle_rental,
restaurant, cafe, bar are top. For OOHScout: you want restaurant, hotel,
fuel, car_dealer, fast_food — high-traffic advertiser categories.

### NTA boundaries — pattern for jurisdiction boundaries

```python
url = 'https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson'
headers = {'User-Agent': 'geoai-essentials/1.0 (book companion)'}
response = requests.get(url, headers=headers, params={'$limit': 1000}, timeout=30)
response.raise_for_status()
nhoods_all = gpd.GeoDataFrame.from_features(response.json()['features'], crs=4326)
```
Downloads NYC neighborhood boundaries from the Socrata REST API.
`User-Agent` header identifies the request (polite practice for public APIs).
`params={'$limit': 1000}` = request up to 1000 features (default is often lower).
`timeout=30` = fail fast if server doesn't respond in 30 seconds.
`response.raise_for_status()` = crash with clear error if HTTP status ≥ 400.
`GeoDataFrame.from_features(..., crs=4326)` = parse GeoJSON features into a GeoDataFrame.

```python
manhattan = (
    nhoods_all[
        (nhoods_all['boroname'] == 'Manhattan') &
        (nhoods_all['ntatype'] == '0')
    ]
    .copy()
    .reset_index(drop=True)
)
```
Filter to Manhattan borough only and residential NTAs (type '0').
`&` = boolean AND (both conditions must be true).
`.copy()` = avoid SettingWithCopyWarning (always copy filtered subsets).
`.reset_index(drop=True)` = reset row numbers from 0 after filtering.

```python
if not pois_path.exists():
    pois_man.to_file(pois_path, driver='GeoJSON')
if not nta_path.exists():
    manhattan.to_file(nta_path, driver='GeoJSON')
```
Save only if not already cached (consistent with the chapter's cache pattern).

---

## HOW EVERYTHING CONNECTS

```
download_item() ─────────────────────────────── downloads raw DN arrays
      ↓
to_reflectance() ─────────────────────────────── converts DN → 0–1 float
      ↓
ndvi() ────────────────────────────────────────── adds 5th channel (NDVI)
      ↓
np.concatenate([s, ndvi[np.newaxis]], axis=0) ─── 4ch → 5ch stack
      ↓
save_geotiff() ────────────────────────────────── saves with geolocation
      ↓
DATA_DIR / 'sentinel_xxx_5ch.tif' ─────────────── loaded by Ch 5–14
```

```
merge_tiles(DSM) + merge_tiles(DTM) ──── two LiDAR mosaics
      ↓
ndsm = clip(dsm - dtm, 0) ───────────── height above ground
      ↓
rio_mask(ndsm, geom_bng) ────────────── crop to study area
      ↓
save lidar_ndsm_crop.tif ────────────── loaded by Ch 5 (segmentation)
                                         loaded by Ch 8 (height regression)
```

```
ox.features_from_polygon(bbox, tags) ─── raw OSM GeoDataFrame
      ↓
filter to Polygon/MultiPolygon ──────── keep only area geometries
      ↓
filter rare classes ─────────────────── only classes with ≥5 polygons
      ↓
save .geojson ───────────────────────── loaded by Ch 10 (land-use classification)
```

---

## OOHSCOUT TRANSLATION TABLE

When you say "do the data prep for OOHScout corridor X", this is what it means:

| Chapter 4 technique | OOHScout equivalent |
|--------------------|--------------------|
| `box(*BBOX)` | `box(west, south, east, north)` for your corridor |
| `ox.features_from_polygon(bbox, tags={'amenity': True})` | Get restaurants, hotels, fuel, fast_food along the corridor |
| `ox.features_from_polygon(bbox, tags={'landuse': True})` | Get zoning proxy (commercial, residential, industrial) |
| `ox.features_from_polygon(bbox, tags={'building': True})` | Get building footprints for visibility/obstruction |
| `ox.features_from_polygon(bbox, tags={'highway': True})` | Get road centerlines for corridor geometry |
| `search_best(date_range, max_cloud=3, bbox=BBOX_CORRIDOR)` | Get Sentinel-2 for vegetation/NDVI along corridor |
| NDVI from Sentinel-2 | Vegetation density = potential tree obstruction |
| nDSM from LiDAR | Building + tree heights = visibility obstruction (Phase 5+) |
| Cache pattern `if path.exists(): load else: download + save` | Use EVERYWHERE in OOHScout data pipeline |
| `to_reflectance()` | Normalize satellite data before any ML |
| GeoDataFrame `.to_crs(EPSG:3857)` | Always project to meters before computing distances |
| `requests.get(url, ...)` | Fetch parcel data, TxDOT traffic, county records from APIs |
| `gpd.read_file(path)` | Load any saved GeoJSON/Shapefile for analysis |

---

## KEY PATTERNS TO REMEMBER

**1. Always cache downloads:**
```python
path = DATA_DIR / 'my_data.geojson'
if path.exists():
    data = gpd.read_file(path)
else:
    data = download_from_somewhere()
    data.to_file(path, driver='GeoJSON')
```

**2. Always project to meters before computing area/distance:**
```python
gdf_meters = gdf.to_crs('EPSG:3857')   # Web Mercator (meters, global)
# or for Texas:
gdf_meters = gdf.to_crs('EPSG:32614')  # UTM Zone 14N (Texas, more accurate)
distances  = gdf_meters.geometry.distance(point)
areas      = gdf_meters.geometry.area
```

**3. bounding box format is always [West, South, East, North]:**
```python
BBOX_CORRIDOR = [-97.2, 31.4, -97.0, 31.6]  # example Texas corridor
```

**4. OSM tag patterns for OOHScout:**
```python
roads     = ox.features_from_polygon(bbox, tags={'highway': ['motorway','trunk','primary']})
buildings = ox.features_from_polygon(bbox, tags={'building': True})
amenities = ox.features_from_polygon(bbox, tags={'amenity': True})
landuse   = ox.features_from_polygon(bbox, tags={'landuse': True})
```

**5. Sentinel-2 bands are always in BGRNIR order (index 0,1,2,3) in this project.**

---

*This file was generated from ch04_FINAL copy.ipynb — do not overwrite the original notebook.*
*Last updated: 2026-08-27*
