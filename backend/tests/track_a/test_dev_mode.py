import pytest
import geopandas as gpd
from shapely.geometry import Polygon, box
from oohscout.track_a_spatial.dev_mode import waco_urban_bbox, clip_to_bbox

def test_waco_urban_bbox_preserves_crs():
    # Waco bbox in WGS84 is (-97.20, 31.48, -97.05, 31.62)
    # Let's request it in EPSG:32614
    bbox = waco_urban_bbox(32614)
    
    # Check that it's a valid polygon
    assert isinstance(bbox, Polygon)
    assert bbox.is_valid
    
    # The X coordinates in EPSG:32614 for Texas should be roughly 600,000+
    bounds = bbox.bounds
    assert bounds[0] > 100000
    assert bounds[2] > 100000

def test_clip_to_bbox_reduces_size():
    # Create a dummy dataframe with two lines, one inside, one outside
    from shapely.geometry import LineString
    
    # A box from 0,0 to 10,10
    test_bbox = box(0, 0, 10, 10)
    
    # Line 1: entirely inside (intersects)
    line1 = LineString([(2, 2), (8, 8)])
    
    # Line 2: entirely outside (does not intersect)
    line2 = LineString([(20, 20), (30, 30)])
    
    # Line 3: crosses the boundary (intersects)
    line3 = LineString([(-5, -5), (5, 5)])
    
    gdf = gpd.GeoDataFrame(
        {'id': [1, 2, 3]},
        geometry=[line1, line2, line3],
        crs="EPSG:32614"
    )
    
    clipped = clip_to_bbox(gdf, test_bbox)
    
    # Should only keep line1 and line3
    assert len(clipped) == 2
    assert set(clipped['id']) == {1, 3}
    
    # Check index was reset
    assert list(clipped.index) == [0, 1]
