"""
data_prep.py
------------
ONE-TIME preprocessing pipeline (run manually, or on a schedule -- see
Phase 13 "Scheduled Data Update" in the README).

IMD Rainfall Data (Parquet)
        |
        v
Data Preprocessing (this script)
        |
   -------------------------------------------------
   |                    |                    |
Spatial Join      Weekly Statistics    Monthly Statistics
(112 Taluks)      (SMW 1-52)           (Jan-Dec)
   |                    |                    |
   -------------------------------------------------
        |
        v
Rainfall Database (Parquet)
        |
        v
   Dash Application

Run:  python data_prep.py
Produces (in data/processed/):
    daily.parquet        -- daily rainfall, 1996-2025, with SMW/month/year columns
    weekly_smw.parquet   -- taluk x year x SMW total rainfall (+ district)
    monthly.parquet      -- taluk x year x month total rainfall (+ district)
    annual.parquet       -- taluk x year total rainfall (+ district)
    taluk_lookup.parquet -- taluk -> district lookup (112 taluks)
    taluks_4326.geojson  -- taluk polygons reprojected to WGS84 for Leaflet
"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd

import config


def smw_from_doy(doy: np.ndarray) -> np.ndarray:
    """Standard Meteorological Week (1-52). Days 365/366 fold into week 52."""
    smw = np.ceil(doy / 7).astype(int)
    smw = np.clip(smw, 1, 52)
    return smw


def build_taluk_lookup() -> pd.DataFrame:
    gdf = gpd.read_file(config.RAW_SHAPEFILE)
    lookup = gdf[["KGISTalukN", "DISTRICT"]].rename(
        columns={"KGISTalukN": "taluk", "DISTRICT": "district"}
    ).drop_duplicates().reset_index(drop=True)
    return lookup


def build_geojson():
    gdf = gpd.read_file(config.RAW_SHAPEFILE)
    gdf = gdf[["KGISTalukN", "DISTRICT", "geometry"]].rename(
        columns={"KGISTalukN": "taluk", "DISTRICT": "district"}
    )
    gdf = gdf.to_crs(epsg=4326)
    # simplify slightly for faster map rendering (tolerance in degrees)
    gdf["geometry"] = gdf["geometry"].simplify(0.0005, preserve_topology=True)
    gdf.to_file(config.TALUKS_GEOJSON, driver="GeoJSON")
    print(f"Wrote {config.TALUKS_GEOJSON}  ({len(gdf)} taluks)")


def build_daily() -> pd.DataFrame:
    df = pd.read_parquet(config.RAW_PARQUET)
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= config.MIN_DATE) & (df["date"] <= config.MAX_DATE)].copy()

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["doy"] = df["date"].dt.dayofyear
    df["smw"] = smw_from_doy(df["doy"].to_numpy())

    lookup = build_taluk_lookup()
    df = df.merge(lookup, on="taluk", how="left")

    df["rainfall"] = df["rainfall"].astype(float).clip(lower=0)
    df = df[["date", "taluk", "district", "year", "month", "smw", "rainfall"]]
    df.to_parquet(config.DAILY_PARQUET, index=False)
    print(f"Wrote {config.DAILY_PARQUET}  {df.shape}")
    return df


def build_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Per taluk / year / SMW total rainfall (sum of the 7 daily values)."""
    g = (
        daily.groupby(["taluk", "district", "year", "smw"], as_index=False)["rainfall"]
        .sum()
        .rename(columns={"rainfall": "weekly_rainfall"})
    )
    g.to_parquet(config.WEEKLY_PARQUET, index=False)
    print(f"Wrote {config.WEEKLY_PARQUET}  {g.shape}")
    return g


def build_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Per taluk / year / month total rainfall."""
    g = (
        daily.groupby(["taluk", "district", "year", "month"], as_index=False)["rainfall"]
        .sum()
        .rename(columns={"rainfall": "monthly_rainfall"})
    )
    g.to_parquet(config.MONTHLY_PARQUET, index=False)
    print(f"Wrote {config.MONTHLY_PARQUET}  {g.shape}")
    return g


def build_annual(daily: pd.DataFrame) -> pd.DataFrame:
    """Per taluk / year total (annual) rainfall, plus rainy-day count."""
    totals = (
        daily.groupby(["taluk", "district", "year"], as_index=False)["rainfall"]
        .sum()
        .rename(columns={"rainfall": "annual_rainfall"})
    )
    rainy = (
        daily.assign(is_rainy=(daily["rainfall"] >= 2.5))
        .groupby(["taluk", "district", "year"], as_index=False)["is_rainy"]
        .sum()
        .rename(columns={"is_rainy": "rainy_days"})
    )
    g = totals.merge(rainy, on=["taluk", "district", "year"], how="left")
    g.to_parquet(config.ANNUAL_PARQUET, index=False)
    print(f"Wrote {config.ANNUAL_PARQUET}  {g.shape}")
    return g


def main():
    os.makedirs(config.PROCESSED_DIR, exist_ok=True)

    lookup = build_taluk_lookup()
    lookup.to_parquet(config.TALUK_LOOKUP, index=False)
    print(f"Wrote {config.TALUK_LOOKUP}  {lookup.shape}")

    build_geojson()

    daily = build_daily()
    build_weekly(daily)
    build_monthly(daily)
    build_annual(daily)

    print("\nPreprocessing complete.")


if __name__ == "__main__":
    main()
