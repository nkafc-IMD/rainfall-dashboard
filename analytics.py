"""
analytics.py
------------
Phase 3 (Rainfall Analytics) and Phase 4 (Statistical Analysis) helpers.
Builds on the same processed tables loaded once in data_loader.py, and
follows the same averaging rule used everywhere else in the app: figures
are computed per-year first, then averaged across the selected years.
"""
import numpy as np
import pandas as pd

import config
import data_loader as dl

SEASONS = {
    "Winter (Jan-Feb)": [1, 2],
    "Pre-Monsoon (Mar-May)": [3, 4, 5],
    "Monsoon (Jun-Sep)": [6, 7, 8, 9],
    "Post-Monsoon (Oct-Dec)": [10, 11, 12],
}

DRY_DAY_THRESHOLD_MM = 2.5  # IMD convention: a "dry day" is < 2.5 mm


# ---------------------------------------------------------------------------
# Phase 3.1 / 3.2 -- Rainfall Ranking / Wettest / Driest Taluks
# ---------------------------------------------------------------------------
def taluk_ranking(start_date, end_date) -> pd.DataFrame:
    """All 112 taluks, ranked by average annual rainfall for the selected period."""
    years = dl.years_in_range(start_date, end_date)
    sub = dl._annual[dl._annual["year"].isin(years)]
    out = (
<<<<<<< HEAD
        sub.groupby(["taluk", "district"], as_index=False, observed=True)["annual_rainfall"]
=======
<<<<<<< HEAD
        sub.groupby(["taluk", "district"], as_index=False, observed=True)["annual_rainfall"]
=======
        sub.groupby(["taluk", "district"], as_index=False)["annual_rainfall"]
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
        .mean()
        .rename(columns={"annual_rainfall": "avg_annual_rainfall"})
        .sort_values("avg_annual_rainfall", ascending=False)
        .reset_index(drop=True)
    )
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    # Small per-query result (112 rows) -- upcast from the source table's
    # memory-saving float32 to float64 *before* rounding. Rounding a float32
    # Series stays float32 and still shows binary-imprecision artifacts (e.g.
    # 1953.5999755859375 instead of 1953.6); upcasting first fixes it, since
    # float64 can represent the rounded decimal cleanly. Order matters here.
    out["avg_annual_rainfall"] = out["avg_annual_rainfall"].astype("float64").round(1)
<<<<<<< HEAD
=======
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    out["rank"] = out.index + 1
    return out


def wettest_taluks(start_date, end_date, n: int = 10) -> pd.DataFrame:
    return taluk_ranking(start_date, end_date).head(n)


def driest_taluks(start_date, end_date, n: int = 10) -> pd.DataFrame:
    return taluk_ranking(start_date, end_date).tail(n).sort_values("avg_annual_rainfall")


# ---------------------------------------------------------------------------
# Phase 3.3 / 3.7 -- Rainfall Trend + Moving Average
# ---------------------------------------------------------------------------
def rainfall_trend(taluk: str, start_date, end_date) -> pd.DataFrame:
    """Yearly totals plus a fitted linear trend line."""
    s = dl.annual_series(taluk, start_date, end_date).reset_index(drop=True)
    if len(s) >= 2:
        coeffs = np.polyfit(s["year"], s["annual_rainfall"], 1)
        s["trend"] = np.polyval(coeffs, s["year"])
        s.attrs["slope_mm_per_year"] = float(coeffs[0])
    else:
        s["trend"] = s["annual_rainfall"]
        s.attrs["slope_mm_per_year"] = 0.0
    return s


def moving_average(taluk: str, start_date, end_date, window: int = 5) -> pd.DataFrame:
    s = dl.annual_series(taluk, start_date, end_date).reset_index(drop=True)
    s["moving_avg"] = s["annual_rainfall"].rolling(window, min_periods=1, center=True).mean()
    return s


# ---------------------------------------------------------------------------
# Phase 3.4 -- Cumulative Rainfall (climatological cumulative curve)
# ---------------------------------------------------------------------------
def cumulative_climatology(taluk: str, start_date, end_date) -> pd.DataFrame:
    """Average daily rainfall by day-of-year (mean across selected years),
    cumulatively summed -- shows how the season's rain typically builds up."""
    years = dl.years_in_range(start_date, end_date)
    sub = dl._daily[(dl._daily["taluk"] == taluk) & (dl._daily["year"].isin(years))].copy()
    sub["doy"] = pd.to_datetime(sub["date"]).dt.dayofyear
    clim = (
        sub.groupby("doy", as_index=False)["rainfall"]
        .mean()
        .set_index("doy")
        .reindex(range(1, 367))
        .fillna(0)
        .reset_index()
    )
    clim["cumulative_rain"] = clim["rainfall"].cumsum()
    return clim


# ---------------------------------------------------------------------------
# Phase 3.6 -- Rainfall Anomaly (departure from the selected period's own mean)
# ---------------------------------------------------------------------------
def rainfall_anomaly(taluk: str, start_date, end_date) -> pd.DataFrame:
    s = dl.annual_series(taluk, start_date, end_date).reset_index(drop=True)
    lta = s["annual_rainfall"].mean() if not s.empty else 0.0
    s["long_term_avg"] = lta
    s["anomaly_mm"] = s["annual_rainfall"] - lta
    s["anomaly_pct"] = np.where(lta > 0, s["anomaly_mm"] / lta * 100, 0.0)
    return s


# ---------------------------------------------------------------------------
# Phase 3.8 -- Standardized Rainfall (z-score, simple SPI-style index)
# ---------------------------------------------------------------------------
def standardized_rainfall(taluk: str, start_date, end_date) -> pd.DataFrame:
    s = dl.annual_series(taluk, start_date, end_date).reset_index(drop=True)
    mean = s["annual_rainfall"].mean() if not s.empty else 0.0
    std = s["annual_rainfall"].std() if len(s) > 1 else np.nan
    s["z_score"] = (s["annual_rainfall"] - mean) / std if std and std > 0 else 0.0
    return s


# ---------------------------------------------------------------------------
# Phase 3.9 -- Seasonal Rainfall (mean of yearly seasonal totals)
# ---------------------------------------------------------------------------
def seasonal_rainfall(taluk: str, start_date, end_date) -> pd.DataFrame:
    years = dl.years_in_range(start_date, end_date)
    sub = dl._monthly[(dl._monthly["taluk"] == taluk) & (dl._monthly["year"].isin(years))]
    rows = []
    for season, months in SEASONS.items():
        yearly_totals = sub[sub["month"].isin(months)].groupby("year")["monthly_rainfall"].sum()
        rows.append({"season": season, "avg_rain": yearly_totals.mean() if not yearly_totals.empty else 0.0})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Phase 4 -- Statistical Analysis summary card
# ---------------------------------------------------------------------------
def _longest_dry_spell(daily_rain: pd.Series) -> int:
    """Longest run of consecutive dry days (< DRY_DAY_THRESHOLD_MM) in the series."""
    is_dry = (daily_rain.to_numpy() < DRY_DAY_THRESHOLD_MM).astype(int)
    if is_dry.size == 0:
        return 0
    # run-length encode
    change = np.diff(is_dry, prepend=0)
    run_starts = np.where(change == 1)[0]
    run_ends = np.where(np.diff(is_dry, append=0) == -1)[0]
    if len(run_starts) == 0:
        return int(is_dry.sum()) if is_dry.all() else 0
    lengths = run_ends - run_starts + 1
    return int(lengths.max()) if len(lengths) else 0


def summary_statistics(taluk: str, start_date, end_date) -> dict:
    """Descriptive statistics on RAINY days only (rainfall > 0 mm) within the
    selected period -- mean/median/percentiles of zero-inflated daily rainfall
    are not meaningful if computed over all days including the long dry season."""
    daily = dl.daily_series(taluk, start_date, end_date)
    years = dl.years_in_range(start_date, end_date)

    rainy = daily.loc[daily["rainfall"] > 0, "rainfall"]

    annual = dl._annual[(dl._annual["taluk"] == taluk) & (dl._annual["year"].isin(years))]

    # Longest dry spell: per-year max, then averaged across years (consistent
    # with the app's "mean of yearly totals" rule), plus the single longest
    # stretch across the whole selected period.
    daily_sorted = daily.sort_values("date")
    yearly_max_dry = []
    for y in years:
        yr_series = daily_sorted.loc[pd.to_datetime(daily_sorted["date"]).dt.year == y, "rainfall"]
        if not yr_series.empty:
            yearly_max_dry.append(_longest_dry_spell(yr_series))
    avg_annual_max_dry_spell = float(np.mean(yearly_max_dry)) if yearly_max_dry else 0.0
    overall_max_dry_spell = _longest_dry_spell(daily_sorted["rainfall"]) if not daily_sorted.empty else 0

    stats = {
        "mean_rainy_day_mm": float(rainy.mean()) if not rainy.empty else 0.0,
        "median_rainy_day_mm": float(rainy.median()) if not rainy.empty else 0.0,
        "max_daily_mm": float(daily["rainfall"].max()) if not daily.empty else 0.0,
        "min_nonzero_daily_mm": float(rainy.min()) if not rainy.empty else 0.0,
        "std_rainy_day_mm": float(rainy.std()) if len(rainy) > 1 else 0.0,
        "cv_pct": float(rainy.std() / rainy.mean() * 100) if not rainy.empty and rainy.mean() > 0 else 0.0,
        "p25_mm": float(rainy.quantile(0.25)) if not rainy.empty else 0.0,
        "p50_mm": float(rainy.quantile(0.50)) if not rainy.empty else 0.0,
        "p75_mm": float(rainy.quantile(0.75)) if not rainy.empty else 0.0,
        "p90_mm": float(rainy.quantile(0.90)) if not rainy.empty else 0.0,
        "total_rainy_days": int((daily["rainfall"] > 0).sum()),
        "avg_annual_rainy_days": float(annual["rainy_days"].mean()) if not annual.empty else 0.0,
        "avg_annual_max_dry_spell_days": avg_annual_max_dry_spell,
        "overall_max_dry_spell_days": overall_max_dry_spell,
    }
    return stats
