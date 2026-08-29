# UA Advanced Chapter 1 — Milan Original: Study-Area Explanation

**Chapter:** Urban Analytics with Python — Advanced Methods, Chapter 1
**Milan's local source:** purchased course notebook outside this repository
**Retype file:** `01_milan_original.ipynb`
**Current explanation scope:** Sections 1.1 and 1.2, which unlock Feature 1

## Chapter goal

Create one explicit study-area configuration, resolve its administrative boundary from OpenStreetMap, project it into an appropriate metric CRS, visually verify it, and persist reusable base geometry.

## OOHScout translation preview

| Milan's Manhattan setup | OOHScout adaptation |
|---|---|
| `PLACE = "Manhattan, New York"` | `PLACE = "McLennan County, Texas"` |
| EPSG:32618, UTM zone 18N | EPSG:32614, UTM zone 14N |
| Manhattan administrative boundary | McLennan County administrative boundary |
| Manhattan buildings become the chapter's base geometry | IH-35 becomes OOHScout's base geometry in F2 |
| Midtown test box | Waco development subset in F5 |

## Section 1.1 — Environment and imports

Milan creates a dedicated Python environment so every later notebook uses compatible versions of GeoPandas, OSMnx, Shapely, PyProj, Contextily, and the analytical libraries introduced later.

The import cell has four responsibilities:

- Suppress distracting warnings during the learning notebook.
- Load OSMnx for geocoding and OpenStreetMap features.
- Load GeoPandas and Shapely for vector data.
- Load Matplotlib and Contextily for visual verification.

Printing the GeoPandas and OSMnx versions is a reproducibility check. When behavior differs from Milan's output, package versions are the first thing to compare.

## Section 1.2 — The study-area pattern

### Configuration cell

```python
PLACE = "Manhattan, New York"
CRS_METRIC = 32618
CRS_GEOGRAPHIC = 4326
```

- `PLACE` is the human-readable query sent to the geocoder.
- `CRS_GEOGRAPHIC` is WGS 84 longitude/latitude, the coordinate system returned by OSM.
- `CRS_METRIC` is the local UTM projection used for areas and distances.

Retargeting requires changing the place, checking that the chosen metric CRS is appropriate for that place, and changing the published area used by the acceptance assertion. OOHScout uses EPSG:32614 for McLennan County. We do not calculate area in EPSG:4326 because degrees are angular units, not meters.

### Boundary-resolution cell

```python
admin_gdf = ox.geocode_to_gdf(PLACE)
admin_poly = admin_gdf.geometry.union_all()
admin_gdf_metric = admin_gdf.to_crs(epsg=CRS_METRIC)
study_area = admin_gdf_metric.geometry.union_all()
```

- `geocode_to_gdf` resolves the place name and returns its administrative geometry.
- `admin_poly` stays in WGS 84 and is suitable for OSMnx download calls.
- `to_crs` creates a projected copy rather than relabeling coordinates.
- `study_area` is the projected geometry owned by deterministic spatial code.

`union_all()` makes one geometry even if the returned boundary has multiple pieces. The OOHScout adaptation still asserts that the GeoDataFrame contains one administrative record and that its geometry is polygonal and valid.

### Area check

The projected geometry's `.area` is measured in square meters. Dividing by `1e6` converts square meters to square kilometers. A published reference area is a sanity check, not a replacement for inspecting the geometry.

### Satellite-basemap plot

Milan draws the boundary first and then asks Contextily for Esri World Imagery in the same CRS. If the CRS is wrong, the boundary may disappear, land in the wrong country, or appear at an implausible scale. Visual QA is therefore part of Feature 1 acceptance, not decoration.

## Techniques introduced

- [x] Central study-area configuration
- [x] Place-name geocoding with OSMnx
- [x] Geographic versus projected CRS discipline
- [x] Polygon union
- [x] Metric area calculation
- [x] Satellite-basemap verification
- [ ] Base-geometry ingestion and unique keys — continue when starting F2
- [ ] Test subset — continue when starting F5

## OOHScout features unlocked

- **F1** — Retargetable Study Area, started in this branch
- **F2** — IH-35 Base Geometry, next after F1 passes
- **F5** — Fast Waco test subset, later in this chapter

## Gotchas

- Changing a place without checking the corresponding metric CRS produces invalid measurements.
- `set_crs` labels coordinates; `to_crs` transforms coordinates. Feature 1 requires `to_crs`.
- Administrative area can include water, so compare like with like.
- A successful geocoder response does not prove it returned the intended jurisdiction; inspect the plot.
- Contextily and OSMnx require internet access on the first run.

## Next action for you

Retype Milan's Sections 1.1 and 1.2 into `01_milan_original.ipynb`, execute each cell, and compare the outputs with the purchased notebook. Then run the OOHScout adaptation one cell at a time.
