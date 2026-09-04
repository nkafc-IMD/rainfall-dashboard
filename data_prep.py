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


<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
def _optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Shrinks the in-memory (and on-disk) footprint of a processed table,
    without changing any value: repeated low-cardinality text columns
    (taluk/district -- 112 and ~24 distinct values, repeated over a million
    rows in the daily table) become pandas Categorical instead of plain
    strings, rainfall figures become float32 (rainfall to 1 decimal place
    needs nowhere near float64's precision), and small-range integer
    columns get the smallest int type that comfortably fits them.

    This matters a lot for low-RAM deployments (e.g. a 512MB hosting tier):
    reading daily.parquet with default dtypes costs ~166MB of resident
    memory even though the DataFrame itself only reports ~75MB (pandas/
    pyarrow's string handling overhead); with these dtypes applied at
    write time, a fresh read of the same data costs ~89MB instead -- and
    the DataFrame's own reported size drops from ~75MB to ~21MB. See
    DEPLOYMENT.md's "Memory footprint" section for the full breakdown.
    """
    df = df.copy()
    for col in ("taluk", "district", "growth_stage"):
        if col in df.columns:
            df[col] = df[col].astype("category")
    for col in ("rainfall", "weekly_rainfall", "monthly_rainfall", "annual_rainfall"):
        if col in df.columns:
            df[col] = df[col].astype("float32")
    if "year" in df.columns:
        df["year"] = df["year"].astype("int16")  # 1996-2025 comfortably fits
    if "month" in df.columns:
        df["month"] = df["month"].astype("int8")  # 1-12
    if "smw" in df.columns:
        df["smw"] = df["smw"].astype("int8")  # 1-52
    if "rainy_days" in df.columns:
        df["rainy_days"] = df["rainy_days"].astype("int16")  # up to 366, int8 would overflow
    return df


<<<<<<< HEAD
=======
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
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
<<<<<<< HEAD
    df = _optimize_dtypes(df)
=======
<<<<<<< HEAD
    df = _optimize_dtypes(df)
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    df.to_parquet(config.DAILY_PARQUET, index=False)
    print(f"Wrote {config.DAILY_PARQUET}  {df.shape}")
    return df


def build_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Per taluk / year / SMW total rainfall (sum of the 7 daily values)."""
    g = (
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
        daily.groupby(["taluk", "district", "year", "smw"], as_index=False, observed=True)["rainfall"]
        .sum()
        .rename(columns={"rainfall": "weekly_rainfall"})
    )
    g = _optimize_dtypes(g)
<<<<<<< HEAD
=======
=======
        daily.groupby(["taluk", "district", "year", "smw"], as_index=False)["rainfall"]
        .sum()
        .rename(columns={"rainfall": "weekly_rainfall"})
    )
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    g.to_parquet(config.WEEKLY_PARQUET, index=False)
    print(f"Wrote {config.WEEKLY_PARQUET}  {g.shape}")
    return g


def build_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Per taluk / year / month total rainfall."""
    g = (
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
        daily.groupby(["taluk", "district", "year", "month"], as_index=False, observed=True)["rainfall"]
        .sum()
        .rename(columns={"rainfall": "monthly_rainfall"})
    )
    g = _optimize_dtypes(g)
<<<<<<< HEAD
=======
=======
        daily.groupby(["taluk", "district", "year", "month"], as_index=False)["rainfall"]
        .sum()
        .rename(columns={"rainfall": "monthly_rainfall"})
    )
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    g.to_parquet(config.MONTHLY_PARQUET, index=False)
    print(f"Wrote {config.MONTHLY_PARQUET}  {g.shape}")
    return g


def build_annual(daily: pd.DataFrame) -> pd.DataFrame:
    """Per taluk / year total (annual) rainfall, plus rainy-day count."""
    totals = (
<<<<<<< HEAD
        daily.groupby(["taluk", "district", "year"], as_index=False, observed=True)["rainfall"]
=======
<<<<<<< HEAD
        daily.groupby(["taluk", "district", "year"], as_index=False, observed=True)["rainfall"]
=======
        daily.groupby(["taluk", "district", "year"], as_index=False)["rainfall"]
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
        .sum()
        .rename(columns={"rainfall": "annual_rainfall"})
    )
    rainy = (
        daily.assign(is_rainy=(daily["rainfall"] >= 2.5))
<<<<<<< HEAD
        .groupby(["taluk", "district", "year"], as_index=False, observed=True)["is_rainy"]
=======
<<<<<<< HEAD
        .groupby(["taluk", "district", "year"], as_index=False, observed=True)["is_rainy"]
=======
        .groupby(["taluk", "district", "year"], as_index=False)["is_rainy"]
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
        .sum()
        .rename(columns={"is_rainy": "rainy_days"})
    )
    g = totals.merge(rainy, on=["taluk", "district", "year"], how="left")
<<<<<<< HEAD
    g = _optimize_dtypes(g)
=======
<<<<<<< HEAD
    g = _optimize_dtypes(g)
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    g.to_parquet(config.ANNUAL_PARQUET, index=False)
    print(f"Wrote {config.ANNUAL_PARQUET}  {g.shape}")
    return g


def main():
    os.makedirs(config.PROCESSED_DIR, exist_ok=True)

    lookup = build_taluk_lookup()
<<<<<<< HEAD
    lookup = _optimize_dtypes(lookup)
=======
<<<<<<< HEAD
    lookup = _optimize_dtypes(lookup)
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
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
