"""
spatial.py
----------
Phase 6 (Spatial Analysis) helpers: taluk ranking map, district ranking,
rainfall zone classification, IDW spatial interpolation, Getis-Ord* hotspot
analysis, and per-year values for the choropleth animation / time slider.

No new heavy geo-dependency is introduced beyond what's already used in
data_prep.py (shapely, via geopandas) -- adjacency and centroids are derived
straight from the same taluk polygons already loaded into memory.
"""
import numpy as np
import pandas as pd
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

import config
import data_loader as dl

RAINFALL_ZONES = [
    (0, 600, "Low (<600 mm)", "#ffe8b3"),
    (600, 900, "Moderate (600-900 mm)", "#a8d98a"),
    (900, 1200, "High (900-1200 mm)", "#4a9d5f"),
    (1200, float("inf"), "Very High (>1200 mm)", "#1f6b34"),
]


# ---------------------------------------------------------------------------
# Geometry helpers (built once from the same GeoJSON used for the map)
# ---------------------------------------------------------------------------
def _geoms():
    feats = dl.TALUKS_GEOJSON["features"]
    taluks = [f["properties"]["taluk"] for f in feats]
    geoms = [shape(f["geometry"]) for f in feats]
    return taluks, geoms


_TALUKS, _GEOMS = _geoms()
_CENTROIDS = pd.DataFrame(
    {
        "taluk": _TALUKS,
        "lon": [g.centroid.x for g in _GEOMS],
        "lat": [g.centroid.y for g in _GEOMS],
    }
).merge(dl._lookup, on="taluk", how="left")


def taluk_centroids() -> pd.DataFrame:
    return _CENTROIDS.copy()


_POINT_TREE = STRtree(_GEOMS)


def taluk_at_latlon(lat: float, lon: float):
    """Point-in-polygon lookup used when the user taps/clicks a taluk on the
    map. Leaflet's click event only reports lat/lon, not which GeoJSON
    feature was hit, so we resolve it server-side against the same taluk
    polygons used to draw the map."""
    pt = Point(lon, lat)
    for i in _POINT_TREE.query(pt):
        i = int(i)
        if _GEOMS[i].contains(pt):
            return _TALUKS[i]
    # fall back to nearest centroid if the tap landed just outside a border
    idx = int(_POINT_TREE.nearest(pt))
    return _TALUKS[idx]


def _build_adjacency():
    """Queen contiguity: two taluks are neighbours if their polygons touch."""
    tree = STRtree(_GEOMS)
    idx_by_id = {id(g): i for i, g in enumerate(_GEOMS)}
    neighbours = {t: [] for t in _TALUKS}
    for i, geom in enumerate(_GEOMS):
        candidate_idxs = tree.query(geom)
        for j in candidate_idxs:
            j = int(j)
            if j == i:
                continue
            if _GEOMS[i].touches(_GEOMS[j]) or _GEOMS[i].intersects(_GEOMS[j]):
                neighbours[_TALUKS[i]].append(_TALUKS[j])
    return neighbours


_ADJACENCY = _build_adjacency()


# ---------------------------------------------------------------------------
# 6.1 Taluk Ranking Map -- reuses data_loader.map_values (avg annual rainfall
# per taluk for the selected period, mean-of-yearly-totals rule)
# ---------------------------------------------------------------------------
def taluk_ranking_map_values(start_date, end_date) -> pd.DataFrame:
    return dl.map_values(start_date, end_date)


# ---------------------------------------------------------------------------
# 6.2 District Ranking -- average of the (per-taluk average annual rainfall)
# within each district
# ---------------------------------------------------------------------------
def district_ranking(start_date, end_date) -> pd.DataFrame:
    tv = dl.map_values(start_date, end_date)
    out = (
        tv.groupby("district", as_index=False)["annual_rainfall"]
        .mean()
        .rename(columns={"annual_rainfall": "avg_annual_rainfall"})
        .sort_values("avg_annual_rainfall", ascending=False)
        .reset_index(drop=True)
    )
    out["rank"] = out.index + 1
    return out


# ---------------------------------------------------------------------------
# 6.3 Rainfall Zones -- classify each taluk's average annual rainfall
# ---------------------------------------------------------------------------
def rainfall_zone_labels(value: float):
    for lo, hi, label, color in RAINFALL_ZONES:
        if lo <= value < hi:
            return label, color
    return RAINFALL_ZONES[-1][2], RAINFALL_ZONES[-1][3]


def rainfall_zones(start_date, end_date) -> pd.DataFrame:
    tv = dl.map_values(start_date, end_date)
    labels, colors = zip(*tv["annual_rainfall"].apply(rainfall_zone_labels))
    tv = tv.copy()
    tv["zone"] = labels
    tv["zone_color"] = colors
    return tv


# ---------------------------------------------------------------------------
# 6.4 Spatial Interpolation -- simple Inverse Distance Weighting (IDW) over
# a regular lat/lon grid, using taluk centroids as sample points
# ---------------------------------------------------------------------------
def idw_grid(start_date, end_date, grid_res: int = 60, power: float = 2.0):
    tv = dl.map_values(start_date, end_date).merge(_CENTROIDS[["taluk", "lat", "lon"]], on="taluk")
    lats = tv["lat"].to_numpy()
    lons = tv["lon"].to_numpy()
    vals = tv["annual_rainfall"].to_numpy()

    lat_grid = np.linspace(lats.min() - 0.2, lats.max() + 0.2, grid_res)
    lon_grid = np.linspace(lons.min() - 0.2, lons.max() + 0.2, grid_res)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)

    # distance from every grid cell to every sample point
    d2 = (lon_mesh[..., None] - lons) ** 2 + (lat_mesh[..., None] - lats) ** 2
    d2 = np.maximum(d2, 1e-12)
    w = 1.0 / (d2 ** (power / 2))
    z = (w * vals).sum(axis=-1) / w.sum(axis=-1)

    return lon_grid, lat_grid, z, tv


# ---------------------------------------------------------------------------
# 6.5 Hotspot Analysis -- simplified Getis-Ord Gi* using queen-contiguity
# neighbours (a taluk's own value is included, matching Gi*)
# ---------------------------------------------------------------------------
def hotspot_analysis(start_date, end_date) -> pd.DataFrame:
    tv = dl.map_values(start_date, end_date).set_index("taluk")
    values = tv["annual_rainfall"]
    n = len(values)
    global_mean = values.mean()
    global_std = values.std()

    rows = []
    for taluk in values.index:
        neighbours = _ADJACENCY.get(taluk, [])
        group = [taluk] + neighbours
        group_vals = values.reindex(group).dropna()
        w = len(group_vals)
        if w == 0 or global_std == 0:
            z = 0.0
        else:
            numerator = group_vals.sum() - global_mean * w
            denom = global_std * np.sqrt((n * w - w * w) / (n - 1)) if n > 1 else 1
            z = numerator / denom if denom else 0.0

        if z >= 1.96:
            category = "Hot Spot (95%)"
        elif z >= 1.65:
            category = "Hot Spot (90%)"
        elif z <= -1.96:
            category = "Cold Spot (95%)"
        elif z <= -1.65:
            category = "Cold Spot (90%)"
        else:
            category = "Not Significant"

        rows.append({
            "taluk": taluk, "district": tv.loc[taluk, "district"],
            "annual_rainfall": values[taluk], "z_score": z, "category": category,
        })
    return pd.DataFrame(rows)


HOTSPOT_COLORS = {
    "Hot Spot (95%)": "#b2182b",
    "Hot Spot (90%)": "#ef8a62",
    "Not Significant": "#e0e0e0",
    "Cold Spot (90%)": "#67a9cf",
    "Cold Spot (95%)": "#2166ac",
}


# ---------------------------------------------------------------------------
# 6.6 / 6.7 Choropleth Animation + Time Slider -- per-year taluk totals
# ---------------------------------------------------------------------------
def yearly_taluk_values(start_date, end_date) -> pd.DataFrame:
    """One row per taluk per year (annual totals, NOT averaged) -- what the
    time slider / animation steps through."""
    years = dl.years_in_range(start_date, end_date)
    sub = dl._annual[dl._annual["year"].isin(years)]
    return sub[["taluk", "district", "year", "annual_rainfall"]]
