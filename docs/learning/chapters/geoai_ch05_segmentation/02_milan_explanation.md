# Chapter 5 — Semantic Segmentation: Line-by-Line Code Explanation
# File: ch05_FINAL.ipynb

This file explains every single line of Python code in Chapter 5, how each piece
connects to others, and how the entire chapter maps to OOHScout AI.

Chapter 5 takes the data files prepared in Chapter 4 and trains neural networks
to classify every pixel in an aerial scene as Ground, Building, or Tree.

---

## WHAT CHAPTER 5 DOES (big picture first)

```
Chapter 4 data files (already in data/)
    lidar_ndsm_crop.tif         ← height above ground, 0.5m/px
    sentinel_edi_clear_5ch.tif  ← 5 spectral channels (B/G/R/NIR/NDVI), upsampled
    osm_buildings_edinburgh.geojson ← building polygon labels

         ↓
STEP 36 — Load + Label Generation
    Load LiDAR → normalize
    Load Sentinel-2 → upsample to LiDAR grid
    Load OSM buildings → rasterize to pixel labels
    Combine height + NDVI → multi-class labels (ground/building/tree)

         ↓
STEP 37 — Binary segmentation: LiDAR only
    Input: nDSM (1 channel)  → predict: building / not building
    U-Net → train → evaluate IoU

         ↓
STEP 38 — Binary segmentation: LiDAR + Sentinel-2
    Input: nDSM + 5 Sentinel channels (6 channels) → predict: building
    Same U-Net → same evaluation → compare with Step 37

         ↓
STEP 39 — Multi-class segmentation: 3 classes
    Input: 6 channels → predict: Ground(0) / Building(1) / Tree(2)
    CrossEntropyLoss instead of BCE+Dice

         ↓
STEP 40 — Evaluation and comparison
    IoU scores for all 3 experiments
    Folium interactive map overlaid on real Edinburgh basemap

         ↓
STEP 41 — Post-processing + vectorisation
    Raw prediction → morphological cleaning → polygon footprints
    GeoDataFrame of predicted building polygons in WGS84
```

---

## OOHSCOUT RELEVANCE SUMMARY

Before reading each line, understand WHY this chapter matters for OOHScout:

| Chapter 5 output | OOHScout use |
|-----------------|-------------|
| Building detection | Obstruction map — what blocks sightlines to a billboard |
| Tree detection (NDVI) | Vegetation screening — trees hiding approach views |
| Post-processing pipeline | Any mask cleanup before spatial analysis |
| Vectorization (raster→polygon) | Convert pixel predictions to GeoJSON for PostGIS |
| 6-channel scene (LiDAR+Sentinel) | Template for combining height + spectral features |
| Spatial train/test split | How to split geospatial data without data leakage |

---

## SECTION 1 — SETUP: Imports

```python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Patch
import matplotlib.cm as cm
```
Standard visualization stack.
`mpatches.Patch` creates colored legend boxes — used for ground/building/tree
color legend on all multi-class plots.
`matplotlib.cm` provides colormaps — `cm.YlOrRd` is used for the height overlay.

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
```
PyTorch deep learning framework.
- `torch.nn` = neural network building blocks (layers, loss functions)
- `torch.optim` = optimization algorithms (Adam, SGD)
- `Dataset` = base class for custom datasets (PatchDataset extends this)
- `DataLoader` = batches your dataset, shuffles, and feeds it to the model

```python
import rasterio
import rasterio.transform
from rasterio.enums import Resampling
from rasterio.features import shapes as rio_shapes
from rasterio.features import rasterize
from rasterio.warp import (
    reproject, calculate_default_transform, Resampling as WarpResampling
)
from rasterio.warp import transform_bounds
from rasterio.crs import CRS
```
Extended rasterio imports beyond Chapter 4:
- `Resampling` = how to resize pixels (nearest/bilinear/cubic)
- `rio_shapes` = converts a raster mask to vector polygons (Step 41)
- `rasterize` = converts vector polygons to a pixel mask (Step 36)
- `reproject` = changes a raster from one CRS to another (for Folium overlays)
- `calculate_default_transform` = computes output dimensions after reprojection
- `transform_bounds` = converts a bounding box from one CRS to another
- `CRS` = coordinate reference system object (used to specify EPSG:4326)

```python
import folium
import io, base64
from PIL import Image
```
For the interactive map in Step 40.
`folium` creates Leaflet.js web maps in Python.
`io.BytesIO` = in-memory file buffer (save PNG without writing to disk).
`base64` = encode binary PNG as text so it can be embedded in HTML.
`PIL.Image` = converts NumPy RGBA arrays to PNG format.

```python
from skimage import morphology, measure
from skimage.morphology import erosion, square
from scipy.ndimage import binary_fill_holes
```
Image processing tools used in Step 41 post-processing.
- `morphology.disk(r)` = circular structuring element of radius r
- `morphology.binary_opening` = erode then dilate — removes small speckles
- `measure.label` = labels connected components (finds individual blobs)
- `measure.regionprops` = measures properties of each blob (area, bbox)
- `erosion` = shrinks binary shapes (for computing boundary in Step 37 viz)
- `square(n)` = n×n square structuring element
- `binary_fill_holes` = fills enclosed holes inside a binary shape

```python
import geopandas as gpd
from shapely.geometry import shape
from pathlib import Path
import random, warnings, json
warnings.filterwarnings('ignore')
```
`gpd` for GeoDataFrames.
`shape(geojson_dict)` converts a GeoJSON-format dict to a Shapely geometry.
Used in Step 41 to convert vectorized polygons from rasterio into Shapely.

```python
from geoai_utils import *
apply_style()
```
`*` imports EVERYTHING from geoai_utils — all the book's helper classes and
functions become available:
- `seed_everything`, `get_device`, `apply_style`, `stretch`
- `UNet` — the neural network architecture
- `PatchDataset` — custom Dataset for patch-based training
- `spatial_split_lr` — geographic train/test split
- `train_model` — training loop with early stopping
- `sliding_window_inference` — runs model over full image in overlapping patches
- `evaluate_segmentation` — computes IoU, precision, recall per class
- `plot_history` — plots training/validation loss curves
- `bce_dice` — combined Binary Cross Entropy + Dice loss
- `compute_class_weights` — balances class weights for imbalanced labels

---

## SECTION 2 — CONSTANTS

```python
DATA_DIR  = Path('data')
BBOX_EDI  = [-3.206475, 55.93484, -3.1750, 55.9525]
LIDAR_RES = 0.5    # meters per pixel
S2_RES    = 10.0   # meters per pixel
UPSAMPLE  = int(S2_RES / LIDAR_RES)   # = 20
```
`LIDAR_RES = 0.5` → LiDAR is at 0.5m per pixel (native Edinburgh resolution).
`S2_RES = 10.0` → Sentinel-2 is at 10m per pixel.
`UPSAMPLE = 20` → one Sentinel-2 pixel covers a 20×20 block of LiDAR pixels.
To align both on the same grid, Sentinel-2 is upsampled using nearest-neighbor,
so every 10m Sentinel pixel becomes a uniform 20×20 block.
This is the key spatial alignment decision for the whole chapter.

```python
CMAP3    = plt.cm.colors.ListedColormap(['#8B7355', '#4169E1', '#228B22'])
PATCHES3 = [
    mpatches.Patch(color='#8B7355', label='Ground'),
    mpatches.Patch(color='#4169E1', label='Building'),
    mpatches.Patch(color='#228B22', label='Tree'),
]
```
Custom 3-color colormap: brown=Ground, blue=Building, green=Tree.
`PATCHES3` = matching legend entries for all multi-class plots.
Consistent colors are used in Steps 39 and 41 so figures are comparable.

```python
seed_everything(42)
device = get_device()
```
`seed_everything(42)` seeds Python's `random`, NumPy, and PyTorch globally.
Without this, different runs would give slightly different model weights.
`get_device()` returns 'cuda' (NVIDIA GPU), 'mps' (Apple GPU), or 'cpu'.
The model is later moved to this device with `.to(device)`.

---

## SECTION 3 — SHARED HELPERS

### `run_segmentation` — the orchestrator

This function is the backbone of Steps 37, 38, and 39. It runs the full
pipeline: split data → create datasets → train model → run inference.

```python
def run_segmentation(scene, labels, in_channels, n_classes,
                     patch_size=64, n_patches=400, epochs=50,
                     patience=12, save_name='model', inf_stride=64):
```
Parameters:
- `scene` = (C, H, W) array — input data (1ch for LiDAR, 6ch for LiDAR+S2)
- `labels` = (H, W) array — pixel-level class labels
- `in_channels` = number of input channels (1 or 6 in this chapter)
- `n_classes` = 1 for binary, 3 for multi-class
- `patch_size` = crop size for training patches (128×128 pixels)
- `n_patches` = how many random patches to sample per epoch
- `patience` = early stopping: stop if val loss doesn't improve for N epochs
- `inf_stride` = stride for sliding window during inference

```python
    SPLIT  = scene.shape[2] // 2
    BUFFER = int(40 / LIDAR_RES)
    tr_img, tr_lbl, te_img, te_lbl = spatial_split_lr(
        scene, labels, SPLIT, BUFFER)
```
Geographic train/test split:
`scene.shape[2] // 2` = midpoint column (splits the scene left/right).
`BUFFER = int(40 / LIDAR_RES) = 80 pixels` = 40m gap at 0.5m/px.
The buffer prevents data leakage — patches near the boundary could overlap
both sides if no gap existed.
`spatial_split_lr` returns left half (train) and right half (test).
This is spatial cross-validation: train on the western part of Edinburgh,
test on the eastern part. This is more realistic than random pixel splits
because adjacent pixels in real images are correlated.

```python
    train_ds = PatchDataset(tr_img, tr_lbl, patch_size, n_patches,
                            pos_ratio=0.5, augment=True, multiclass=multiclass)
    val_ds   = PatchDataset(te_img, te_lbl, patch_size, n_patches // 4,
                            pos_ratio=0.5, augment=False, multiclass=multiclass)
```
`PatchDataset` randomly samples patches from the scene during training.
`pos_ratio=0.5` = 50% of patches must contain at least one building pixel.
Without this, most patches would be pure background (urban areas have ~30%
building coverage), and the model would learn to predict "nothing" everywhere.
`augment=True` for training (random flips/rotations), `False` for validation.
`n_patches // 4` = 200 validation patches (1/4 of training count).

```python
    train_dl = DataLoader(train_ds, batch_size=16, shuffle=True,  num_workers=0)
    val_dl   = DataLoader(val_ds,   batch_size=16, shuffle=False, num_workers=0)
```
DataLoader wraps the dataset and handles batching.
`batch_size=16` = 16 patches per gradient update.
`shuffle=True` for training (randomize patch order each epoch).
`num_workers=0` = load data in main process (safe on Windows).

```python
    if multiclass:
        weights   = compute_class_weights(tr_lbl, n_classes, device)
        criterion = nn.CrossEntropyLoss(weight=weights, ignore_index=255)
    else:
        criterion = bce_dice
```
Loss function selection:
- Binary (n_classes=1): `bce_dice` = Binary Cross Entropy + Dice Loss.
  BCE focuses on per-pixel accuracy; Dice focuses on shape overlap.
  Combining them gives better training stability for imbalanced scenes.
- Multi-class (n_classes=3): `CrossEntropyLoss` with class weights.
  `compute_class_weights` = inverse frequency weights so rare classes
  (buildings and trees) are weighted higher than the majority (ground).
  `ignore_index=255` = pixels labeled 255 are skipped in loss calculation
  (used for uncertain/ambiguous regions).

```python
    model = UNet(in_channels=in_channels, n_classes=n_classes).to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
```
Creates a U-Net with the specified number of input channels and output classes.
`p.numel()` = number of elements in parameter tensor.
`if p.requires_grad` = only count trainable parameters (not frozen layers).
Printed for reference — helps confirm model complexity is as expected.

```python
    history = train_model(
        model, train_dl, val_dl, criterion,
        epochs=epochs, lr=1e-3, patience=patience,
        multiclass=multiclass, device=device)
```
Runs the training loop from geoai_utils:
`lr=1e-3` = learning rate for Adam optimizer.
`patience=8` = if validation loss doesn't improve for 8 consecutive epochs,
stop training and restore the best weights.
Returns a `history` dict with train/val loss and IoU per epoch.

```python
    out_map  = sliding_window_inference(
        model, te_img, patch_size, stride=inf_stride,
        device=device, n_classes=n_classes)
    pred_map = ((out_map > 0.5).astype(np.uint8) if not multiclass
                else out_map.argmax(axis=0).astype(np.uint8))
```
Runs model over the full test image in overlapping 128×128 windows:
- Binary: output is a probability map → threshold at 0.5 → 0 or 1
- Multi-class: output is (3,H,W) logits → argmax along class axis → class ID

`sliding_window_inference` handles edge padding and average-blends overlapping
predictions, which reduces tiling artifacts at patch boundaries.

```python
    out_full = sliding_window_inference(model, scene, ...)
    pred_full = ...
```
Same inference but on the ENTIRE scene (both train and test halves).
Used for full-scene visualization in Steps 37-40.

### `arr_to_overlay_wgs84` — for Folium map

```python
def arr_to_overlay_wgs84(arr_2d, color_rgb, downsample=10):
```
Converts a binary pixel mask (in British National Grid) to a PNG image in
WGS84 so it can be overlaid on a Folium/Leaflet basemap.

```python
    small = block_reduce(arr_2d, (downsample, downsample), np.max).astype(np.float32)
```
`block_reduce` downsamples by taking the max in each 10×10 block.
`np.max` (not mean) because for binary masks: if ANY pixel in the block is 1
(building), the block should show as 1. Using mean would erase thin buildings.
Downsample by 10 → reduces 4000×4000 pixel array to 400×400 (manageable PNG).

```python
    src_tf = rasterio.transform.Affine(
        lidar_tf.a * downsample, lidar_tf.b, lidar_tf.c,
        lidar_tf.d, lidar_tf.e * downsample, lidar_tf.f,
    )
```
Updates the affine transform for the downsampled image.
`lidar_tf.a` = pixel width (0.5m). After 10x downsample → 5m per pixel.
`lidar_tf.e` = pixel height (negative, -0.5m). After downsample → -5m per pixel.
The origin (`.c` and `.f`) stays the same — top-left corner doesn't move.

```python
    reproject(source=small, destination=dst,
              src_transform=src_tf, src_crs=src_crs,
              dst_transform=dst_tf, dst_crs=dst_crs,
              resampling=WarpResampling.nearest)
```
Reprojects the downsampled array from EPSG:27700 (British National Grid, meters)
to EPSG:4326 (WGS84, degrees). Folium expects lat/lon coordinates.
`nearest` resampling for binary masks (no interpolation between 0 and 1).

```python
    rgba = np.zeros((*dst.shape, 4), dtype=np.uint8)
    rgba[dst > 0.5] = [*color_rgb, 180]
```
Creates an RGBA image (4 channels: R, G, B, Alpha).
Background pixels → transparent (alpha=0, stays as zeros).
Predicted pixels → specified color + alpha=180 (semi-transparent overlay).
`*color_rgb` unpacks the list: `[65, 105, 225]` → R=65, G=105, B=225.

```python
    buf = io.BytesIO()
    Image.fromarray(rgba, 'RGBA').save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'data:image/png;base64,{b64}', [[bottom2, left2], [top2, right2]]
```
Encodes the PNG as base64 text so it can be embedded directly in HTML
(no server or file needed — the image lives inside the URL string).
Returns the data URL + the bounding box in [[S,W],[N,E]] format for Folium.

### `ndsm_to_overlay_wgs84` — continuous height overlay

Same structure as `arr_to_overlay_wgs84` but for continuous values (nDSM):
- Uses `np.mean` instead of `np.max` (averaging heights is more accurate)
- `WarpResampling.bilinear` instead of nearest (smooth the gradient)
- `cm.YlOrRd(dst)` = applies Yellow-Orange-Red colormap to height values
- `(dst > threshold)` for alpha — only show pixels above 2cm height

---

## STEP 35 — Segmentation type comparison

```python
rows = [
    ('Semantic', '(H,W) class per pixel', 'Building vs tree vs ground', 'Steps 36–39'),
    ('Instance', '(H,W) object IDs', 'Count individual buildings', 'Step 41 post-proc'),
    ('Panoptic', '(H,W) class + instance', 'Full urban scene labelling', 'Conceptual only'),
]
```
A simple reference table — no computation, just education.
Semantic: every pixel gets a class label (what this chapter does).
Instance: every OBJECT gets a unique ID (how many buildings?).
Panoptic: combines both (professional systems like Google Street View).
For OOHScout: semantic segmentation gives you which pixels are buildings/trees.

---

## STEP 36 — Label generation

### Load LiDAR

```python
with rasterio.open(DATA_DIR / 'lidar_ndsm_crop.tif') as src:
    ndsm_raw     = src.read(1).astype(np.float32)
    lidar_crs    = src.crs
    lidar_tf     = src.transform
    lidar_bounds = src.bounds
H, W = ndsm_raw.shape
```
Loads the Edinburgh nDSM saved by Chapter 4.
`src.read(1)` = read band 1 (the only band) as a (H,W) array.
`.astype(np.float32)` = convert to 32-bit float for math.
`lidar_crs` = EPSG:27700 (British National Grid) — saved for reprojection later.
`lidar_tf` = affine transform (pixel → coordinates) — saved for rasterization.
`lidar_bounds` = (left, bottom, right, top) in meters — used to verify Sentinel alignment.
`H, W = ndsm_raw.shape` → the reference grid size that everything else must match.

```python
ndsm_norm = np.clip(ndsm_raw, 0, 50) / 50.0
```
Normalizes height to [0, 1]:
`np.clip(..., 0, 50)` = cap at 50m (any building taller is treated same as 50m).
`/ 50.0` = scale to 0–1 range.
Why normalize? Neural networks train better with inputs in a small range (0–1)
than raw values (0–108 meters with outliers).

### Load Sentinel-2 and verify alignment

```python
with rasterio.open(DATA_DIR / 'sentinel_edi_clear_5ch.tif') as src:
    sent_bounds = transform_bounds(src.crs, lidar_crs, *src.bounds)
    for a, b, name in zip(sent_bounds, lidar_bounds, ['west', 'south', 'east', 'north']):
        assert abs(a - b) < 50, (...)
    s5_edi = src.read(
        out_shape=(5, H, W),
        resampling=Resampling.nearest
    ).astype(np.float32)
```
`transform_bounds(src.crs, lidar_crs, *src.bounds)` = converts Sentinel bbox
from UTM (its native CRS) to BNG so we can compare with LiDAR bounds.
`assert abs(a - b) < 50` = verify that Sentinel and LiDAR cover the same area
(within 50m tolerance). If Chapter 4 was run correctly, this passes.
`src.read(out_shape=(5, H, W), resampling=Resampling.nearest)` = reads AND
resamples Sentinel from its native (5, 198, 198) to (5, H, W) = (5, 3999, 4000).
`Resampling.nearest` = each 10m Sentinel pixel becomes a solid 20×20 block.
This is the upsampling — we don't interpolate because Sentinel pixels
represent actual spectral measurements at 10m resolution, not a continuous field.

```python
n_nan = int(np.isnan(s5_edi[4]).sum())
s5_edi   = np.nan_to_num(s5_edi, nan=0.0)
ndvi_map = s5_edi[4]
```
NDVI has NaN at water/edge pixels where NIR+Red ≈ 0.
`np.nan_to_num(..., nan=0.0)` replaces NaN with 0 (neutral NDVI = bare soil).
One NaN in the input would propagate through the entire network forward pass
and break training. This must be done before creating any dataset.
`ndvi_map = s5_edi[4]` = extract the NDVI channel (index 4) for label generation.

### Rasterize OSM buildings

```python
bldg_edi     = gpd.read_file(DATA_DIR / 'osm_buildings_edinburgh.geojson')
bldg_edi_bng = bldg_edi.to_crs('EPSG:27700')
```
Load the OSM building footprints saved by Chapter 4.
`.to_crs('EPSG:27700')` = reproject from WGS84 to British National Grid.
Rasterization requires the polygons and the raster to be in the SAME CRS.

```python
valid_geoms = [(g, 1) for g in bldg_edi_bng.geometry
               if g is not None and g.is_valid and not g.is_empty]
```
Filter to valid geometries only.
`(g, 1)` = tuple of (geometry, burn_value) — value 1 means "building pixel."
Invalid geometries (self-intersections, empty shapes) cause rasterization errors.
`g.is_valid` = passes Shapely's validity check (no self-intersections).
`not g.is_empty` = has actual geometry (not a null shape).

```python
labels_bin = rasterize(
    valid_geoms,
    out_shape=(H, W),
    transform=lidar_tf,
    fill=0,
    dtype='uint8',
)
```
`rasterize` converts vector polygons to a pixel mask:
- Pixels INSIDE any building polygon → value 1
- All other pixels → value 0 (fill)
- `out_shape=(H, W)` = match the LiDAR grid exactly
- `transform=lidar_tf` = use LiDAR's affine transform so pixels align perfectly
- `dtype='uint8'` = 0/1 values fit in 8-bit unsigned integer

### Multi-class labels

```python
HEIGHT_THRESHOLD = 2.0 / 50.0   # = 0.04 normalized
NDVI_TREE        = 0.35
NDVI_UNCERTAIN   = 0.15
```
Thresholds for the 3-class labeling rules:
- `HEIGHT_THRESHOLD = 0.04` = pixels with normalized height ≥ 0.04 (2m real)
  are considered elevated (could be buildings or trees)
- `NDVI_TREE = 0.35` = above this NDVI → clearly vegetated
- `NDVI_UNCERTAIN = 0.15` = between 0.15 and 0.35 → uncertain zone

```python
elevated  = ndsm_norm >= HEIGHT_THRESHOLD     # boolean mask: True where tall
labels_mc = np.zeros((H, W), dtype=np.uint8) # start: everything is ground (0)
labels_mc[labels_bin == 1] = 1               # OSM buildings → class 1
labels_mc[elevated & (ndvi_map > NDVI_TREE) & (labels_bin == 0)] = 2   # trees
```
The labeling logic:
1. Everything starts as Ground (0)
2. OSM building polygons → Building (1) — trusted source, highest priority
3. Pixels that are elevated AND have high NDVI AND are NOT OSM buildings → Tree (2)
   The `& (labels_bin == 0)` prevents OSM buildings from being overwritten by trees

```python
uncertain = (elevated & (ndvi_map >= NDVI_UNCERTAIN)
             & (ndvi_map <= NDVI_TREE) & (labels_bin == 0))
ndvi_mid  = (NDVI_UNCERTAIN + NDVI_TREE) / 2
labels_mc[uncertain & (ndvi_map <  ndvi_mid)] = 1   # → building
labels_mc[uncertain & (ndvi_map >= ndvi_mid)] = 2   # → tree
```
The uncertain zone (NDVI 0.15–0.35): elevated, not in OSM, moderate NDVI.
Could be a rooftop garden, a tree next to a building, or just sensor noise.
Decision: split at midpoint NDVI (0.25).
Below midpoint → lean toward Building; Above midpoint → lean toward Tree.
This is a heuristic, not truth. The model will learn to correct it.

---

## STEP 37 — Binary segmentation: LiDAR only

```python
scene_lidar = ndsm_norm[np.newaxis]   # (H,W) → (1, H, W)
```
`np.newaxis` adds a new first dimension.
The model expects (C, H, W) format, so even a single-channel input needs the C dimension.
`C=1` = one input channel (height only).

```python
model_lidar, hist_lidar, prob_lidar, pred_lidar, \
    te_img_lidar, te_lbl_lidar, pred_full_lidar, SPLIT = run_segmentation(
        scene_lidar, labels_bin, in_channels=1, n_classes=1, ...)
```
Runs the full pipeline with:
- 1 input channel (nDSM height)
- 1 output class (binary: building or not)
- `n_classes=1` → sigmoid output + BCE+Dice loss
Returns 8 values: model, history, probability map, predicted mask (test half),
test image, test labels, full-scene prediction, train/test split column.

```python
te_lbl_lidar_bin = (te_lbl_lidar == 1).astype(np.uint8)
results_lidar = evaluate_segmentation(pred_lidar, te_lbl_lidar_bin, ['Background', 'Building'])
```
`te_lbl_lidar == 1` extracts only the building class as a binary mask.
`evaluate_segmentation` computes: IoU, Precision, Recall for each class.
IoU (Intersection over Union) = area of overlap / area of union — the standard
metric for segmentation. Higher = better. Random = ~0.15. Good model = >0.70.

### Full scene visualization

```python
gt_boundary = (labels_bin.astype(np.int16)
               - erosion(labels_bin, square(3)).astype(np.int16))
gt_boundary = (gt_boundary > 0).astype(np.uint8)
canvas[gt_boundary == 1] = [255, 130, 0]
```
Computes the BOUNDARY of OSM buildings by subtracting an eroded version.
`erosion(labels_bin, square(3))` shrinks the building mask by 1 pixel in all directions.
Original mask minus eroded mask = just the edge pixels (1 pixel thick).
Drawing only the boundary (orange) instead of filled polygons lets you see
where the model prediction overlaps with the OSM ground truth.

---

## STEP 38 — Binary segmentation: LiDAR + Sentinel-2

```python
scene_6ch = np.concatenate([ndsm_norm[np.newaxis], s5_edi], axis=0)
print(f'Channels: nDSM | B | G | R | NIR | NDVI')
```
`np.concatenate([...], axis=0)` stacks arrays along the channel dimension.
`ndsm_norm[np.newaxis]` = (1, H, W) + `s5_edi` = (5, H, W) = (6, H, W) total.
Channel order: index 0=height, 1=Blue, 2=Green, 3=Red, 4=NIR, 5=NDVI.
The ONLY change from Step 37: `in_channels=1` → `in_channels=6`.
Everything else (U-Net, loss, training loop) is identical.
This lets us measure the exact contribution of spectral information.

### Difference map visualization

```python
both_bg   = (pred_full_lidar == 0) & (pred_full_lidar_s2 == 0)
both_bldg = (pred_full_lidar == 1) & (pred_full_lidar_s2 == 1)
only_s2   = (pred_full_lidar == 0) & (pred_full_lidar_s2 == 1)
only_lid  = (pred_full_lidar == 1) & (pred_full_lidar_s2 == 0)
```
4 mutually exclusive pixel categories:
- `both_bg` → both agree: not a building (gray)
- `both_bldg` → both agree: is a building (green)
- `only_s2` → Sentinel-2 model found it, LiDAR model missed it (blue = GAIN)
- `only_lid` → LiDAR model found it, Sentinel-2 model lost it (red = LOSS)
This map shows WHERE adding spectral channels helps vs hurts.

---

## STEP 39 — Multi-class segmentation

```python
model_mc, ... = run_segmentation(
    scene_6ch, labels_mc,
    in_channels=6, n_classes=3, ...)
```
Changes from Step 38:
1. `labels_mc` instead of `labels_bin` → 3-class labels (0/1/2)
2. `n_classes=3` → U-Net output has 3 channels (one score per class)
3. Inside `run_segmentation`: `CrossEntropyLoss` with class weights instead of BCE+Dice
4. `pred_map = out_map.argmax(axis=0)` instead of `out_map > 0.5`

Why `argmax(axis=0)`? The model outputs (3, H, W) — 3 scores per pixel.
`argmax` along axis 0 picks the class with the highest score for each pixel.
Result: (H, W) array with values 0, 1, or 2.

```python
results_mc = evaluate_segmentation(pred_mc, te_lbl_mc, ['Ground', 'Building', 'Tree'])
```
Evaluates all 3 classes simultaneously. Reports IoU per class.
Tree IoU is typically lower than Building IoU because:
1. Tree labels are derived from NDVI + height heuristics (less precise than OSM)
2. Tree boundaries are inherently fuzzy (crown spread, mixed pixels)

---

## STEP 40 — Evaluation and Folium map

### IoU comparison table

```python
b37 = results_lidar["Building"]
b38 = results_lidar_s2["Building"]
b39 = results_mc["Building"]
print(f'37  LiDAR only (1ch)       {b37:.3f}  baseline')
print(f'38  LiDAR + Sentinel (6ch) {b38:.3f}  +spectral')
print(f'39  Multi-class (6ch)      {b39:.3f}  3 classes')
```
Direct comparison of the 3 experiments.
Expected result: Step 38 ≥ Step 37 (spectral channels add information).
Step 39 may be slightly lower than Step 38 (harder optimization problem,
but adds tree detection capability).

### Folium interactive map

```python
fmap_edi = folium.Map(
    location=[(lat_s + lat_n) / 2, (lon_w + lon_e) / 2],
    zoom_start=15, tiles='CartoDB positron',
)
```
Creates a web map centered on Edinburgh's study area.
`CartoDB positron` = a minimal light-gray basemap (doesn't compete visually
with the colorful overlays we're adding).

```python
folium.GeoJson(
    bldg_edi.__geo_interface__,
    name='OSM building polygons',
    style_function=lambda x: {
        'fillColor': '#FF4444', 'color': '#CC0000',
        'weight': 1, 'fillOpacity': 0.3,
    },
).add_to(fmap_edi)
```
Adds OSM building polygons as vector layer (not a raster).
`__geo_interface__` = GeoDataFrame's built-in GeoJSON representation.
`style_function` = lambda that returns CSS-style dict for each feature.
Red fill + red border so OSM polygons are visually distinct from predictions.

```python
for url, b, name, show in [...]:
    folium.raster_layers.ImageOverlay(
        image=url, bounds=b, opacity=0.5,
        name=name, overlay=True, control=True, show=show,
    ).add_to(fmap_edi)
folium.LayerControl(collapsed=False).add_to(fmap_edi)
```
Adds each prediction as a toggleable image overlay.
`bounds=b` = [[S,W],[N,E]] in WGS84 — tells Leaflet where to place the image.
`opacity=0.5` = semi-transparent so the basemap is visible underneath.
`show=False` = layer is available in the control panel but starts hidden.
`LayerControl` = the checkbox panel on the map that lets you toggle layers.

---

## STEP 41 — Post-processing and vectorisation

### Why post-processing?

Raw neural network predictions have:
1. Small isolated speckle pixels (1-2 pixel "buildings" in open fields)
2. Internal holes (courtyards misclassified as non-building)
3. Jagged boundaries not meaningful for footprint polygons

Post-processing cleans these up before converting to vector data.

```python
raw_pred = (pred_full_mc == 1).astype(np.uint8)
```
Extract just the Building class (class 1) from the multi-class prediction.
`== 1` → boolean mask (True where building), `.astype(np.uint8)` → 0/1 values.

```python
structure = morphology.disk(2)
opened = morphology.binary_opening(raw_pred, structure).astype(np.uint8)
```
`morphology.disk(2)` = circular structuring element with radius 2 pixels = 1m radius.
`binary_opening` = erosion followed by dilation.
Erosion first: shrinks all building blobs by the structuring element size.
Any blob smaller than the structuring element disappears completely.
Dilation after: restores the eroded blobs back to approximately original size.
Net effect: small isolated speckles (< 1m radius) are removed;
large blobs (real buildings) survive.

```python
labeled = measure.label(opened)
cleaned = np.zeros_like(opened)
for prop in measure.regionprops(labeled):
    if prop.area >= 10:
        cleaned[labeled == prop.label] = 1
```
`measure.label(opened)` = assigns unique integer IDs to each connected component.
Pixels that touch each other get the same label; isolated groups get different labels.
`measure.regionprops(labeled)` = computes properties for each labeled region.
`prop.area` = number of pixels in the region.
`prop.area >= 10` = keep only blobs with at least 10 pixels = 2.5m².
Smaller blobs are too small to be real buildings and are discarded.

```python
filled = np.zeros_like(cleaned)
labeled_cln = measure.label(cleaned)
for prop in measure.regionprops(labeled_cln):
    r0, c0, r1, c1 = prop.bbox
    pad = 2
    r0 = max(0, r0 - pad); c0 = max(0, c0 - pad)
    r1 = min(cleaned.shape[0], r1 + pad); c1 = min(cleaned.shape[1], c1 + pad)
    blob        = (labeled_cln[r0:r1, c0:c1] == prop.label).astype(np.uint8)
    blob_filled = binary_fill_holes(blob).astype(np.uint8)
    filled[r0:r1, c0:c1] = np.maximum(filled[r0:r1, c0:c1], blob_filled)
```
Per-blob hole filling — fills enclosed voids (courtyards, skylights):
`prop.bbox` = bounding box (row_min, col_min, row_max, col_max) of each blob.
`pad = 2` = expand the crop window by 2 pixels on each side.
The padding is needed because `binary_fill_holes` requires the blob to be
completely surrounded — without padding, holes touching the crop edge aren't filled.
`blob = (labeled_cln[r0:r1, c0:c1] == prop.label)` = isolate just this one blob.
`binary_fill_holes(blob)` = fills all enclosed holes in this blob.
`np.maximum(...)` = merge back into the output (take max of existing and filled).
Process per blob (not whole image) because global fill would connect separate buildings.

### Vectorisation

```python
geoms = [
    shape(g) for g, v in rio_shapes(filled.astype(np.int32), transform=lidar_tf)
    if v == 1
]
```
`rio_shapes(array, transform)` converts a raster to GeoJSON polygon features.
It traces the boundary of each connected region and returns (geojson_dict, value) pairs.
`if v == 1` = only keep building polygons (skip background, v=0).
`shape(g)` converts the GeoJSON dict to a Shapely geometry.
`transform=lidar_tf` = uses LiDAR's georeferencing so polygons have real coordinates.

```python
footprints = gpd.GeoDataFrame(
    {'geometry': geoms}, crs='EPSG:27700').to_crs('EPSG:4326')
footprints['area_m2'] = footprints.to_crs('EPSG:27700').geometry.area
```
Wraps the Shapely geometries in a GeoDataFrame with EPSG:27700 CRS.
`.to_crs('EPSG:4326')` = converts to WGS84 (lat/lon) for storage and web display.
`footprints.to_crs('EPSG:27700').geometry.area` = computes area in square meters.
Must re-project to EPSG:27700 (meters) for area calculation — degrees aren't uniform.

### Zoom comparison

```python
fp_bng  = footprints.to_crs('EPSG:27700')
osm_bng = bldg_edi.to_crs('EPSG:27700')
scene_cx = (lidar_bounds.left + lidar_bounds.right) / 2
scene_cy = (lidar_bounds.bottom + lidar_bounds.top) / 2
minx, maxx = scene_cx - 450, scene_cx + 450
miny, maxy = scene_cy - 550, scene_cy + 550
fp_zoom  = fp_bng.cx[minx:maxx, miny:maxy]
osm_zoom = osm_bng.cx[minx:maxx, miny:maxy]
```
Both converted to BNG (meters) for plotting — plotting WGS84 at 56°N latitude
would horizontally stretch shapes by ~1.78× due to the latitude distortion.
`scene_cx/cy` = center of the study area in BNG meters.
`±450m / ±550m` = 900m × 1100m zoom window (about 10 city blocks).
`.cx[minx:maxx, miny:maxy]` = GeoPandas spatial index clip to the window.

```python
ax.set_aspect('equal')
```
Critical for geographic plots in meters — ensures 1m east = 1m north on screen.
Without this, east-west and north-south distances would appear different.

---

## HOW STEPS CONNECT

```
Chapter 4 files
    lidar_ndsm_crop.tif
    sentinel_edi_clear_5ch.tif
    osm_buildings_edinburgh.geojson
         ↓
STEP 36: Load all 3 → create labels
    ndsm_norm   (1, H, W)  ← normalized height, [0,1]
    s5_edi      (5, H, W)  ← Sentinel channels, NaN→0
    labels_bin  (H, W)     ← 0=bg, 1=building
    labels_mc   (H, W)     ← 0=ground, 1=building, 2=tree
         ↓
STEP 37: scene = ndsm_norm[np.newaxis]    → binary model (1ch input)
STEP 38: scene = np.concatenate([ndsm, s5])  → binary model (6ch input)
STEP 39: same scene as Step 38              → multi-class model (6ch, 3 classes)
         ↓ (all 3 steps use run_segmentation internally)
         ↓
STEP 40: compare IoU scores + Folium map
         ↓
STEP 41: Take Step 39's prediction → clean → vectorize
    pred_full_mc == 1   → binary building mask
    → opening → remove small blobs → fill holes
    → rio_shapes → GeoDataFrame → WGS84 footprints
         ↓
    footprints GeoDataFrame (can be saved to PostGIS)
```

---

## KEY PATTERNS FOR OOHSCOUT

### 1. Spatial train/test split — use this everywhere

```python
SPLIT  = scene.shape[2] // 2       # split at midpoint column
BUFFER = int(40 / LIDAR_RES)       # 40m gap in meters
tr_img, tr_lbl, te_img, te_lbl = spatial_split_lr(scene, labels, SPLIT, BUFFER)
```
NEVER do random train/test split on geospatial data.
Adjacent pixels are correlated — a random split leaks training info into test.
Always split by geography (left/right or north/south).

### 2. Always upsample Sentinel-2 to LiDAR grid with nearest-neighbor

```python
s5_edi = src.read(out_shape=(5, H, W), resampling=Resampling.nearest)
```
When mixing resolutions, always bring lower-res data to higher-res grid.
Use nearest (not bilinear) to preserve the actual spectral measurement
without blending neighboring pixels.

### 3. Replace NaN before any neural network call

```python
s5_edi = np.nan_to_num(s5_edi, nan=0.0)
```
One NaN in input → entire model output is NaN → loss is NaN → training fails.
Always replace NaN before creating datasets.

### 4. Rasterize vector → raster

```python
labels = rasterize(valid_geoms, out_shape=(H, W), transform=lidar_tf, fill=0, dtype='uint8')
```
Use the SAME transform as your target raster. Any mismatch → misaligned labels.

### 5. Vectorize raster → vector (the reverse)

```python
geoms = [shape(g) for g, v in rio_shapes(mask.astype(np.int32), transform=lidar_tf) if v == 1]
footprints = gpd.GeoDataFrame({'geometry': geoms}, crs='EPSG:27700').to_crs('EPSG:4326')
```
For OOHScout: save prediction polygons to PostGIS for spatial queries.

### 6. Positive ratio sampling for imbalanced classes

```python
train_ds = PatchDataset(tr_img, tr_lbl, patch_size, n_patches, pos_ratio=0.5, ...)
```
In billboard siting, most pixels along a corridor are NOT buildings or parcels.
Always force 50% of training patches to contain at least one positive class pixel.

### 7. Post-processing before vectorizing

```python
opened  = morphology.binary_opening(raw_pred, morphology.disk(2))
cleaned = remove small blobs < 10 pixels
filled  = binary_fill_holes per blob
```
For OOHScout: clean any raster predictions before converting to polygons for PostGIS.

---

## OOHSCOUT TRANSLATION TABLE

| Chapter 5 technique | OOHScout equivalent |
|--------------------|-------------------|
| `ndsm_norm` as input | Any height/elevation data along corridor |
| `s5_edi` (NDVI channel) | Vegetation density → billboard obstruction score |
| `labels_mc[elevated & high_ndvi] = 2` | Tree label rule → corridor vegetation map |
| Building IoU evaluation | Accuracy metric for any OOHScout spatial prediction |
| `rio_shapes(mask, transform=lidar_tf)` | Convert parcel suitability mask → polygon candidates |
| `binary_opening(pred, disk(2))` | Clean noise from any binary suitability mask |
| `remove blobs < 10 pixels` | Minimum parcel size filter (too small = not a real site) |
| `binary_fill_holes` | Fill interior voids in candidate parcel polygons |
| `spatial_split_lr` | Spatial validation for any OOHScout ML model |
| `Folium + ImageOverlay` | Interactive map for billboard candidate visualization |
| `footprints.to_crs('EPSG:4326')` | Save all candidate polygons in WGS84 for PostGIS/web |

---

*File generated from ch05_FINAL.ipynb. Do not overwrite the original notebook.*
*Last updated: 2026-08-28*
