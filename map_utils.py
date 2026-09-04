"""
map_utils.py
Builds the per-request GeoJSON (district taluks, selected taluk highlighted)
and the associated map bounds, mirroring the look of the original Shiny
Leaflet map (orange highlight on the selected taluk, thin district outline).
"""
import copy
import config
import data_loader as dl

SELECTED_FILL = config.COLORS["accent"]      # orange
OTHER_FILL = "#ffe8c7"                        # pale orange (rest of district)
BORDER_COLOR = "#8a5a1e"


OTHER_DISTRICT_FILL = "#e2e2e2"  # muted grey for taluks outside the selected district


def full_map_geojson(selected_district: str, selected_taluk: str):
    """All 112 taluks, always -- so the sidebar map can be tapped directly to
    pick a taluk (handy on mobile, where typing in a dropdown is slower).
    The selected district's taluks are shown pale orange, the selected taluk
    in full orange, and every other district's taluks in a muted grey (still
    clickable, just visually secondary). Returned bounds are fit to the
    selected district only, to keep the existing zoom-in behaviour."""
    out_feats = []
    dist_lats, dist_lons = [], []
    for f in dl.TALUKS_GEOJSON["features"]:
        f = copy.deepcopy(f)
        taluk = f["properties"].get("taluk")
        district = f["properties"].get("district")
        is_sel = taluk == selected_taluk
        in_district = district == selected_district
        if is_sel:
            f["properties"]["color"] = SELECTED_FILL
            f["properties"]["fillOpacity"] = 0.85
            f["properties"]["borderColor"] = BORDER_COLOR
            f["properties"]["borderWeight"] = 2.5
        elif in_district:
            f["properties"]["color"] = OTHER_FILL
            f["properties"]["fillOpacity"] = 0.45
            f["properties"]["borderColor"] = BORDER_COLOR
            f["properties"]["borderWeight"] = 1
        else:
            f["properties"]["color"] = OTHER_DISTRICT_FILL
            f["properties"]["fillOpacity"] = 0.25
            f["properties"]["borderColor"] = "#aaaaaa"
            f["properties"]["borderWeight"] = 0.5
        out_feats.append(f)
        if in_district:
            _collect_coords(f["geometry"]["coordinates"], dist_lats, dist_lons)

    fc = {"type": "FeatureCollection", "features": out_feats}
    bounds = [[min(dist_lats), min(dist_lons)], [max(dist_lats), max(dist_lons)]] if dist_lats else None
    return fc, bounds


def district_geojson(district: str, selected_taluk: str):
    """Return (geojson_feature_collection, bounds) for one district."""
    all_feats = dl.TALUKS_GEOJSON["features"]
    out_feats = []
    lats, lons = [], []
    for f in all_feats:
        if f["properties"].get("district") != district:
            continue
        f = copy.deepcopy(f)
        is_sel = f["properties"].get("taluk") == selected_taluk
        f["properties"]["color"] = SELECTED_FILL if is_sel else OTHER_FILL
        f["properties"]["fillOpacity"] = 0.85 if is_sel else 0.45
        out_feats.append(f)

        geom = f["geometry"]
        coords = geom["coordinates"]
        _collect_coords(coords, lats, lons)

    fc = {"type": "FeatureCollection", "features": out_feats}
    if lats and lons:
        bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
    else:
        bounds = None
    return fc, bounds


def region_geojson(color_map: dict, opacity: float = 0.75, default_color: str = "#e0e0e0"):
    """Build a FeatureCollection covering ALL taluks, colored per `color_map`
    (taluk -> hex color). Used by the Phase 6 spatial-analysis maps (region-
    wide ranking / zones / hotspots), as opposed to district_geojson() above
    which is scoped to one district for the main sidebar map."""
    out_feats = []
    lats, lons = [], []
    for f in dl.TALUKS_GEOJSON["features"]:
        f = copy.deepcopy(f)
        taluk = f["properties"].get("taluk")
        f["properties"]["color"] = color_map.get(taluk, default_color)
        f["properties"]["fillOpacity"] = opacity
        out_feats.append(f)
        _collect_coords(f["geometry"]["coordinates"], lats, lons)

    fc = {"type": "FeatureCollection", "features": out_feats}
    bounds = [[min(lats), min(lons)], [max(lats), max(lons)]] if lats else None
    return fc, bounds


def _collect_coords(coords, lats, lons):
    """Recursively walk nested coordinate lists (Polygon / MultiPolygon)."""
    if isinstance(coords[0], (float, int)):
        lons.append(coords[0])
        lats.append(coords[1])
    else:
        for c in coords:
            _collect_coords(c, lats, lons)
