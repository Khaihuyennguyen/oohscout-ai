import geopandas as gpd
from shapely.geometry import box, Polygon
import pyproj
from shapely.ops import transform

WACO_URBAN_BBOX_WGS84 = (-97.20, 31.48, -97.05, 31.62)

def waco_urban_bbox(crs_metric: int) -> Polygon:
    """
    Returns the Waco urban DEV_MODE bounding box as a Polygon, 
    projected to the requested metric CRS.
    """
    # Create the bounding box polygon in WGS84
    minx, miny, maxx, maxy = WACO_URBAN_BBOX_WGS84
    bbox_wgs84 = box(minx, miny, maxx, maxy)
    
    # Project to the metric CRS
    project = pyproj.Transformer.from_crs(
        pyproj.CRS("EPSG:4326"), 
        pyproj.CRS(f"EPSG:{crs_metric}"), 
        always_xy=True
    ).transform
    
    bbox_metric = transform(project, bbox_wgs84)
    return bbox_metric

def clip_to_bbox(gdf: gpd.GeoDataFrame, bbox: Polygon) -> gpd.GeoDataFrame:
    """
    Clips a GeoDataFrame to a bounding box polygon using an intersects predicate.
    Returns a new GeoDataFrame with the index reset.
    """
    # Use intersects instead of within to keep line segments that cross the boundary
    clipped = gdf[gdf.intersects(bbox)].copy()
    return clipped.reset_index(drop=True)
