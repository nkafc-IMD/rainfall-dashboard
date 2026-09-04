"""
data_loader.py
--------------
Loads the pre-processed parquet tables once at process start-up (Waitress /
gunicorn workers each hold their own copy in memory -- ~112 taluks x 30 years
is small, well under 50 MB total) and exposes fast aggregation helpers.

AVERAGING RULE (as specified by the user)
------------------------------------------
When a user selects a date range spanning multiple years, e.g. 1996-2000:
  1. Compute the total for the period-of-interest (SMW / month / year)
     *separately for each year* in the range.
  2. Average those per-year totals across the selected years.
This is a "mean of yearly totals", NOT a pooled mean of raw daily values, so a
short month in a leap year etc. does not distort the comparison. It is what
was validated against the original R/Shiny dashboard (Hubballi taluk, full
1996-2025 range -> 687.1 mm/year, matches the pre-processed data exactly).
"""
import json
import functools
import pandas as pd

import config


# ---------------------------------------------------------------------------
# Load once, keep in memory
# ---------------------------------------------------------------------------
_daily = pd.read_parquet(config.DAILY_PARQUET)
_weekly = pd.read_parquet(config.WEEKLY_PARQUET)
_monthly = pd.read_parquet(config.MONTHLY_PARQUET)
_annual = pd.read_parquet(config.ANNUAL_PARQUET)
_lookup = pd.read_parquet(config.TALUK_LOOKUP).sort_values("taluk")

with open(config.TALUKS_GEOJSON) as f:
    TALUKS_GEOJSON = json.load(f)

DISTRICTS = sorted(_lookup["district"].unique().tolist())
TALUKS_BY_DISTRICT = (
    _lookup.groupby("district")["taluk"].apply(lambda s: sorted(s.tolist())).to_dict()
)
ALL_TALUKS = sorted(_lookup["taluk"].unique().tolist())


def taluk_district(taluk: str) -> str:
    row = _lookup.loc[_lookup["taluk"] == taluk]
    return row["district"].iloc[0] if not row.empty else None


def years_in_range(start_date, end_date):
    """Full calendar years touched by the selected date range (inclusive)."""
    y0 = pd.Timestamp(start_date).year
    y1 = pd.Timestamp(end_date).year
    y0 = max(y0, config.MIN_YEAR)
    y1 = min(y1, config.MAX_YEAR)
    return list(range(y0, y1 + 1))


# ---------------------------------------------------------------------------
# Weekly (SMW) -- mean of yearly totals per SMW
# ---------------------------------------------------------------------------
def weekly_climatology(taluk: str, start_date, end_date) -> pd.DataFrame:
    years = years_in_range(start_date, end_date)
    sub = _weekly[(_weekly["taluk"] == taluk) & (_weekly["year"].isin(years))]
    out = (
<<<<<<< HEAD
        sub.groupby("smw", as_index=False, observed=True)["weekly_rainfall"]
=======
        sub.groupby("smw", as_index=False)["weekly_rainfall"]
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
        .agg(avg_rain="mean", min_rain="min", max_rain="max")
        .sort_values("smw")
    )
    # ensure all 52 weeks present even if some are missing from the slice
    out = out.set_index("smw").reindex(range(1, 53)).fillna(0).reset_index()
<<<<<<< HEAD
    # Small per-query result (52 rows) -- upcast from the source table's
    # memory-saving float32 to plain float64 so rounded values display
    # cleanly (e.g. "39.9") instead of leaking float32 binary imprecision
    # (e.g. "39.90000152587890625") into any table/JSON built from this.
    for col in ("avg_rain", "min_rain", "max_rain"):
        out[col] = out[col].astype("float64").round(1)
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
    return out


def weekly_by_year_pivot(taluk: str, start_date, end_date) -> pd.DataFrame:
    """Wide breakdown for the Excel export: one row per SMW (1-52), one
    column per selected year showing that year's weekly total, plus a final
    'Average (Y0-Y1)' column -- the same mean-of-yearly-totals figure used
    everywhere else in the app, just with the individual years shown
    alongside it instead of only the final average."""
    years = years_in_range(start_date, end_date)
    sub = _weekly[(_weekly["taluk"] == taluk) & (_weekly["year"].isin(years))]
    pivot = sub.pivot_table(index="smw", columns="year", values="weekly_rainfall", aggfunc="sum")
    pivot = pivot.reindex(index=range(1, 53), columns=years)
    avg_label = f"Average ({years[0]}-{years[-1]})" if len(years) > 1 else f"Average ({years[0]})"
    pivot[avg_label] = pivot[years].mean(axis=1)
    pivot = pivot.fillna(0).reset_index().rename(columns={"smw": "SMW"})
    pivot.columns = [str(c) for c in pivot.columns]
<<<<<<< HEAD
    for col in pivot.columns:
        if col != "SMW":
            pivot[col] = pivot[col].astype("float64").round(1)
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
    return pivot


# ---------------------------------------------------------------------------
# Monthly -- mean of yearly totals per calendar month
# ---------------------------------------------------------------------------
def monthly_climatology(taluk: str, start_date, end_date) -> pd.DataFrame:
    years = years_in_range(start_date, end_date)
    sub = _monthly[(_monthly["taluk"] == taluk) & (_monthly["year"].isin(years))]
    out = (
<<<<<<< HEAD
        sub.groupby("month", as_index=False, observed=True)["monthly_rainfall"]
=======
        sub.groupby("month", as_index=False)["monthly_rainfall"]
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
        .mean()
        .rename(columns={"monthly_rainfall": "avg_rain"})
        .sort_values("month")
    )
    out = out.set_index("month").reindex(range(1, 13)).fillna(0).reset_index()
<<<<<<< HEAD
    out["avg_rain"] = out["avg_rain"].astype("float64").round(1)
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
    return out


def monthly_by_year_pivot(taluk: str, start_date, end_date) -> pd.DataFrame:
    """Wide breakdown for the Excel export: one row per calendar month
    (Jan-Dec), one column per selected year showing that year's monthly
    total, plus a final 'Average (Y0-Y1)' column."""
    years = years_in_range(start_date, end_date)
    sub = _monthly[(_monthly["taluk"] == taluk) & (_monthly["year"].isin(years))]
    pivot = sub.pivot_table(index="month", columns="year", values="monthly_rainfall", aggfunc="sum")
    pivot = pivot.reindex(index=range(1, 13), columns=years)
    avg_label = f"Average ({years[0]}-{years[-1]})" if len(years) > 1 else f"Average ({years[0]})"
    pivot[avg_label] = pivot[years].mean(axis=1)
    pivot = pivot.fillna(0).reset_index().rename(columns={"month": "Month"})
    pivot.columns = [str(c) for c in pivot.columns]
<<<<<<< HEAD
    for col in pivot.columns:
        if col != "Month":
            pivot[col] = pivot[col].astype("float64").round(1)
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
    return pivot


# ---------------------------------------------------------------------------
# Annual -- mean of yearly totals (a single number: "Annual Average Rainfall")
# ---------------------------------------------------------------------------
def annual_average(taluk: str, start_date, end_date) -> float:
    years = years_in_range(start_date, end_date)
    sub = _annual[(_annual["taluk"] == taluk) & (_annual["year"].isin(years))]
    if sub.empty:
        return 0.0
<<<<<<< HEAD
    return round(float(sub["annual_rainfall"].astype("float64").mean()), 1)
=======
    return float(sub["annual_rainfall"].mean())
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af


def annual_series(taluk: str, start_date, end_date) -> pd.DataFrame:
    """Yearly totals (for trend charts), not averaged -- one row per year."""
    years = years_in_range(start_date, end_date)
    sub = _annual[(_annual["taluk"] == taluk) & (_annual["year"].isin(years))]
<<<<<<< HEAD
    out = sub.sort_values("year")[["year", "annual_rainfall", "rainy_days"]].copy()
    out["annual_rainfall"] = out["annual_rainfall"].astype("float64").round(1)
    return out
=======
    return sub.sort_values("year")[["year", "annual_rainfall", "rainy_days"]]
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af


def annual_breakdown_with_average(taluk: str, start_date, end_date) -> pd.DataFrame:
    """Same as annual_series, with one extra summary row appended at the
    bottom: 'Average (Y0-Y1)' -- the mean of the yearly totals shown above
    it, matching the Annual Average Rainfall KPI shown elsewhere in the app."""
    s = annual_series(taluk, start_date, end_date)
    years = years_in_range(start_date, end_date)
    label = f"Average ({years[0]}-{years[-1]})" if len(years) > 1 else f"Average ({years[0]})"
    avg_row = pd.DataFrame([{
        "year": label,
        "annual_rainfall": s["annual_rainfall"].mean() if not s.empty else 0.0,
        "rainy_days": s["rainy_days"].mean() if not s.empty else 0.0,
    }])
    out = pd.concat([s, avg_row], ignore_index=True)
    out = out.rename(columns={"year": "Year", "annual_rainfall": "Annual Rainfall (mm)", "rainy_days": "Rainy Days"})
    return out


# ---------------------------------------------------------------------------
# Daily series (for the raw daily chart / calendar plot / downloads)
# ---------------------------------------------------------------------------
def daily_series(taluk: str, start_date, end_date) -> pd.DataFrame:
    sub = _daily[
        (_daily["taluk"] == taluk)
        & (_daily["date"] >= pd.Timestamp(start_date))
        & (_daily["date"] <= pd.Timestamp(end_date))
    ]
<<<<<<< HEAD
    out = sub.sort_values("date")[["date", "rainfall"]].copy()
    out["rainfall"] = out["rainfall"].astype("float64").round(1)
    return out
=======
    return sub.sort_values("date")[["date", "rainfall"]]
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af


# ---------------------------------------------------------------------------
# Map data -- one averaged annual value per taluk, for the choropleth
# ---------------------------------------------------------------------------
def map_values(start_date, end_date) -> pd.DataFrame:
    years = years_in_range(start_date, end_date)
    sub = _annual[_annual["year"].isin(years)]
<<<<<<< HEAD
    out = sub.groupby(["taluk", "district"], as_index=False, observed=True)["annual_rainfall"].mean()
    out["annual_rainfall"] = out["annual_rainfall"].astype("float64").round(1)
=======
    out = sub.groupby(["taluk", "district"], as_index=False)["annual_rainfall"].mean()
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
    return out


# ---------------------------------------------------------------------------
# Irrigation calendar (weekly rule: <30mm -> Irrigation Required, else No Irrigation)
# ---------------------------------------------------------------------------
def irrigation_calendar(taluk: str, start_date, end_date) -> pd.DataFrame:
    wk = weekly_climatology(taluk, start_date, end_date)
    wk["advisory"] = wk["avg_rain"].apply(
        lambda v: "Irrigation Required" if v < config.IRRIGATION_THRESHOLD_MM else "No Irrigation"
    )
    return wk
