# F1 Adaptation — Deep Walkthrough (Mentor Mode)

**Feature:** F1 — Retargetable Study Area
**Notebook:** [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb)
**Production module:** [backend/src/oohscout/track_a_spatial/study_area.py](../../../../backend/src/oohscout/track_a_spatial/study_area.py)

This document is what I would say out loud if we were pair-coding. Every cell has three sections:

- **WHAT** — the concrete thing this cell does. One sentence.
- **WHY** — the reason it exists at all. What breaks or what lie enters the system if you skip it.
- **HOW** — the mechanism, gotchas, and alternatives I considered and rejected.

If any section feels shallow, tell me which one and I'll deepen it.

---

## Cell 0 — Markdown header

**WHAT.** Names the notebook and pins its scope to F1 only.

**WHY.** Scope creep is the #1 reason feature branches never merge. Milan's Chapter 1 introduces four things (imports, study area, buildings, DEV_MODE bbox), but F1 in our PRD is *only* the study-area pattern. Everything else moves to F2/F5. Naming that at the top of the notebook is a contract with your future self.

**HOW.** The header also lists sources — Nominatim for the boundary, Census TIGERweb for the reference area, Esri World Imagery for the visual check. Every dataset that touches this notebook is disclosed here. This is not decoration; it's the seed of the F4 "data provenance" feature we haven't built yet.

---

## Cell 1 — Markdown: "1.1 Setting Up the Environment"

**WHAT.** Reminds you to launch JupyterLab with `uv run jupyter lab` from the repo root.

**WHY.** Because if you launch from `~/` or from `docs/learning/...`, the repo-root detection in cell 4 still works (it walks up looking for `pyproject.toml`), but relative paths in later cells silently write files into the wrong folder. Milan's course uses `Path("data")`, which resolves relative to wherever Jupyter started. That's a bug waiting to happen. We fix it in cell 4, but the reminder here is the first line of defense.

---

## Cell 2 — Imports

```python
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import osmnx as ox

print(f'geopandas {gpd.__version__}')
print(f'osmnx     {ox.__version__}')
```

**WHAT.** Loads the five libraries every Chapter 1 cell touches and prints two version strings.

**WHY per import.**
- `warnings.filterwarnings('ignore')` — Geospatial libraries throw deprecation warnings from GDAL, PROJ, and pyproj on every projection call. In production we'd log them; in a notebook we mute them because you're going to run projections dozens of times per session and the noise buries real errors.
- `Path` — We refuse to use string concatenation for filesystem paths. Windows uses backslashes, Linux uses forward slashes, and `os.path.join` returns strings that lose their identity. `Path` objects carry OS awareness and support the `/` operator (`DATA_DIR / 'file.gpkg'`), which reads like the actual directory tree.
- `geopandas` — Extends pandas' `DataFrame` with a `geometry` column backed by Shapely. Every row is a spatial record. Filter, merge, groupby all still work.
- `osmnx` — The Python client for OpenStreetMap. Two things we use: `geocode_to_gdf` (place name → boundary polygon via Nominatim) and later `features_from_polygon` (bbox + tags → OSM features via Overpass).
- `matplotlib.pyplot` — The plotting foundation. GeoPandas' `.plot()` uses it under the hood.
- `contextily` — Downloads web-map tiles (Esri, OSM, CartoDB) and pastes them behind a matplotlib axis. Requires the axis to already be in a projected CRS. This is how we get satellite imagery under our boundary without leaving Python.

**WHY the version print.** Because two months from now, when this notebook stops working, the first thing you or I will ask is "what version of osmnx did it work with?" and you will hate yourself for not printing it. `geopandas` in particular had a breaking change at 1.0 (`geometry.unary_union` → `geometry.union_all`). Recording versions is one line; not recording them is hours of debugging.

**HOW — the ordering choice.** Standard-library imports first (`warnings`, `pathlib`), then third-party alphabetical. This is PEP 8 and every Python linter enforces it. Notice I did *not* import `numpy` or `pandas` — GeoPandas re-exports what it needs. Adding unused imports bloats the environment and hides real dependencies.

---

## Cell 3 — Markdown: "1.2 The Study-Area Pattern"

**WHAT.** Introduces the two-CRS discipline in one sentence.

**WHY.** This is the single most important idea in the entire course, and every cell that follows depends on you internalizing it. The next cell is where you'll be tempted to skip it.

---

## Cell 4 — Configuration + repo-root detection + paths

```python
PLACE = 'McLennan County, Texas'
CRS_METRIC = 32614       # WGS 84 / UTM zone 14N, meters
CRS_GEOGRAPHIC = 4326    # WGS 84 longitude/latitude

REFERENCE_TOTAL_AREA_KM2 = 2746.0
AREA_TOLERANCE_PCT = 5.0

working_dir = Path.cwd().resolve()
repo_candidates = [working_dir, *working_dir.parents]
REPO_ROOT = next(
    (path for path in repo_candidates if (path / 'pyproject.toml').exists()),
    None,
)
assert REPO_ROOT is not None, 'Run this notebook from inside the repository.'

DATA_DIR = REPO_ROOT / 'backend' / 'data' / 'processed'
DATA_DIR.mkdir(parents=True, exist_ok=True)
place_slug = PLACE.split(',')[0].strip().lower().replace(' ', '_')
STUDY_AREA_PATH = DATA_DIR / f'{place_slug}_study_area.gpkg'
```

### The three configuration constants — WHY they live together

**WHAT.** Three constants: what to geocode, what metric projection to use, what geographic CRS OSM returns.

**WHY they must stay in one block.** Imagine a future session where you retarget the notebook to Bexar County (San Antonio). If `PLACE` and `CRS_METRIC` are declared in different cells, you will change one and forget the other. Then every buffer, every distance, every area is computed against a projection that doesn't match the county's real UTM zone. The math still runs — that's the danger — the results are just wrong by 200-500 meters. This kind of bug survives code review because the pipeline "works." Keeping the block together makes retargeting an atomic operation.

**WHY `CRS_METRIC = 32614` specifically.**

`EPSG:32614` is "WGS 84 / UTM Zone 14N". UTM (Universal Transverse Mercator) divides the world into 60 six-degree-wide longitude zones. Within a zone, distances and areas are as close to Euclidean as any global projection ever gets — typically <1m distortion over a 30 km stretch. McLennan County is centered on roughly -97.15° longitude. UTM zone 14 covers -102° to -96°. Waco sits comfortably inside. If we'd used Zone 15 (-96° to -90°, correct for Houston), our area measurement would drift by 5-10%.

**Rule of thumb:** UTM zone number = `int((longitude + 180) / 6) + 1`. For McLennan (-97.15°): `int((-97.15 + 180) / 6) + 1 = int(13.808) + 1 = 14`. Add `N` if you're above the equator.

**WHY `CRS_GEOGRAPHIC = 4326`.**

Because that's what Nominatim returns. Every geocoding API, every GPS device, every web-map API on the planet speaks EPSG:4326 — WGS 84 in latitude/longitude degrees. We accept OSM data in 4326, immediately project to 32614 for measurement, and only convert back to 4326 when we need to send data to a web-map front-end. Two representations, one truth.

**WHY the published-area constants.**

`REFERENCE_TOTAL_AREA_KM2 = 2746.0` comes from the U.S. Census TIGERweb record for McLennan County (GEOID 48309): 2,685,056,036 m² land + 60,961,676 m² water ≈ 2,746 km² total. We use *total* area (not land-only) because OSM's administrative polygon includes water — otherwise we'd fail our own assertion. `AREA_TOLERANCE_PCT = 5.0` is the slack we allow for OSM polygon simplification and projection distortion. Our actual measurement came in at 2,747.3 km² (0.05% off), so we're well within tolerance. If a future retarget produces >5% error, that's a signal Nominatim returned a subdivision or the wrong-named place — do not proceed.

### The repo-root detection block — WHY it exists

**WHAT.** Walks up the directory tree from `Path.cwd()` looking for `pyproject.toml`, then anchors `DATA_DIR` to it.

**WHY.** Jupyter's working directory is wherever you launched `jupyter lab`. If you launched from the repo root, `Path("data")` resolves to `<repo>/data/`. If you launched from `docs/learning/chapters/...`, it resolves to `<repo>/docs/learning/chapters/.../data/`. Milan's course has this exact bug — cache files scatter across the filesystem, and downstream chapters can't find them.

**HOW the walk works.**
- `Path.cwd().resolve()` gives you the absolute current working directory (`.resolve()` follows symlinks so we compare against real paths).
- `[working_dir, *working_dir.parents]` gives you `[cwd, cwd.parent, cwd.parent.parent, ..., root]`. In Windows this eventually terminates at `C:\`.
- `next((p for p in candidates if (p / 'pyproject.toml').exists()), None)` returns the first ancestor that contains `pyproject.toml`. If none exists, returns `None`.
- The `assert` catches the "wrong Jupyter launch directory" case with a helpful message instead of a mysterious FileNotFoundError three cells later.

**WHY `pyproject.toml` and not `.git`.** Because `.git` disappears if you clone this project as a zip. `pyproject.toml` is committed and always present at the repo root as long as the project is a Python package.

### The path assembly — WHY this layout

**WHAT.** Builds the cache path: `<repo_root>/backend/data/processed/mclennan_county_study_area.gpkg`.

**WHY `backend/data/processed/` specifically.** Look at [backend/README.md](../../../../backend/README.md) — the project convention is `data/` for cached artifacts (gitignored) sub-organized into `raw/` (untouched downloads) and `processed/` (normalized/reprojected outputs). Our cache is *processed* because it lives in the target metric CRS, not raw WGS 84.

**WHY the slug transform (`'mclennan_county'`).**
```python
place_slug = PLACE.split(',')[0].strip().lower().replace(' ', '_')
```
If we retarget to `"Bexar County, Texas"`, we get `bexar_county_study_area.gpkg` automatically. No manual filename edit. The comma-split drops the state (which is redundant when the county name is unique in the U.S.); lowercase + underscore is a filesystem-safe convention that works on Windows, macOS, and Linux equally.

---

## Cell 5 — Markdown: cache-vs-download policy

**WHAT.** Documents the two representations and the cache-first policy.

**WHY.** Because the *next* cell does something clever (loads from disk on repeat runs) and if you don't see the intent stated, you might "refactor" it away as needless complexity. This markdown cell is a note-to-future-you.

---

## Cell 6 — Resolve, project, and cache

```python
if STUDY_AREA_PATH.exists():
    admin_gdf_metric = gpd.read_file(STUDY_AREA_PATH, layer='study_area')
    admin_gdf = admin_gdf_metric.to_crs(epsg=CRS_GEOGRAPHIC)
    print('Loaded the cached study-area boundary.')
else:
    admin_gdf = ox.geocode_to_gdf(PLACE)
    admin_gdf_metric = admin_gdf.to_crs(epsg=CRS_METRIC)
    admin_gdf_metric.to_file(
        STUDY_AREA_PATH, layer='study_area', driver='GPKG'
    )
    print('Downloaded and cached the study-area boundary.')

admin_poly = admin_gdf.geometry.union_all()
study_area = admin_gdf_metric.geometry.union_all()
```

### The cache-first branch — WHY it matters

**WHAT.** If the `.gpkg` exists, load it. Otherwise, geocode via Nominatim, project to metric CRS, save.

**WHY.** Nominatim is a shared community service running on donated infrastructure. Repeated identical requests are considered abuse. If everyone in the course ran their notebook 20 times, the collective load would be a real problem. The cache-first pattern is both good citizenship and 100× faster on repeat runs (disk read ~10ms vs Nominatim round-trip ~1-3s).

**HOW.** The cache stores the *projected* representation (`admin_gdf_metric`) because that's what we do measurements against. When we need the WGS 84 version for OSM queries (like F2's highway fetch), we call `to_crs(epsg=4326)` on the fly — projection is fast, storage is expensive.

**WHY layer='study_area'.** GeoPackage is a container format — one `.gpkg` file can hold many named layers (like a SQLite database of spatial tables). Naming the layer explicitly means F2 could add its own `ih35_centerline` layer to the same file if we wanted to keep McLennan's data in one place. We don't do that yet, but the naming makes it possible.

### The `union_all()` step — WHY we do it

**WHAT.** Collapses whatever geometry the GeoDataFrame contains into a single `Polygon` or `MultiPolygon`.

**WHY.** Some administrative queries return multiple rows (islands, exclaves, disjoint parcels). Manhattan returned as a MultiPolygon with Roosevelt Island and Governors Island as separate polygons. McLennan is a single contiguous county so `union_all()` returns one Polygon here — but writing the general form protects us from a "one-off works, general case breaks" bug the day we retarget to a coastal county with islands.

**WHY not `unary_union`.** That's the pre-GeoPandas-1.0 name. `union_all()` is the current API. If you see `unary_union` in Milan's notebook, that's version drift.

### WHY we keep both `admin_poly` and `study_area`

They're the same geometry in different coordinate systems. Every downstream call has to pick the right one:

- Feeding OSM Overpass queries: `admin_poly` (WGS 84 — OSM only speaks lat/lon)
- Measuring anything (area, distance, buffer): `study_area` (metric — degrees are lies)
- Rendering on a slippy web map: `admin_poly` (Leaflet/MapLibre expect 4326)
- Rendering on a static matplotlib basemap: `admin_gdf_metric` (contextily needs the projected CRS)

Get the wrong one and either the math is nonsense or the map is empty. Naming them differently is the type-safety we get without static types.

---

## Cell 7 — Markdown: "assertions are executable acceptance criteria"

**WHAT.** One line, but a philosophy statement.

**WHY.** In Milan's course, sanity checks are printed and manually inspected. In OOHScout, they're `assert`s that halt the notebook. This matters because the notebook feeds a production module (`study_area.py`) whose callers cannot inspect prints. If the assertion is executable, the notebook and the module behave identically.

---

## Cell 8 — The assertion battery

```python
assert len(admin_gdf) == 1, 'Expected one county record.'
assert admin_gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon']).all()
assert not admin_gdf.geometry.is_empty.any()
assert admin_gdf.geometry.is_valid.all()
assert admin_gdf_metric.crs.to_epsg() == CRS_METRIC
assert study_area.is_valid and not study_area.is_empty

area_km2 = study_area.area / 1_000_000
area_difference_pct = (
    abs(area_km2 - REFERENCE_TOTAL_AREA_KM2)
    / REFERENCE_TOTAL_AREA_KM2
    * 100
)

assert area_difference_pct <= AREA_TOLERANCE_PCT, (
    f'Area differs from the published reference by {area_difference_pct:.1f}%.'
)
```

### Assertion 1 — one record

**WHAT.** Confirms Nominatim returned exactly one row.

**WHY.** If Nominatim can't disambiguate `"McLennan County, Texas"` and returns multiple candidates (e.g., "McLennan County" and "McLennan Community College"), our downstream code would silently union them into a Frankenstein polygon. The area check would later catch it, but this fails fast with a clearer message.

### Assertion 2 — geometry type

**WHAT.** Confirms every row is a `Polygon` or `MultiPolygon`.

**WHY.** OSM contains `Point` geometries too — the geocoder could return a single lat/lon "centroid" record for a place it doesn't have a boundary polygon for. A Point has no area, and our next check would divide by that zero. Assert the shape first.

### Assertions 3 & 4 — non-empty and valid

**WHAT.** Confirms no geometry is empty and every geometry passes Shapely's `is_valid` check.

**WHY.** OSM administrative polygons occasionally have self-intersecting rings from imperfect community edits. Shapely's `is_valid` runs a topology check (uses the GEOS library) and returns `False` if the polygon has self-touches, self-crosses, or ring order problems. An invalid polygon breaks buffer/union/intersection math downstream in unpredictable ways. If this fires, the fix is `.buffer(0)` (a nil buffer that GEOS uses to fix common ring issues) — but you should investigate why the OSM data is broken first.

### Assertion 5 — CRS actually applied

**WHAT.** Confirms the metric GeoDataFrame's CRS is truly EPSG:32614.

**WHY.** This catches the "set_crs vs to_crs" mistake I mentioned in `02_milan_explanation.md`. If someone (or a future you) writes `.set_crs(epsg=32614)` instead of `.to_crs(epsg=32614)`, the coordinates never actually transform — they stay as raw degrees but the metadata now claims meters. The area calculation would return something like 0.00007 km² and this check catches it.

### Assertion 6 — area within 5% of Census

**WHAT.** Divides Shapely's area (which returns square meters when the CRS is metric) by 1,000,000 to get km², then compares to the published reference.

**WHY.** This is the strongest possible check that Nominatim returned the *right place*. If it accidentally geocoded a city instead of the county, or the wrong-state county with a similar name, or a subdivision, the area would be wildly different from 2,746 km². Our measured 2,747.3 km² is 0.05% off — this passes with room to spare.

**WHY 5% and not stricter.** OSM's administrative polygons are simplified from the Census TIGER lines (which have millions of vertices to describe every riverbank meander). The simplification means the OSM polygon is slightly smaller. 5% is generous enough to accommodate that plus any UTM projection distortion at the edges of the zone.

---

## Cell 9 — Markdown: "final acceptance check is visual"

**WHAT.** Explains why we still need to eyeball a map even after all these asserts.

**WHY.** The area check catches "wrong-sized place." It does not catch "correctly-sized place in the wrong location." If Nominatim returned a same-sized county 200 miles east of Waco, all our assertions would pass. Only the visual check catches this class of bug.

**Future improvement:** We could replace this with a programmatic check that a known landmark (Waco courthouse at -97.1467, 31.5493) is inside `study_area`. That's what `assert_contains_point()` in the production module does. The notebook keeps the visual for humans; the module uses the assertion for automation.

---

## Cell 10 — The plot + savefig

```python
fig, ax = plt.subplots(1, 1, figsize=(7, 7))
admin_gdf_metric.plot(
    ax=ax, facecolor='none', edgecolor='#ff2d55', linewidth=2
)
cx.add_basemap(
    ax, crs=admin_gdf_metric.crs, source=cx.providers.Esri.WorldImagery
)
ax.set_title(f'{PLACE} — F1 study-area boundary', fontsize=13)
ax.set_aspect('equal')
ax.axis('off')
plt.tight_layout()

check_png = DATA_DIR / 'mclennan_f1_check.png'
fig.savefig(check_png, dpi=120)
print(f'Saved boundary check image to {check_png}')

plt.show()
```

### The plot construction

**WHAT.** Creates a 7×7-inch matplotlib figure, draws the metric boundary as a hollow red outline, pulls Esri satellite tiles behind it.

**WHY `facecolor='none'`.** So the satellite imagery underneath is fully visible inside the boundary. A filled polygon would hide exactly the thing we're checking.

**WHY `edgecolor='#ff2d55'`.** That specific pink-red is Apple's iOS "systemRed" — highly visible against green/tan Central Texas terrain and doesn't blend into any common satellite feature. `red` would work too; the hex code is just a habit.

**WHY `set_aspect('equal')`.** In a projected CRS, 1 meter in X and 1 meter in Y should occupy the same screen distance. Without this, matplotlib fits the plot to the figure and stretches the aspect ratio, making the county look wider or taller than it is. In UTM this matters because Y-distortion at the zone edges can already be up to 0.1% — you don't want matplotlib adding more.

**WHY `axis('off')`.** UTM coordinate values (e.g., "770000, 3490000") are meaningless to a human eyeballing a boundary. Removing the tick marks reduces visual clutter.

### The savefig placement

**WHAT.** Writes a PNG copy of the figure to disk, *before* `plt.show()`.

**WHY the ordering.** In Jupyter, `plt.show()` renders the figure inline and then closes it. Any subsequent `savefig` writes an empty canvas — this is the bug that made our first attempt produce a blank PNG. Save first, show second.

**WHY no `bbox_inches='tight'`.** Combined with `ax.axis('off')`, `tight` sometimes crops to zero (because it counts axis labels/titles as content and there aren't any). Leaving it off produces a slightly padded PNG that renders reliably.

**WHY save at all.** Because two collaborators (you and me) can't share a Jupyter inline display. The PNG on disk is a durable artifact I can Read and confirm. It also becomes the visual gate evidence that F1 shipped — anyone auditing the branch can look at it without re-running the notebook.

---

## Cell 11 — Markdown: completion gate

**WHAT.** States that F1 is not shipped until every assertion passes *and* you visually confirm.

**WHY.** This is the contract between the notebook and the PRD. The status in [docs/PRD.md](../../../PRD.md) can't flip to SHIPPED until this cell's conditions are met. Writing them down inside the notebook (rather than only in the PRD) means the gate travels with the code — if you fork this notebook to a different feature, the completion criteria come along.

---

## What this notebook does NOT do

Deliberately out of scope for F1:

- **No IH-35 fetch.** That's F2. It would use this notebook's `admin_poly` as input.
- **No `TEST_BBOX`.** That's F5. Would be a Waco urban subset for fast iteration.
- **No POI query.** That's F10.
- **No candidate generation.** That's F7.
- **No score, no ranking, no map with markers.** Those are F25, F27, F42.
- **No API endpoint.** That's Phase 5+ (FastAPI on top of the production module).

Keeping F1 minimal is what lets us ship it in one session. The temptation to "just add one more thing" is what turns feature branches into month-long slogs.

---

## What the production module does that the notebook does not

The notebook is for learning + one-off human verification. [`study_area.py`](../../../../backend/src/oohscout/track_a_spatial/study_area.py) is what the app imports. Differences:

| Concern | Notebook | Production module |
|---|---|---|
| Interface | Global variables | `StudyArea` dataclass, one function call |
| Assertions | Printed with pass/fail | Raised as `AssertionError` with human message |
| Retargeting | Edit the config cell | Pass different args to `load_or_build_study_area()` |
| Visual check | Matplotlib plot | `assert_contains_point()` for automation |
| Called by | Human running Shift+Enter | FastAPI endpoint, agent tool, pytest |
| Import | Not importable | `from oohscout.track_a_spatial import load_or_build_study_area` |

**Rule of thumb:** anything you'd want to reuse from another feature (F2, F5, tests, API) belongs in the module. Anything that's a one-time explanation, exploration, or visualization belongs in the notebook.

---

## Where to go if a cell breaks

- **Cell 2 (imports) fails** — env problem. Run `uv sync` at the repo root.
- **Cell 4 (paths) fails on the assert** — you launched Jupyter from outside the repo. Restart from repo root.
- **Cell 6 (geocoding) hangs or errors** — Nominatim is rate-limited or down. Delete the cached `.gpkg` and retry in 60 seconds.
- **Cell 8 area assertion fires** — Nominatim returned a different place or a subdivision. Print `admin_gdf[['name', 'display_name']]` and check what it actually resolved to.
- **Cell 10 basemap doesn't render** — contextily can't reach Esri. Check internet; try `source=cx.providers.OpenStreetMap.Mapnik` as a fallback.

---

## The one-page mental model to walk away with

1. Two CRSes, always: geographic (4326) for I/O, projected metric for math.
2. Cache first, network second.
3. Every geometric claim is an `assert`, not a print.
4. Notebook proves the pattern; module ships it.
5. Ship the smallest thing that clears the gate. Everything else is the next feature.
