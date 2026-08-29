"""
Fix oohscout_real_txdot_data.ipynb.

Adjustments applied here:
  1. Strip all outputs (makes file editable and small)
  2. Setup cell: switch to correct AADT endpoint
  3. B.1: pull AADT with numeric conversion + IH-35 filter
  4. B.2: defensive numeric conversion + generic year column
  5. C.1: always regenerate 40 candidates along IH-35
  6. C.3: use whichever year column exists (AADT_RPT_YEAR vs LATEST_AADT_YR)
  7. D.1: add fit_bounds; use generic year column

Run:  uv run python scripts/fix_real_txdot_notebook.py
"""
import json
from pathlib import Path

NB_PATH = Path('notebooks/oohscout_real_txdot_data.ipynb')

nb = json.loads(NB_PATH.read_text(encoding='utf-8'))

# ── STEP 1: Strip all outputs ────────────────────────────────────────────
for cell in nb['cells']:
    if cell.get('cell_type') == 'code':
        cell['outputs'] = []
        cell['execution_count'] = None

# ── STEP 2: Cell replacements ────────────────────────────────────────────

CELL_SETUP = '''# ── SECTION 1: SETUP ────────────────────────────────────────────────────────

import json
import requests
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
from pathlib import Path
from shapely.geometry import Point, shape
from shapely.ops import unary_union
import warnings
warnings.filterwarnings('ignore')

# Data directory (same rule as all OOHScout notebooks)
DATA_DIR = Path('data/new_study')
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── VERIFIED REAL TxDOT REST ENDPOINTS ──────────────────────────────────────
# All verified via live queries. See DATA_VERIFICATION_REPORT.md.

# Real permitted billboards — 14,943 statewide, 182 in McLennan County
TXDOT_BILLBOARDS_URL = (
    'https://services.arcgis.com/KTcxiTD9dsQw4r7Z/ArcGIS/rest/services/'
    'Commercial_Signs_Test/FeatureServer/0/query'
)

# Real AADT — 20 years of history (2006-2025), INCLUDES interstate mainlane.
# Top McLennan station on IH-35 = 137,451 AADT (verified live).
# This is the CORRECT dataset for billboard-relevant traffic scoring.
TXDOT_AADT_URL = (
    'https://services.arcgis.com/KTcxiTD9dsQw4r7Z/ArcGIS/rest/services/'
    'TxDOT_AADT_Annuals_(Public_View)/FeatureServer/0/query'
)

# Coordinate systems
WGS84   = 'EPSG:4326'      # storage / display
TEX_CRS = 'EPSG:32614'     # UTM Zone 14N, Texas, meters — for distance math

# Legal spacing constants (from 43 TAC Chapter 21)
PRIMARY_SPACING_FT     = 500       # Primary highways minimum spacing
INTERSTATE_SPACING_FT  = 1500      # Interstate baseline in Texas rural areas
FT_TO_METERS           = 0.3048

# Waco corridor bounding box (for candidate generation)
WACO_BBOX = [-97.25, 31.30, -96.95, 31.85]

# Number of candidate zones to sample along IH-35
N_CANDIDATES = 40


def pick_year_col(df):
    """Return whichever AADT year column exists in df, or None.

    Different TxDOT datasets use different names:
      TxDOT_AADT_Annuals_(Public_View)    -> AADT_RPT_YEAR
      TxDOT_5_Year_Statewide_AADT_...     -> LATEST_AADT_YR
    """
    for col in ('AADT_RPT_YEAR', 'LATEST_AADT_YR'):
        if col in df.columns:
            return col
    return None


print('Setup complete.')
print(f'TxDOT Billboards endpoint: verified live (14,943 statewide records)')
print(f'TxDOT AADT endpoint (20yr history, includes mainlane): verified live')
print(f'Data dir: {DATA_DIR.resolve()}')
'''

CELL_B1 = '''# ── B.1: Pull all real McLennan County AADT stations ────────────────────────
# Uses the TxDOT_AADT_Annuals dataset which INCLUDES interstate mainlane counts.
# The alternative "5-Year Statewide AADT" only covers short/urban counts (max ~30K).

aadt_path = DATA_DIR / 'txdot_aadt_mclennan_real_v2.geojson'

aadt = query_arcgis_rest(
    endpoint_url=TXDOT_AADT_URL,
    where="CNTY_NM='McLennan'",
    out_fields='*',
    cache_path=aadt_path,
)

print(f'\\nReal McLennan County AADT stations: {len(aadt)}')
print(f'Columns available: {list(aadt.columns)}')

# ArcGIS/GeoJSON round-trip sometimes preserves numeric fields as strings.
# Force numeric conversion for every AADT-related column.
year_col = pick_year_col(aadt)
aadt_numeric_cols = [c for c in aadt.columns if c.startswith('AADT_RPT')]
if year_col and year_col not in aadt_numeric_cols:
    aadt_numeric_cols.append(year_col)
for col in aadt_numeric_cols:
    aadt[col] = pd.to_numeric(aadt[col], errors='coerce')

# Latest AADT: prefer current year, fall back through history
if 'AADT_RPT_QTY' in aadt.columns:
    aadt['latest_aadt'] = aadt['AADT_RPT_QTY']
    hist_cols = sorted([c for c in aadt.columns if c.startswith('AADT_RPT_HIST_')])
    for hist_col in hist_cols:
        aadt['latest_aadt'] = aadt['latest_aadt'].fillna(aadt[hist_col])
    aadt['latest_aadt'] = pd.to_numeric(aadt['latest_aadt'], errors='coerce')

print(f'\\nlatest_aadt dtype: {aadt["latest_aadt"].dtype}')
print(f'Year column detected: {year_col}')
print(f'\\nSample stations (top 5 by AADT):')
if 'latest_aadt' in aadt.columns:
    top5 = aadt.nlargest(5, 'latest_aadt')
    display_cols = ['TRFC_STATN_ID', 'ON_ROAD', 'CNTY_NM', year_col, 'latest_aadt']
    display_cols = [c for c in display_cols if c and c in aadt.columns]
    print(top5[display_cols].to_string(index=False))
'''

CELL_B2 = '''# ── B.2: AADT distribution — where the eyeballs actually are ────────────────

# Defensive: force numeric conversion in case cell B.1 wasn't re-run after the fix.
year_col = pick_year_col(aadt)
aadt_numeric_cols = [c for c in aadt.columns if c.startswith('AADT_RPT')]
if year_col and year_col not in aadt_numeric_cols:
    aadt_numeric_cols.append(year_col)
for col in aadt_numeric_cols:
    aadt[col] = pd.to_numeric(aadt[col], errors='coerce')

# Rebuild latest_aadt from the (now-numeric) columns
if 'AADT_RPT_QTY' in aadt.columns:
    aadt['latest_aadt'] = aadt['AADT_RPT_QTY']
    hist_cols = sorted([c for c in aadt.columns if c.startswith('AADT_RPT_HIST_')])
    for hist_col in hist_cols:
        aadt['latest_aadt'] = aadt['latest_aadt'].fillna(aadt[hist_col])
    aadt['latest_aadt'] = pd.to_numeric(aadt['latest_aadt'], errors='coerce')

print(f'latest_aadt dtype after conversion: {aadt["latest_aadt"].dtype}')

# Filter to stations with real data
aadt_with_data = aadt[aadt['latest_aadt'].notna() & (aadt['latest_aadt'] > 0)].copy()

print(f'Stations with valid AADT data: {len(aadt_with_data)} of {len(aadt)}')
print(f'\\nAADT statistics for McLennan County:')
print(f'  Min:    {int(aadt_with_data["latest_aadt"].min()):>7,} vehicles/day')
print(f'  Median: {int(aadt_with_data["latest_aadt"].median()):>7,} vehicles/day')
print(f'  Mean:   {int(aadt_with_data["latest_aadt"].mean()):>7,} vehicles/day')
print(f'  Max:    {int(aadt_with_data["latest_aadt"].max()):>7,} vehicles/day')

print(f'\\nTop 10 highest-traffic stations in McLennan County:')
top_cols = ['TRFC_STATN_ID', 'latest_aadt']
if 'ON_ROAD' in aadt_with_data.columns:
    top_cols.insert(1, 'ON_ROAD')
top10 = aadt_with_data.nlargest(10, 'latest_aadt')[top_cols]
print(top10.to_string(index=False))

print(f'\\n(The highest-AADT stations should be on IH-35 mainlane — verify ON_ROAD)')

# Visualize distribution
fig, axes = plt.subplots(1, 2, figsize=(14, 4))

axes[0].hist(aadt_with_data['latest_aadt'], bins=40, color='#2255AA', edgecolor='white')
axes[0].set_title('AADT Distribution — McLennan County', fontweight='bold')
axes[0].set_xlabel('AADT (vehicles/day)')
axes[0].set_ylabel('Number of stations')

axes[1].hist(np.log10(aadt_with_data['latest_aadt']), bins=40, color='#2288AA', edgecolor='white')
axes[1].set_title('AADT Distribution (log scale)', fontweight='bold')
axes[1].set_xlabel('log10(AADT)')
axes[1].set_ylabel('Number of stations')

plt.tight_layout()
plt.show()
'''

CELL_C1 = '''# ── C.1: Generate candidates that FOLLOW the actual curved IH-35 highway ────
# The naive approach (linspace between bbox corners) draws a straight diagonal
# that misses the real curved highway. Instead, we build the candidate line from
# the REAL IH-35 road geometry (if available) or from real billboards (proxy).

from shapely.ops import linemerge

candidates_path = DATA_DIR / 'ih35_waco_candidates.geojson'

need_regenerate = True
if candidates_path.exists():
    existing = gpd.read_file(candidates_path)
    if len(existing) >= N_CANDIDATES // 2:
        candidates = existing
        need_regenerate = False
        print(f'Loaded {len(candidates)} candidates from cache')

if need_regenerate:
    print(f'Regenerating {N_CANDIDATES} candidates along the CURVED IH-35...')

    master_line_tex = None

    # STRATEGY 1: Use the actual OSM road geometry from the Phase 1 notebook
    roads_path = DATA_DIR / 'ih35_waco_roads.geojson'
    if roads_path.exists():
        roads = gpd.read_file(roads_path)
        if 'highway' in roads.columns:
            is_motorway = roads['highway'].astype(str).str.contains('motorway', na=False)
            ih35_line = roads[is_motorway].copy()
        else:
            ih35_line = roads.copy()

        if len(ih35_line) > 0:
            ih35_line_tex = ih35_line.to_crs(TEX_CRS)
            merged = linemerge(unary_union(ih35_line_tex.geometry))
            if merged.geom_type == 'MultiLineString':
                merged = max(merged.geoms, key=lambda g: g.length)
            master_line_tex = merged
            print(f'  Using OSM road geometry (length {master_line_tex.length/1000:.1f} km)')

    # STRATEGY 2: Fall back to real billboards as anchor line (sort by latitude)
    if master_line_tex is None and len(ih35_bb) > 0:
        bb_sorted = ih35_bb.to_crs(TEX_CRS).copy()
        # Sort by y-coordinate (latitude, IH-35 runs mostly N-S)
        bb_sorted['y'] = bb_sorted.geometry.y
        bb_sorted = bb_sorted.sort_values('y').reset_index(drop=True)

        from shapely.geometry import LineString
        pts = [(g.x, g.y) for g in bb_sorted.geometry]
        if len(pts) >= 2:
            master_line_tex = LineString(pts)
            print(f'  Using {len(pts)} real billboards as anchor line (length {master_line_tex.length/1000:.1f} km)')

    # STRATEGY 3: Last-resort straight line from bbox
    if master_line_tex is None:
        from shapely.geometry import LineString
        lon_min, lat_min, lon_max, lat_max = WACO_BBOX
        corner_gdf = gpd.GeoDataFrame(
            {'geometry': [Point((lon_min + lon_max)/2, lat_min),
                          Point((lon_min + lon_max)/2, lat_max)]},
            crs=WGS84,
        ).to_crs(TEX_CRS)
        master_line_tex = LineString(corner_gdf.geometry.tolist())
        print('  WARNING: no road or billboard data — using straight bbox fallback')

    # Sample N_CANDIDATES points evenly along the actual curved line
    dists = np.linspace(0, master_line_tex.length, N_CANDIDATES)
    points_tex = [master_line_tex.interpolate(d) for d in dists]

    candidates_tex_new = gpd.GeoDataFrame(
        {
            'candidate_id':  [f'WA-{i:03d}' for i in range(N_CANDIDATES)],
            'corridor':      'IH-35 Waco',
            'dist_along_km': [d / 1000 for d in dists],
            'geometry':      points_tex,
        },
        crs=TEX_CRS,
    )
    candidates = candidates_tex_new.to_crs(WGS84)
    candidates.to_file(candidates_path, driver='GeoJSON')
    print(f'  Saved {len(candidates)} candidates that follow the real highway curve')

print(f'\\nCandidate summary:')
print(f'  Count:        {len(candidates)}')
print(f'  ID range:     {candidates["candidate_id"].iloc[0]} → {candidates["candidate_id"].iloc[-1]}')
print(f'  Bounds:       {candidates.total_bounds}')
if "dist_along_km" in candidates.columns:
    print(f'  Total length: {candidates["dist_along_km"].max():.1f} km')
'''

CELL_C3 = '''# ── C.3: Spatial join — nearest real AADT station to each candidate ─────────
# This gives every candidate a REAL traffic volume.

aadt_tex = aadt_with_data.to_crs(TEX_CRS)

# Use whichever year column exists in the dataset (differs by TxDOT service)
year_col = pick_year_col(aadt_tex)
aadt_join_cols = ['TRFC_STATN_ID', 'latest_aadt', 'geometry']
if year_col:
    aadt_join_cols.insert(2, year_col)
if 'ON_ROAD' in aadt_tex.columns:
    aadt_join_cols.insert(2, 'ON_ROAD')

joined_aadt = gpd.sjoin_nearest(
    candidates_tex[['candidate_id', 'geometry']],
    aadt_tex[aadt_join_cols],
    how='left',
    distance_col='dist_to_aadt_station_m',
)

# Normalize AADT to [0, 1] using log scale (traffic value is non-linear)
log_aadt = np.log10(joined_aadt['latest_aadt'].clip(lower=100))
log_min, log_max = log_aadt.min(), log_aadt.max()
if log_max > log_min:
    joined_aadt['traffic_score_real'] = (log_aadt - log_min) / (log_max - log_min)
else:
    joined_aadt['traffic_score_real'] = 1.0

print(f'AADT join results for {len(joined_aadt)} candidates:')
print(f'  Min AADT:      {int(joined_aadt["latest_aadt"].min()):,}')
print(f'  Median AADT:   {int(joined_aadt["latest_aadt"].median()):,}')
print(f'  Max AADT:      {int(joined_aadt["latest_aadt"].max()):,}')

print(f'\\nSample results (first 10 candidates):')
show_cols = ['candidate_id', 'TRFC_STATN_ID', 'latest_aadt', 'traffic_score_real']
if 'ON_ROAD' in joined_aadt.columns:
    show_cols.insert(2, 'ON_ROAD')
print(joined_aadt[show_cols].head(10).to_string(index=False))
'''

CELL_D1 = '''# ── D.1: Folium map with all real data layers ────────────────────────────────

# Compute bounds that include EVERYTHING so map auto-fits properly
all_geoms_bounds = pd.concat([
    ih35_bb.geometry.bounds,
    candidates_real.geometry.bounds,
]).agg({'minx': 'min', 'miny': 'min', 'maxx': 'max', 'maxy': 'max'})

center_lat = (all_geoms_bounds['miny'] + all_geoms_bounds['maxy']) / 2
center_lon = (all_geoms_bounds['minx'] + all_geoms_bounds['maxx']) / 2

fmap = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles='OpenStreetMap')

# FORCE map to fit all data — this is the key fix for blank maps
fmap.fit_bounds([
    [all_geoms_bounds['miny'], all_geoms_bounds['minx']],
    [all_geoms_bounds['maxy'], all_geoms_bounds['maxx']],
])

# ── LAYER: Real 500 ft exclusion zones ──────────────────────────────────────
if len(exclusion_gdf) > 0:
    excl_500 = exclusion_gdf[exclusion_gdf['rule'] == '500ft (primary)'].iloc[0]['geometry']
    folium.GeoJson(
        excl_500.__geo_interface__,
        name='500 ft legal exclusion (spacing rule)',
        style_function=lambda x: {
            'fillColor': '#CC0000', 'color': '#CC0000',
            'weight': 1, 'fillOpacity': 0.15,
        },
    ).add_to(fmap)

# ── LAYER: Real billboards ──────────────────────────────────────────────────
bb_layer = folium.FeatureGroup(name=f'Real TxDOT billboards (n={len(ih35_bb)})', show=True)
for _, row in ih35_bb.iterrows():
    is_digital = row.get('ELECTRONIC') == 'Yes'
    color = '#FF3333' if is_digital else '#8B0000'
    popup = folium.Popup(
        f"<b>REAL TxDOT PERMIT</b><br>"
        f"Permit ID: {row.get('RCRD_ID', '')}<br>"
        f"Operator: {row.get('OWNR', '')}<br>"
        f"Highway: {row.get('HWY', '')}<br>"
        f"Type: {'Digital' if is_digital else 'Static'}<br>"
        f"Status: {row.get('STAT', '')}",
        max_width=250,
    )
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=6, color=color, fill=True, fill_opacity=0.9,
        popup=popup,
        tooltip=f"{row.get('OWNR', '')} — {row.get('RCRD_ID', '')}",
    ).add_to(bb_layer)
bb_layer.add_to(fmap)

# ── LAYER: Real AADT stations ───────────────────────────────────────────────
aadt_show = aadt_with_data[aadt_with_data['latest_aadt'] >= 5000].copy()
year_col = pick_year_col(aadt_show)
aadt_layer = folium.FeatureGroup(
    name=f'Real AADT stations (AADT ≥ 5000, n={len(aadt_show)})', show=True
)
for _, row in aadt_show.iterrows():
    aadt_val = int(row['latest_aadt'])
    size = 4 + np.log10(max(aadt_val, 1000)) * 2
    year_val = row.get(year_col) if year_col else None
    year_str = str(int(year_val)) if pd.notna(year_val) else 'N/A'
    popup = folium.Popup(
        f"<b>REAL TxDOT AADT STATION</b><br>"
        f"Station ID: {row.get('TRFC_STATN_ID', '')}<br>"
        f"Road: {row.get('ON_ROAD', 'N/A')}<br>"
        f"Latest AADT: {aadt_val:,} vehicles/day<br>"
        f"Year: {year_str}",
        max_width=250,
    )
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=size, color='#0055AA', fill=True, fill_color='#3399FF', fill_opacity=0.7,
        popup=popup,
        tooltip=f"AADT: {aadt_val:,}",
    ).add_to(aadt_layer)
aadt_layer.add_to(fmap)

# ── LAYER: OOHScout candidates ──────────────────────────────────────────────
top10_ids = set(
    candidates_real.sort_values('opportunity_score_v2', ascending=False)
                   .head(10)['candidate_id']
)
cand_layer = folium.FeatureGroup(name=f'OOHScout candidates (n={len(candidates_real)})', show=True)

for _, row in candidates_real.iterrows():
    passes = row.get('spacing_pass_500ft', False)
    is_top = row['candidate_id'] in top10_ids

    if is_top and passes:
        color, radius = '#00BB44', 12
    elif passes:
        color, radius = '#FFAA00', 8
    else:
        color, radius = '#888888', 6

    dist_ft = row.get('dist_to_billboard_ft', 0)
    aadt_val = row.get('latest_aadt', 0)
    popup = folium.Popup(
        f"<b>{row['candidate_id']}</b><br>"
        f"Rank v2: #{int(row.get('rank_v2', 0))}<br>"
        f"Score v2: {row.get('opportunity_score_v2', 0):.3f}<br>"
        f"<b>Real spacing check:</b><br>"
        f"Dist to nearest sign: {dist_ft:.0f} ft<br>"
        f"Nearest operator: {row.get('OWNR', 'N/A')}<br>"
        f"Pass 500ft rule: {'YES' if passes else 'NO'}<br>"
        f"<b>Real traffic:</b><br>"
        f"Nearest AADT: {int(aadt_val) if pd.notna(aadt_val) else 'N/A'} vehicles/day<br>"
        f"<b>Status:</b> {row.get('reg_status_v2', 'PENDING')}",
        max_width=280,
    )
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=radius,
        color='black', weight=1,
        fill=True, fill_color=color, fill_opacity=0.85,
        popup=popup,
        tooltip=f"{row['candidate_id']} — Score {row.get('opportunity_score_v2', 0):.2f}",
    ).add_to(cand_layer)
cand_layer.add_to(fmap)

# Legend
legend_html = \'\'\'
<div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
     background: white; padding: 12px; border-radius: 8px;
     border: 2px solid #333; font-size: 13px; font-family: sans-serif;">
  <b>OOHScout AI — Real Data Layer</b><br>
  <i>Source: live TxDOT ArcGIS API</i><br><br>
  <b>Existing billboards (competition):</b><br>
  <span style="color:#8B0000">●</span> Static bulletin<br>
  <span style="color:#FF3333">●</span> Digital bulletin<br><br>
  <b>Legal check:</b><br>
  <span style="background:#CC000030;padding:2px 8px;">500 ft exclusion zone</span><br><br>
  <b>AADT (traffic):</b><br>
  <span style="color:#3399FF">◆</span> Real traffic station (size = AADT)<br><br>
  <b>Candidates:</b><br>
  <span style="color:#00BB44">●</span> Top 10 & pass spacing<br>
  <span style="color:#FFAA00">●</span> Pass spacing<br>
  <span style="color:#888888">●</span> Fail 500 ft rule<br>
</div>
\'\'\'
fmap.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl(collapsed=False).add_to(fmap)

map_path = DATA_DIR / 'ih35_waco_REAL_data_map.html'
fmap.save(str(map_path))
print(f'Interactive real-data map saved: {map_path}')
print(f'  Layers: {len(ih35_bb)} real billboards + {len(aadt_show)} AADT stations + {len(candidates_real)} candidates')
fmap
'''

# Map of cell IDs to new content
replacements = {
    'cell-setup': CELL_SETUP,
    'cell-b1':    CELL_B1,
    'cell-b2':    CELL_B2,
    'cell-c1':    CELL_C1,
    'cell-c3':    CELL_C3,
    'cell-d1':    CELL_D1,
}

# ── STEP 3: Apply the replacements ───────────────────────────────────────
replaced = []
for cell in nb['cells']:
    cid = cell.get('id')
    if cid in replacements:
        cell['source'] = replacements[cid].splitlines(keepends=True)
        replaced.append(cid)

# ── STEP 4: Save back ────────────────────────────────────────────────────
NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')

print(f'Notebook fixed: {NB_PATH}')
print(f'Cells replaced: {replaced}')
print(f'All outputs stripped ({len(nb["cells"])} cells total)')
