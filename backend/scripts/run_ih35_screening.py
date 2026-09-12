"""Run the MVP preliminary screening for IH-35 through McLennan County.

The concrete caller: every McLennan / IH-35 / Waco value lives here, the
modules it calls are generic. Downloads are cached in backend/data/processed/
with provenance sidecars; results go to

- backend/data/processed/mclennan_ih35_screening.gpkg   (stretches, candidates, existing_signs)
- backend/data/outputs/mclennan_ih35_candidates.csv
- backend/data/outputs/mclennan_ih35_screening_map.html

Run:  uv run python backend/scripts/run_ih35_screening.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
from oohscout.data.arcgis import load_or_fetch_arcgis_layer
from oohscout.data.provenance import SourceRecord, write_source_yaml
from oohscout.rules import (
    ETJ_REACH_LARGE_CITY,
    FT_TO_M,
    TX_CERTIFIED_CITY,
    TX_FREEWAY_SPACING,
    TX_HIGHWAY_FACILITIES,
    WACO_CAP_AND_REPLACE,
)
from oohscout.track_a_spatial import (
    build_milepost_scale,
    load_or_build_corridor_buffer,
    load_or_build_highway_centerline,
    load_or_build_reference_lines,
    load_or_build_study_area,
    merge_stretches,
    place_candidates,
    prepare_existing_signs,
    probe_points,
    screen_probes,
    select_highway_signs,
)

PLACE = "McLennan County, Texas"
CRS = 32614
ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "backend" / "data" / "processed"
OUTPUTS = ROOT / "backend" / "data" / "outputs"
NOTES_COPY = ROOT.parent / "ai-portfolio" / "docs" / "OOHSCOUT" / "mclennan_ih35_screening_map.html"

ARCGIS = "https://services.arcgis.com/KTcxiTD9dsQw4r7Z/ArcGIS/rest/services"
TXDOT_SIGNS = f"{ARCGIS}/Commercial_Signs_Test/FeatureServer/0"
CERTIFIED_CITY_SIGNS = f"{ARCGIS}/TxDOT_Certified_City_Signs/FeatureServer/0"
REFERENCE_MARKERS = f"{ARCGIS}/TxDOT_Reference_Markers/FeatureServer/0"
CITY_BOUNDARIES = f"{ARCGIS}/TxDOT_City_Boundaries/FeatureServer/0"

IH35_PATTERN = r"\b(?:IH|I|INTERSTATE)[\s-]*35\b|KULTGEN"
ACTIVE_STATUSES = {"Active", "Present", "PENDING"}
CERTIFIED = {"Waco": WACO_CAP_AND_REPLACE}
MARGIN_DEG = 0.02  # ~2 km: signs just across the county line still count for spacing

STEP_M = 10.0
TOLERANCE_M = 15.0

COLORS = {
    "open": "#1a9850",
    "near_limit": "#fdae61",
    "blocked": "#d73027",
    "city_rules": "#7b3294",
    "possible_etj": "#f1b6da",
}
LABELS = {
    "open": "Open — passed automated spacing + ramp screening (REVIEW)",
    "near_limit": "Near a limit — within ±15 m (REVIEW)",
    "blocked": "Blocked — too close to a sign or ramp (FAIL)",
    "city_rules": "Waco city rules — cap-and-replace (REVIEW)",
    "possible_etj": "Possible Waco ETJ — confirm with the city (REVIEW)",
}


def _txdot_source(name: str, url: str, notes: str) -> SourceRecord:
    return SourceRecord(
        source_name=name,
        source_url=url,
        record_count=0,
        license="Public government data (TxDOT Open Data)",
        commercial_use_allowed="true (public record; confirm TxDOT terms before resale)",
        redistribution_allowed="true (public record; confirm TxDOT terms before resale)",
        retrieval_method="ArcGIS REST query, bbox = McLennan County + 0.02 deg margin",
        authority="Texas Department of Transportation",
        notes=notes,
    )


def load_inputs() -> dict:
    study = load_or_build_study_area(place=PLACE, crs_metric=CRS, cache_dir=PROCESSED)
    corridor = load_or_build_highway_centerline(admin_poly=study.admin_poly, cache_dir=PROCESSED, crs_metric=CRS)
    zone = load_or_build_corridor_buffer(
        corridor.corridor_gdf_metric, study.admin_gdf_metric, PROCESSED, cache_slug="mclennan_ih35_buffer"
    )
    west, south, east, north = study.admin_gdf.total_bounds
    bbox = (west - MARGIN_DEG, south - MARGIN_DEG, east + MARGIN_DEG, north + MARGIN_DEG)

    signs = load_or_fetch_arcgis_layer(
        TXDOT_SIGNS, PROCESSED / "txdot_commercial_signs_mclennan_margin.gpkg", bbox=bbox,
        source=_txdot_source("TxDOT commercial sign permits", TXDOT_SIGNS,
                             "All counties inside the bbox, so signs across the county line count for spacing."),
    )
    city_signs = load_or_fetch_arcgis_layer(
        CERTIFIED_CITY_SIGNS, PROCESSED / "txdot_certified_city_signs_mclennan_margin.gpkg", bbox=bbox,
        source=_txdot_source("TxDOT certified-city sign permits", CERTIFIED_CITY_SIGNS,
                             "Signs permitted by certified cities (Waco) — missing from the TxDOT permit layer."),
    )
    markers = load_or_fetch_arcgis_layer(
        REFERENCE_MARKERS, PROCESSED / "txdot_ih35_reference_markers_mclennan_margin.gpkg", bbox=bbox,
        where="RTE_NM = 'IH0035-KG'",
        source=_txdot_source("TxDOT reference markers, IH-35 main roadbed", REFERENCE_MARKERS,
                             "Mileposts (MRKR_NBR) on roadbed KG; used to label positions like MP 331.4."),
    )
    cities = load_or_fetch_arcgis_layer(
        CITY_BOUNDARIES, PROCESSED / "txdot_city_boundaries_mclennan_margin.gpkg", bbox=bbox,
        source=_txdot_source("TxDOT city boundaries", CITY_BOUNDARIES, "Incorporated city limits."),
    )

    ramps_path = PROCESSED / "mclennan_ih35_ramps.gpkg"
    if ramps_path.exists():
        ramps = gpd.read_file(ramps_path)
    else:
        zone_wgs84 = zone.buffer_gdf_metric.to_crs(4326).geometry.iloc[0]
        raw = ox.features_from_polygon(zone_wgs84, tags={"highway": "motorway_link"}).reset_index()
        raw = raw[raw.geometry.geom_type.isin(["LineString", "MultiLineString"])]
        ramps = raw[["geometry"]].to_crs(CRS)
        ramps.to_file(ramps_path, driver="GPKG")
        write_source_yaml(ramps_path, SourceRecord(
            source_name="OpenStreetMap highway=motorway_link inside the 500 m IH-35 zone",
            source_url="https://www.openstreetmap.org (Overpass via osmnx)", record_count=len(ramps),
            license="Open Database License (ODbL) 1.0", commercial_use_allowed=True, redistribution_allowed=True,
            retrieval_method="osmnx.features_from_polygon(zone, highway=motorway_link)",
            authority="OpenStreetMap contributors",
            notes="Ramps/links used for the 43 TAC §21.179 highway-facilities check. Attribution: © OpenStreetMap contributors.",
        ))

    return {"study": study, "corridor": corridor, "signs": signs, "city_signs": city_signs,
            "markers": markers, "cities": cities, "ramps": ramps}


def combine_signs(signs: gpd.GeoDataFrame, city_signs: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    txdot = select_highway_signs(signs, hwy_col="HWY", pattern=IH35_PATTERN)
    txdot = txdot[txdot["STAT"].isin(ACTIVE_STATUSES)]
    waco = select_highway_signs(city_signs, hwy_col="HWY", pattern=IH35_PATTERN)
    both = pd.concat(
        [
            gpd.GeoDataFrame({"permit": txdot["RCRD_ID"].astype(str), "owner": txdot["OWNR"],
                              "source": "TxDOT permit"}, geometry=txdot.geometry, crs=4326),
            gpd.GeoDataFrame({"permit": "WACO-" + waco["CITY_PRMT_NBR"].astype(str), "owner": waco["SIGN_OWNR"],
                              "source": "Waco city permit"}, geometry=waco.geometry, crs=4326),
        ],
        ignore_index=True,
    )
    return gpd.GeoDataFrame(both, geometry="geometry", crs=4326).to_crs(CRS)


def nearest_sign_ft(candidates: gpd.GeoDataFrame, signs: gpd.GeoDataFrame) -> list[float]:
    out = []
    for direction, chainage in zip(candidates["direction"], candidates["chainage_m"]):
        same = signs.loc[signs["direction"] == direction, "chainage_m"].to_numpy()
        out.append(float(np.abs(same - chainage).min() / FT_TO_M) if len(same) else float("inf"))
    return out


def build_map(study, stretches, candidates, signs) -> folium.Map:
    stretches_wgs = stretches.to_crs(4326)
    centre = study.admin_gdf.geometry.iloc[0].centroid
    fmap = folium.Map(location=[centre.y, centre.x], zoom_start=10, tiles="CartoDB positron")
    folium.GeoJson(study.admin_gdf, name="McLennan County",
                   style_function=lambda f: {"color": "#333", "weight": 1, "fillOpacity": 0}).add_to(fmap)
    for screen, colour in COLORS.items():
        part = stretches_wgs[stretches_wgs["screen"] == screen]
        if part.empty:
            continue
        part = part.assign(length_ft=(part["length_m"] / FT_TO_M).round(0))
        folium.GeoJson(
            part[["side", "city", "screen", "citation", "blockers", "length_ft", "geometry"]],
            name=LABELS[screen],
            style_function=lambda f, c=colour: {"color": c, "weight": 6, "opacity": 0.85},
            tooltip=folium.GeoJsonTooltip(["side", "screen", "citation", "blockers", "length_ft"]),
        ).add_to(fmap)
    sign_layer = folium.FeatureGroup(name="Existing signs (TxDOT + Waco permits)")
    for s in signs.to_crs(4326).itertuples():
        folium.CircleMarker([s.geometry.y, s.geometry.x], radius=3, color="#000" if s.source == "TxDOT permit" else "#555",
                            fill=True, tooltip=f"{s.permits} — {s.owner} ({s.source}), side {s.side}").add_to(sign_layer)
    sign_layer.add_to(fmap)
    cand_layer = folium.FeatureGroup(name="Candidate spots (REVIEW)")
    for c in candidates.to_crs(4326).itertuples():
        folium.Marker(
            [c.geometry.y, c.geometry.x],
            icon=folium.Icon(color="green", icon="flag"),
            tooltip=c.candidate_id,
            popup=folium.Popup(
                f"<b>{c.candidate_id}</b><br>Side {c.side} ({c.direction} traffic), MP {c.milepost:.2f}<br>"
                f"Nearest existing sign on this side: {c.nearest_sign_ft:,.0f} ft<br>"
                f"<b>REVIEW</b> — {c.reason}", max_width=360),
        ).add_to(cand_layer)
    cand_layer.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap


def main() -> int:
    inputs = load_inputs()
    study, corridor = inputs["study"], inputs["corridor"]
    refs = load_or_build_reference_lines(corridor.corridor_gdf_metric, PROCESSED, cache_slug="mclennan_ih35_reference_lines")
    write_source_yaml(PROCESSED / "mclennan_ih35_reference_lines.gpkg", SourceRecord(
        source_name="Derived — IH-35 reference lines, one per direction of travel (McLennan County)",
        source_url="derived: mclennan_ih35_centerline.gpkg", record_count=len(refs),
        license="Open Database License (ODbL) 1.0", commercial_use_allowed=True, redistribution_allowed=True,
        retrieval_method="build_reference_lines(): travel direction per segment -> line_merge(directed=True)",
        authority="OpenStreetMap contributors (parent dataset)",
        notes="Attribution required: © OpenStreetMap contributors.",
    ))
    signs = prepare_existing_signs(combine_signs(inputs["signs"], inputs["city_signs"]), refs, id_col="permit")
    markers = inputs["markers"].to_crs(CRS).drop_duplicates("MRKR_NBR")
    scale = build_milepost_scale(refs, markers, marker_col="MRKR_NBR")
    cities = inputs["cities"].to_crs(CRS)

    screened = screen_probes(
        probe_points(refs, STEP_M), signs=signs, sign_id_col="permits",
        study_area=study.admin_gdf_metric, cities=cities, city_name_col="CITY_NM",
        certified_cities=CERTIFIED, ramps=inputs["ramps"], spacing_rule=TX_FREEWAY_SPACING,
        facilities_rule=TX_HIGHWAY_FACILITIES, certified_city_rule=TX_CERTIFIED_CITY,
        etj_rule=ETJ_REACH_LARGE_CITY, tolerance_m=TOLERANCE_M,
    )
    stretches = merge_stretches(screened, refs, STEP_M)
    stretches["mp_from"] = [float(scale.at(d, a)) for d, a in zip(stretches["direction"], stretches["from_m"])]
    stretches["mp_to"] = [float(scale.at(d, b)) for d, b in zip(stretches["direction"], stretches["to_m"])]
    candidates = place_candidates(stretches, refs, TX_FREEWAY_SPACING, id_prefix="IH35", mileposts=scale)
    candidates["nearest_sign_ft"] = nearest_sign_ft(candidates, signs)
    # Roadside markers (what drivers and operators see) drive the ID; TxDOT's exact
    # distance-from-origin is kept alongside for joining to TxDOT's own datasets.
    dfo = build_milepost_scale(refs, markers, marker_col="DFO")
    candidates["dfo_mi"] = [float(dfo.at(d, c)) for d, c in zip(candidates["direction"], candidates["chainage_m"])]

    # --- save -------------------------------------------------------------------
    out_gpkg = PROCESSED / "mclennan_ih35_screening.gpkg"
    out_gpkg.unlink(missing_ok=True)
    stretches.to_file(out_gpkg, layer="stretches", driver="GPKG")
    candidates.to_file(out_gpkg, layer="candidates", driver="GPKG")
    signs.to_file(out_gpkg, layer="existing_signs", driver="GPKG")
    write_source_yaml(out_gpkg, SourceRecord(
        source_name="Derived — OOHScout preliminary screening, IH-35 McLennan County",
        source_url="derived: OSM centerline/ramps + TxDOT permits, certified-city permits, markers, city limits",
        record_count=len(candidates), license="Mixed: ODbL (OSM-derived geometry) + public TxDOT records",
        commercial_use_allowed="true (ODbL share-alike applies to OSM-derived geometry)",
        redistribution_allowed="true (ODbL share-alike; attribution © OpenStreetMap contributors)",
        retrieval_method="backend/scripts/run_ih35_screening.py", authority="OOHScout (derived)",
        notes="Preliminary screening only — never a legal determination. Rule table not yet verified word-for-word.",
    ))
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    candidates.drop(columns="geometry").assign(
        lat=candidates.to_crs(4326).geometry.y, lon=candidates.to_crs(4326).geometry.x
    ).to_csv(OUTPUTS / "mclennan_ih35_candidates.csv", index=False)
    map_path = OUTPUTS / "mclennan_ih35_screening_map.html"
    build_map(study, stretches, candidates, signs).save(map_path)
    if NOTES_COPY.parent.exists():
        shutil.copyfile(map_path, NOTES_COPY)

    # --- summary ----------------------------------------------------------------
    print(f"existing signs on IH-35 (structures): {len(signs)}  by source: {signs['source'].value_counts().to_dict()}")
    km = stretches.assign(km=stretches["length_m"] / 1000).pivot_table(
        index="screen", columns="side", values="km", aggfunc="sum", fill_value=0).round(1)
    print("km of road by outcome (inside the county):\n", km)
    print(f"candidate spots: {len(candidates)}  by side: {candidates['side'].value_counts().to_dict()}")
    print(candidates[["candidate_id", "city", "nearest_sign_ft"]].head(12).to_string(index=False)
          if "city" in candidates else candidates[["candidate_id", "nearest_sign_ft"]].head(12).to_string(index=False))
    print("map:", map_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
