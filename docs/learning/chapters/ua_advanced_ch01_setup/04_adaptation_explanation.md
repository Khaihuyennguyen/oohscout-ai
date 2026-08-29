# UA Advanced Chapter 1 — OOHScout F1 Adaptation Explanation

**Adaptation file:** `03_oohscout_adaptation.ipynb`
**PRD feature started:** F1 — Retargetable Study Area
**Geographic scope:** McLennan County, Texas

## Adaptation goal

Produce one verified McLennan County administrative boundary in WGS 84 for future OSM downloads and one projected EPSG:32614 copy for deterministic spatial measurement.

## Parameter choices

| Parameter | Milan's Manhattan value | OOHScout value | Why |
|---|---:|---:|---|
| `PLACE` | Manhattan, New York | McLennan County, Texas | PRD MVP jurisdiction |
| `CRS_GEOGRAPHIC` | EPSG:4326 | EPSG:4326 | OSM longitude/latitude input |
| `CRS_METRIC` | EPSG:32618 | EPSG:32614 | Local UTM zone for McLennan County |
| Reference total area | Manhattan administrative area | 2,746.0 km² | Census TIGER land plus water area |
| Persistence format | GeoJSON in the course example | GeoPackage | Projected coordinates belong in a CRS-aware format |

## Cell-by-cell walkthrough

### Imports

The notebook uses only the Chapter 1 toolset: OSMnx, GeoPandas, Matplotlib, Contextily, and `Path`. No LLM performs or estimates geometry.

### Configuration

`PLACE`, `CRS_METRIC`, and `CRS_GEOGRAPHIC` remain together so a future retargeting cannot silently reuse McLennan's CRS. `REFERENCE_TOTAL_AREA_KM2` makes the acceptance test explicit.

The notebook searches the current directory and its parents for `pyproject.toml`. The repository-root assertion prevents a common Jupyter bug where relative output paths silently write files into an unexpected directory.

### Resolve and cache

The first run calls `ox.geocode_to_gdf(PLACE)`. Later runs load `mclennan_county_study_area.gpkg`. The GeoPackage cache removes the repeated Nominatim request; the Esri basemap cell still requires internet access. The notebook maintains two representations:

- `admin_poly`: WGS 84 geometry for future OSMnx requests.
- `study_area`: EPSG:32614 geometry for areas, distances, buffers, and candidate generation.

### Assertions

The code verifies one polygonal county record, non-empty and valid geometry, the expected projected CRS, and an administrative area within 5% of the published reference.

The comparison uses total administrative area, including water. It must not be compared with land-only area. The reference comes from the [U.S. Census TIGERweb county record for GEOID 48309](https://tigerweb.geo.census.gov/tigerwebmain/Files/acs25/tigerweb_acs25_county_2020_tab20_tx.html).

### Visual check

The Esri World Imagery plot confirms that the geometry surrounds McLennan County. A successful assertion cannot detect every wrong-place geocoding result, so the visual check remains mandatory.

## Sanity checks

- [ ] `len(admin_gdf) == 1`
- [ ] Geometry is Polygon or MultiPolygon
- [ ] Geometry is valid and non-empty
- [ ] `admin_gdf_metric.crs.to_epsg() == 32614`
- [ ] Published-area difference is no more than 5%
- [ ] Boundary visually surrounds McLennan County

## File produced

| Filename | Contents | Next consumer |
|---|---|---|
| `backend/data/processed/mclennan_county_study_area.gpkg` | Projected county boundary | F2 IH-35 centerline ingestion |

The file is ignored by Git because it is a reproducible cache. The notebook and its assertions are the versioned artifact.

## Status

F1 is **in progress**, not complete. Completion requires the user to run the notebook cell by cell and verify the map. After that, update the feature register and begin F2.
