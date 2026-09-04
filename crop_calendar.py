"""
crop_calendar.py
-----------------
Crop Irrigation Calendar, built around actual crop water requirement (CWR)
data instead of a flat rainfall threshold.

Source data (data/raw/NIK_All_Crops_SMW_Water_Requirements.xlsx, sheet
"SMW_Weekly_CWR_Breakdown") gives, for each crop, a week-by-week growth
profile: Kc (crop coefficient), ET0, and the resulting Weekly CWR (ETc, mm)
-- how much water the crop needs that week, regardless of calendar date.
That profile is anchored to a reference sowing week ("Sowing Window SMW").

Each crop in the sheet has exactly one variety/soil-type combination, so the
dashboard identifies and displays crops by name only (e.g. "Maize", not
"Maize - GH-0727"); the variety is still used internally to pick the right
rows out of the sheet, it's just not shown to the user.

The user picks their sowing week directly as "SMW 1 (Jan 1 - Jan 7)" ...
"SMW 52 (Dec 24 - Dec 31)" rather than a calendar date (a specific date adds
a year that doesn't matter here and just has to be converted back to a week
number anyway). We shift the whole crop-growth profile so it starts there:
the crop's "Week 1" lands on the chosen SMW, and every subsequent crop-week
advances one calendar SMW from there (wrapping past week 52 back to week 1).
The CWR figures themselves don't change -- a crop in its flowering week
needs the same water whether sown in SMW 35 or SMW 40 -- only which calendar
week (and therefore which rainfall climatology) that growth stage lines up
with changes.

For each resulting calendar SMW we pull the avg/min/max weekly rainfall from
the full 1996-2025 (30-year) climatology for the selected taluk -- fixed,
not the Rainfall page's adjustable date range, since the irrigation advisory
is meant to reflect the long-term normal, not whatever period happens to be
selected elsewhere in the app -- and compare it to that week's CWR:
avg rainfall < CWR  ->  Irrigation Required (shows the deficit, mm)
avg rainfall >= CWR ->  No Irrigation Required
"""
import re
import datetime
import pandas as pd

import config
import data_loader as dl

CROP_XLSX = f"{config.RAW_DIR}/NIK_All_Crops_SMW_Water_Requirements.xlsx"
CROP_SHEET = "SMW_Weekly_CWR_Breakdown"


def _parse_smw(value) -> int:
    """'SMW 39' -> 39 (also handles a bare int/float)."""
    if isinstance(value, (int, float)):
        return int(value)
    m = re.search(r"\d+", str(value))
    return int(m.group()) if m else None


def _parse_week(value) -> int:
    """'Week 1' -> 1."""
    if isinstance(value, (int, float)):
        return int(value)
    m = re.search(r"\d+", str(value))
    return int(m.group()) if m else None


def _load_raw() -> pd.DataFrame:
    df = pd.read_excel(CROP_XLSX, sheet_name=CROP_SHEET)
    df["crop_week"] = df["Crop Week"].apply(_parse_week)
    df["reference_sowing_smw"] = df["Sowing Window SMW"].apply(_parse_smw)
    df = df.rename(columns={
        "Crop": "crop", "Variety": "variety", "Soil Type": "soil_type",
        "Days in Week": "days_in_week", "Growth Stage": "growth_stage",
        "Kc (Crop Coeff)": "kc", "Benchmark ET0 (mm/day)": "et0_benchmark",
        "Weekly ET0 (mm)": "weekly_et0", "Weekly CWR (ETc mm)": "weekly_cwr",
        "Cumulative CWR (mm)": "cumulative_cwr",
    })
    return df.sort_values(["crop", "crop_week"]).reset_index(drop=True)


_CROP_DATA = _load_raw()


def available_crops() -> list:
    """[{'label': 'Rabi Sorghum (Jowar)', 'value': 'Rabi Sorghum (Jowar)'}, ...] --
    crop name only; each crop maps to exactly one variety/soil-type behind
    the scenes, so there's nothing for the user to disambiguate."""
    crops = sorted(_CROP_DATA["crop"].unique().tolist())
    return [{"label": c, "value": c} for c in crops]


# ---------------------------------------------------------------------------
# SMW <-> calendar date-range labels, e.g. "SMW 1 (Jan 1 - Jan 7)"
# ---------------------------------------------------------------------------
def smw_date_range(smw: int, ref_year: int = 2023):
    """(start_date, end_date) for a given SMW, using a fixed non-leap
    reference year purely to produce a Jan-1-anchored month/day label --
    the same day-of-year -> SMW rule used throughout the app
    (ceil(doy/7), capped at 52) is inverted here."""
    start_doy = (smw - 1) * 7 + 1
    end_doy = 365 if smw == 52 else smw * 7
    start = datetime.date(ref_year, 1, 1) + datetime.timedelta(days=start_doy - 1)
    end = datetime.date(ref_year, 1, 1) + datetime.timedelta(days=end_doy - 1)
    return start, end


def smw_label(smw: int) -> str:
    start, end = smw_date_range(smw)
    # Manual day formatting (not strftime's %-d / %#d) since that flag isn't
    # portable between Linux/Mac and Windows -- this app needs to run on both.
    start_str = f"{start.strftime('%b')} {start.day}"
    end_str = f"{end.strftime('%b')} {end.day}"
    return f"SMW {smw} ({start_str} - {end_str})"


def smw_options() -> list:
    """[{'label': 'SMW 1 (Jan 1 - Jan 7)', 'value': 1}, ..., 'SMW 52 (Dec 24 - Dec 31)']"""
    return [{"label": smw_label(w), "value": w} for w in range(1, 53)]


def build_crop_calendar(crop: str, taluk: str, sowing_smw: int) -> pd.DataFrame:
    """The main entry point: returns one row per crop-week with the growth
    stage, CWR, the taluk's 30-year rainfall climatology for that calendar
    week, and the irrigation advisory. sowing_smw is 1-52, as selected from
    the SMW dropdown."""
    profile = _CROP_DATA[_CROP_DATA["crop"] == crop].copy()
    profile = profile.sort_values("crop_week").reset_index(drop=True)
    variety = profile["variety"].iloc[0] if not profile.empty else None

    sowing_smw = int(sowing_smw)
    wk_clim = dl.weekly_climatology(taluk, config.MIN_DATE, config.MAX_DATE).set_index("smw")

    rows = []
    for _, r in profile.iterrows():
        calendar_smw = ((sowing_smw - 1) + (r["crop_week"] - 1)) % 52 + 1

        if calendar_smw in wk_clim.index:
            avg_rain = float(wk_clim.loc[calendar_smw, "avg_rain"])
            min_rain = float(wk_clim.loc[calendar_smw, "min_rain"])
            max_rain = float(wk_clim.loc[calendar_smw, "max_rain"])
        else:
            avg_rain = min_rain = max_rain = 0.0

        cwr = float(r["weekly_cwr"])
        deficit = max(0.0, cwr - avg_rain)
        advisory = "Irrigation Required" if avg_rain < cwr else "No Irrigation Required"

        rows.append({
            "crop_week": int(r["crop_week"]),
            "calendar_smw": int(calendar_smw),
            "growth_stage": r["growth_stage"],
            "kc": r["kc"],
            "weekly_cwr_mm": round(cwr, 1),
            "cumulative_cwr_mm": round(float(r["cumulative_cwr"]), 1),
            "avg_rain_mm": round(avg_rain, 1),
            "min_rain_mm": round(min_rain, 1),
            "max_rain_mm": round(max_rain, 1),
            "deficit_mm": round(deficit, 1),
            "advisory": advisory,
        })

    out = pd.DataFrame(rows)
    out.attrs["crop"] = crop
    out.attrs["variety"] = variety
    out.attrs["taluk"] = taluk
    out.attrs["sowing_smw"] = sowing_smw
    out.attrs["sowing_smw_label"] = smw_label(sowing_smw)
    return out


def crop_calendar_summary(cal: pd.DataFrame) -> dict:
    total_weeks = len(cal)
    total_cwr = float(cal["weekly_cwr_mm"].sum())
    total_expected_rain = float(cal["avg_rain_mm"].sum())
    net_irrigation = max(0.0, total_cwr - total_expected_rain)
    weeks_needing_irrigation = int((cal["advisory"] == "Irrigation Required").sum())
    return {
        "total_weeks": total_weeks,
        "total_cwr_mm": round(total_cwr, 1),
        "total_expected_rain_mm": round(total_expected_rain, 1),
        "net_irrigation_mm": round(net_irrigation, 1),
        "weeks_needing_irrigation": weeks_needing_irrigation,
    }
