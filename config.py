"""
config.py
Central configuration for the North Karnataka Taluk Rainfall Dashboard.
Edit paths / constants here rather than inside app logic.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

RAW_PARQUET = os.path.join(RAW_DIR, "rainfall_taluk_daily_1996_2025.parquet")
RAW_SHAPEFILE = os.path.join(RAW_DIR, "NIK_Taluks_Updated.shp")

DAILY_PARQUET = os.path.join(PROCESSED_DIR, "daily.parquet")
WEEKLY_PARQUET = os.path.join(PROCESSED_DIR, "weekly_smw.parquet")
MONTHLY_PARQUET = os.path.join(PROCESSED_DIR, "monthly.parquet")
ANNUAL_PARQUET = os.path.join(PROCESSED_DIR, "annual.parquet")
TALUK_LOOKUP = os.path.join(PROCESSED_DIR, "taluk_lookup.parquet")
TALUKS_GEOJSON = os.path.join(PROCESSED_DIR, "taluks_4326.geojson")

# ---------------------------------------------------------------------------
# Data range
# ---------------------------------------------------------------------------
MIN_YEAR = 1996
MAX_YEAR = 2025
MIN_DATE = f"{MIN_YEAR}-01-01"
MAX_DATE = f"{MAX_YEAR}-12-31"

# ---------------------------------------------------------------------------
# Irrigation advisory rule (weekly rainfall, mm)
#   < 30 mm  -> Irrigation Required
#   >= 30 mm -> No Irrigation
# ---------------------------------------------------------------------------
IRRIGATION_THRESHOLD_MM = 30.0

# ---------------------------------------------------------------------------
# Map / branding
# ---------------------------------------------------------------------------
APP_TITLE = "Taluk Rainfall Dashboard (1996-2025)"
MAP_CENTER = (15.7, 75.6)   # approx centre of North Karnataka
MAP_ZOOM = 7

COLORS = {
    "primary": "#1f4e79",     # IMD navy blue (cards, headings, accents)
    "navbar": "#1565d8",      # bright blue navbar
    "accent": "#e07b1a",      # highlight orange (matches screenshot taluk fill)
    "bg": "#f5f6f8",
    "card": "#ffffff",
    "text": "#222222",
}

RAINFALL_COLOR_BINS = [0, 5, 10, 20, 40, 80, 150, 300]
RAINFALL_COLOR_SCALE = [
    "#ffffcc", "#c7e9b4", "#7fcdbb", "#41b6c4",
    "#2c7fb8", "#253494", "#081d58",
]

# ---------------------------------------------------------------------------
# Feedback (Google Form embed)
# ---------------------------------------------------------------------------
# Paste your Google Form's embed URL here once you've created one:
# Form -> Send -> the "<>" embed icon -> copy the src="..." URL from the
# <iframe>. Leave blank and the Feedback tab shows setup instructions
# instead of a broken embed.
FEEDBACK_FORM_URL = "https://forms.gle/dQAqToNiBM4oL2X99"
CONTACT_EMAIL = "nkafcimd@gmail.com"
CONTACT_ADDRESS = (
    "North Karnataka Agrometeorological Forecasting and Research Centre, IMD, "
    "Organic Farming Dept, UASD College, 500085"
)
