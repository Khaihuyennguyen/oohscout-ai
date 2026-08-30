# F2 — Milan Explanation (Pointer)

F2 reuses the UA Advanced Chapter 1 pattern that [F1's 02_milan_explanation.md](../ua_advanced_ch01_setup/02_milan_explanation.md) covers in detail. Rather than duplicate 300 lines, this doc lists the two things F2 does differently.

## Difference 1 — different OSM feature class

Milan / F1 fetched building footprints:

```python
buildings = ox.features_from_polygon(admin_poly, tags={"building": True})
```

F2 fetches motorway line segments:

```python
highways = ox.features_from_polygon(admin_poly, tags={"highway": ["motorway"]})
```

`admin_poly` is the same object in both — F1's WGS 84 study-area polygon. The only change is the `tags` dict, which controls what OSM sends back.

## Difference 2 — different geometry filter

Milan / F1 kept only `Polygon` / `MultiPolygon`:

```python
is_polygon = buildings.geometry.type.isin(["Polygon", "MultiPolygon"])
buildings = buildings[is_polygon].copy()
```

F2 keeps only `LineString` / `MultiLineString`:

```python
is_line = raw.geometry.geom_type.isin(["LineString", "MultiLineString"])
raw = raw[is_line].copy()
```

The reason is identical — OSM occasionally returns a `Point` for a motorway "node" (e.g. an exit marker) that would break length math. Filter fast, filter early.

## Everything else transfers unchanged

- Two-CRS discipline (WGS 84 in, projected metric out)
- `admin_poly` as the search polygon
- Cache-first pattern to avoid re-hitting Overpass
- `assert osmid.is_unique` after the geometry filter
- `.gpkg` (not GeoJSON) because we save projected coordinates

## One F2-specific gotcha

OSMnx sometimes returns the same OSM way twice with byte-identical geometry. Milan's building example didn't hit this because building queries are typically clean. F2 handles it explicitly:

```python
matched = matched.drop_duplicates(subset=["osmid"], keep="first")
```

The dedupe is safe because the duplicated rows are true copies — verified by comparing `.geometry.equals()`. If you drop the dedupe, the `assert osmid.is_unique` fires.

## Where to go for the deep explanation of F2

Read [04_adaptation_explanation.md](04_adaptation_explanation.md) for the WHAT / WHY / HOW walkthrough of each cell in [03_oohscout_adaptation.ipynb](03_oohscout_adaptation.ipynb).
