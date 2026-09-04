"""
advanced_charts.py
------------------
Phase 5 (Advanced Charts) data helpers: Histogram, Box Plot, Heatmap,
Calendar Plot, Violin Plot, Scatter Plot + Trend Line, Monthly Climatology,
Decadal Comparison.

Same rule as the rest of the app applies wherever an "average" is produced:
per-year figures first, then averaged across the selected years.
"""
import numpy as np
import pandas as pd

import data_loader as dl

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------------------
# 5.1 Histogram -- distribution of daily rainfall on rainy days
# ---------------------------------------------------------------------------
def histogram_data(taluk: str, start_date, end_date) -> pd.Series:
    daily = dl.daily_series(taluk, start_date, end_date)
    return daily.loc[daily["rainfall"] > 0, "rainfall"]


# ---------------------------------------------------------------------------
# 5.2 / 5.5 Box Plot & Violin Plot -- monthly rainfall distribution (one
# total per taluk/year/month), spread across the selected years
# ---------------------------------------------------------------------------
def monthly_distribution(taluk: str, start_date, end_date) -> pd.DataFrame:
    years = dl.years_in_range(start_date, end_date)
    sub = dl._monthly[(dl._monthly["taluk"] == taluk) & (dl._monthly["year"].isin(years))].copy()
    sub["month_name"] = sub["month"].apply(lambda m: MONTH_NAMES[m - 1])
    return sub[["year", "month", "month_name", "monthly_rainfall"]].sort_values("month")


# ---------------------------------------------------------------------------
# 5.3 Heatmap -- year x month total rainfall matrix
# ---------------------------------------------------------------------------
def heatmap_matrix(taluk: str, start_date, end_date) -> pd.DataFrame:
    years = dl.years_in_range(start_date, end_date)
    sub = dl._monthly[(dl._monthly["taluk"] == taluk) & (dl._monthly["year"].isin(years))]
    pivot = sub.pivot_table(index="year", columns="month", values="monthly_rainfall", fill_value=0)
    pivot = pivot.reindex(columns=range(1, 13), fill_value=0)
    pivot.columns = MONTH_NAMES
    return pivot.sort_index()


# ---------------------------------------------------------------------------
# 5.4 Calendar Plot -- daily rainfall for ONE selected year (GitHub-style grid)
# ---------------------------------------------------------------------------
def calendar_year_data(taluk: str, year: int) -> pd.DataFrame:
    sub = dl._daily[(dl._daily["taluk"] == taluk) & (dl._daily["year"] == year)].copy()
    sub["date"] = pd.to_datetime(sub["date"])
    sub["dow"] = sub["date"].dt.weekday          # 0=Mon
    sub["week"] = sub["date"].dt.isocalendar().week.astype(int)
    # ISO week 52/53 from late Dec can wrap to next year's week 1 -- push to week 53
    sub.loc[(sub["date"].dt.month == 1) & (sub["week"] > 50), "week"] = 0
    sub.loc[(sub["date"].dt.month == 12) & (sub["week"] == 1), "week"] = 53
    return sub[["date", "dow", "week", "rainfall"]].sort_values("date")


# ---------------------------------------------------------------------------
# 5.6 Scatter Plot + 5.7 Trend Line -- annual rainfall vs rainy days
# ---------------------------------------------------------------------------
def scatter_rainfall_vs_rainydays(taluk: str, start_date, end_date) -> pd.DataFrame:
    s = dl.annual_series(taluk, start_date, end_date).reset_index(drop=True)
    if len(s) >= 2:
        coeffs = np.polyfit(s["rainy_days"], s["annual_rainfall"], 1)
        s["trend"] = np.polyval(coeffs, s["rainy_days"])
    else:
        s["trend"] = s["annual_rainfall"]
    return s


# ---------------------------------------------------------------------------
# 5.8 Monthly Climatology -- mean +/- 1 std-dev band per month
# ---------------------------------------------------------------------------
def monthly_climatology_band(taluk: str, start_date, end_date) -> pd.DataFrame:
    dist = monthly_distribution(taluk, start_date, end_date)
    out = (
        dist.groupby("month", as_index=False)["monthly_rainfall"]
        .agg(mean="mean", std="std")
        .sort_values("month")
    )
    out["std"] = out["std"].fillna(0)
    out["month_name"] = out["month"].apply(lambda m: MONTH_NAMES[m - 1])
    out["upper"] = out["mean"] + out["std"]
    out["lower"] = (out["mean"] - out["std"]).clip(lower=0)
    return out


# ---------------------------------------------------------------------------
# 5.9 Decadal Comparison -- avg monthly rainfall, grouped into 10-year blocks
# aligned to the data's own 1996-2025 span (calendar decades like "2000s"
# would leave 1996-1999 and 2020-2025 as partial, misleading buckets)
# ---------------------------------------------------------------------------
DECADE_BUCKETS = [
    ("1996-2005", 1996, 2005),
    ("2006-2015", 2006, 2015),
    ("2016-2025", 2016, 2025),
]


def decadal_comparison(taluk: str, start_date, end_date) -> pd.DataFrame:
    years = set(dl.years_in_range(start_date, end_date))
    sub = dl._monthly[(dl._monthly["taluk"] == taluk) & (dl._monthly["year"].isin(years))].copy()

    def decade_label(y):
        for label, y0, y1 in DECADE_BUCKETS:
            if y0 <= y <= y1:
                return label
        return None

    sub["decade"] = sub["year"].apply(decade_label)
    sub = sub.dropna(subset=["decade"])
    out = (
        sub.groupby(["decade", "month"], as_index=False)["monthly_rainfall"]
        .mean()
        .sort_values(["decade", "month"])
    )
    out["month_name"] = out["month"].apply(lambda m: MONTH_NAMES[m - 1])
    return out
