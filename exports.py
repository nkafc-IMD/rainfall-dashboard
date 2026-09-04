"""
exports.py
----------
Phase 7 (Download Centre): PDF Report, PNG Maps, Graph Images, JSON Export.
(CSV and Excel are handled directly in app.py, next to the sidebar's
"Download Excel" button.)

Deliberately uses matplotlib + reportlab instead of Plotly/Kaleido for image
export: Kaleido v1 needs a local Chrome install (`plotly_get_chrome`), which
is one more thing to set up on the IIS server. matplotlib has no such
dependency, so PNG/PDF export works out of the box wherever Python runs.
"""
import io
import json
import zipfile

import geopandas as gpd
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors as rl_colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import config
import data_loader as dl

NAVY = "#1f4e79"
ACCENT = "#e07b1a"

<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
# Built from the GeoJSON dict data_loader already parsed at import time,
# rather than gpd.read_file()-ing the same file again from disk -- that
# redundant second parse cost ~36MB of resident memory for no benefit,
# which matters on a memory-constrained host (see DEPLOYMENT.md).
_GDF = gpd.GeoDataFrame.from_features(dl.TALUKS_GEOJSON["features"], crs="EPSG:4326")

_plt = None  # lazily imported -- see _get_plt() below


def _get_plt():
    """matplotlib costs ~25MB of resident memory just to import, and this
    module is the only place in the app that needs it (Plotly/Kaleido would
    need a local Chrome install instead -- see the module docstring). Most
    server processes may go their whole lifetime without anyone downloading
    a PDF/PNG/graph-images ZIP, so importing it lazily on first actual use
    -- rather than paying that cost at server startup for every process --
    matters on a memory-constrained host. Cached after the first call, so
    this costs nothing on subsequent chart renders."""
    global _plt
    if _plt is None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        _plt = plt
    return _plt
<<<<<<< HEAD
=======
=======
_GDF = gpd.read_file(config.TALUKS_GEOJSON)
if "KGISTalukN" in _GDF.columns:
    _GDF = _GDF.rename(columns={"KGISTalukN": "taluk", "DISTRICT": "district"})
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7


# ---------------------------------------------------------------------------
# Chart PNGs (matplotlib, returns PNG bytes)
# ---------------------------------------------------------------------------
def _fig_to_png_bytes(fig) -> bytes:
<<<<<<< HEAD
    plt = _get_plt()
=======
<<<<<<< HEAD
    plt = _get_plt()
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def render_weekly_png(taluk: str, start_date, end_date) -> bytes:
<<<<<<< HEAD
    plt = _get_plt()
=======
<<<<<<< HEAD
    plt = _get_plt()
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    wk = dl.weekly_climatology(taluk, start_date, end_date)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.plot(wk["smw"], wk["avg_rain"], color="#2e7d32", linewidth=2)
    ax.set_xlabel("SMW")
    ax.set_ylabel("Avg Weekly Rainfall (mm)")
    ax.set_title(f"Weekly Average Rainfall (SMW) — {taluk}")
    ax.grid(alpha=0.3)
    return _fig_to_png_bytes(fig)


def render_monthly_png(taluk: str, start_date, end_date) -> bytes:
<<<<<<< HEAD
    plt = _get_plt()
=======
<<<<<<< HEAD
    plt = _get_plt()
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    mo = dl.monthly_climatology(taluk, start_date, end_date)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.bar([f"{m:02d}" for m in mo["month"]], mo["avg_rain"], color="#7ec8e3")
    ax.set_xlabel("Month")
    ax.set_ylabel("Avg Monthly Rainfall (mm)")
    ax.set_title(f"Monthly Average Rainfall — {taluk}")
    ax.grid(alpha=0.3, axis="y")
    return _fig_to_png_bytes(fig)


def render_trend_png(taluk: str, start_date, end_date) -> bytes:
    import analytics as an
<<<<<<< HEAD
    plt = _get_plt()
=======
<<<<<<< HEAD
    plt = _get_plt()
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    tr = an.rainfall_trend(taluk, start_date, end_date)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.bar(tr["year"], tr["annual_rainfall"], color="#7ec8e3", label="Annual Rainfall")
    ax.plot(tr["year"], tr["trend"], color="#c0392b", linewidth=2, label="Linear Trend")
    ax.set_xlabel("Year")
    ax.set_ylabel("Annual Rainfall (mm)")
    ax.set_title(f"Annual Rainfall Trend — {taluk}")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")
    return _fig_to_png_bytes(fig)


# ---------------------------------------------------------------------------
# Map PNG (matplotlib + geopandas -- mirrors the sidebar Leaflet map)
# ---------------------------------------------------------------------------
def render_map_png(district: str, selected_taluk: str) -> bytes:
<<<<<<< HEAD
    plt = _get_plt()
=======
<<<<<<< HEAD
    plt = _get_plt()
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    sub = _GDF[_GDF["district"] == district]
    fig, ax = plt.subplots(figsize=(6, 6))
    sub.plot(ax=ax, color="#ffe8c7", edgecolor="#8a5a1e", linewidth=1)
    sel = sub[sub["taluk"] == selected_taluk]
    if not sel.empty:
        sel.plot(ax=ax, color=ACCENT, edgecolor="#8a5a1e", linewidth=2)
    for _, row in sub.iterrows():
        pt = row.geometry.representative_point()
        ax.annotate(row["taluk"], (pt.x, pt.y), fontsize=7, ha="center", color="#333")
    ax.set_title(f"{district} District — {selected_taluk} highlighted")
    ax.set_axis_off()
    return _fig_to_png_bytes(fig)


def render_region_map_png(color_map: dict, title: str) -> bytes:
    """Whole-region (112 taluk) static map, used by the Phase 6 spatial tab
    if the user wants a PNG of the ranking/zones/hotspot map."""
<<<<<<< HEAD
    plt = _get_plt()
=======
<<<<<<< HEAD
    plt = _get_plt()
=======
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
>>>>>>> d7e7f5a9f1617f0743e7f5e566e24bfb35b4aea7
    gdf = _GDF.copy()
    gdf["_color"] = gdf["taluk"].map(color_map).fillna("#e0e0e0")
    fig, ax = plt.subplots(figsize=(7, 7))
    gdf.plot(ax=ax, color=gdf["_color"], edgecolor="#666666", linewidth=0.4)
    ax.set_title(title)
    ax.set_axis_off()
    return _fig_to_png_bytes(fig)


# ---------------------------------------------------------------------------
# JSON export -- full processed data package for the selected taluk/period
# ---------------------------------------------------------------------------
def build_json_export(taluk: str, district: str, start_date, end_date) -> bytes:
    import analytics as an

    payload = {
        "taluk": taluk,
        "district": district,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "annual_average_rainfall_mm": dl.annual_average(taluk, start_date, end_date),
        "daily": dl.daily_series(taluk, start_date, end_date).assign(
            date=lambda d: d["date"].astype(str)
        ).to_dict("records"),
        "weekly_smw": dl.weekly_climatology(taluk, start_date, end_date).to_dict("records"),
        "monthly": dl.monthly_climatology(taluk, start_date, end_date).to_dict("records"),
        "annual": dl.annual_series(taluk, start_date, end_date).to_dict("records"),
        "irrigation_calendar": dl.irrigation_calendar(taluk, start_date, end_date).to_dict("records"),
        "statistics": an.summary_statistics(taluk, start_date, end_date),
    }
    return json.dumps(payload, indent=2, default=str).encode("utf-8")


# ---------------------------------------------------------------------------
# Graph Images -- zip of the three chart PNGs + the map PNG
# ---------------------------------------------------------------------------
def build_graph_images_zip(taluk: str, district: str, start_date, end_date) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("weekly_rainfall.png", render_weekly_png(taluk, start_date, end_date))
        zf.writestr("monthly_rainfall.png", render_monthly_png(taluk, start_date, end_date))
        zf.writestr("annual_trend.png", render_trend_png(taluk, start_date, end_date))
        zf.writestr("taluk_map.png", render_map_png(district, taluk))
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# PDF Report -- one-page-plus summary using reportlab
# ---------------------------------------------------------------------------
def build_pdf_report(taluk: str, district: str, start_date, end_date) -> bytes:
    import analytics as an

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleNavy", parent=styles["Title"], textColor=rl_colors.HexColor(NAVY))
    heading_style = ParagraphStyle("HeadingNavy", parent=styles["Heading2"], textColor=rl_colors.HexColor(NAVY))
    normal = styles["Normal"]

    story = []
    story.append(Paragraph("North Karnataka Agrometeorological Forecasting and Research Centre", normal))
    story.append(Paragraph("Taluk Rainfall Report", title_style))
    story.append(Paragraph(f"District: {district} &nbsp;|&nbsp; Taluk: {taluk}", normal))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", normal))
    story.append(Spacer(1, 10))

    avg_annual = dl.annual_average(taluk, start_date, end_date)
    story.append(Paragraph(f"<b>Annual Average Rainfall: {avg_annual:.1f} mm/year</b>", styles["Heading3"]))
    story.append(Spacer(1, 6))

    # Map + weekly + monthly + trend images
    for label, png_bytes, width in [
        ("Taluk Location", render_map_png(district, taluk), 9 * cm),
        ("Weekly Average Rainfall (SMW)", render_weekly_png(taluk, start_date, end_date), 16 * cm),
        ("Monthly Average Rainfall", render_monthly_png(taluk, start_date, end_date), 16 * cm),
        ("Annual Rainfall Trend", render_trend_png(taluk, start_date, end_date), 16 * cm),
    ]:
        story.append(Paragraph(label, heading_style))
        img = RLImage(io.BytesIO(png_bytes))
        img.drawWidth = width
        img.drawHeight = width * img.imageHeight / img.imageWidth
        story.append(img)
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # Irrigation calendar summary table (first 15 weeks, to keep it to a page)
    story.append(Paragraph("Crop Irrigation Calendar (first 15 SMW)", heading_style))
    irr = dl.irrigation_calendar(taluk, start_date, end_date).head(15)
    table_data = [["SMW", "Avg Rain (mm)", "Min (mm)", "Max (mm)", "Advisory"]]
    for _, row in irr.iterrows():
        table_data.append([
            int(row["smw"]), f"{row['avg_rain']:.1f}", f"{row['min_rain']:.1f}",
            f"{row['max_rain']:.1f}", row["advisory"],
        ])
    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, rl_colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # Summary statistics table
    story.append(Paragraph("Statistical Summary", heading_style))
    stats = an.summary_statistics(taluk, start_date, end_date)
    stats_labels = {
        "mean_rainy_day_mm": "Mean (rainy days, mm)",
        "median_rainy_day_mm": "Median (rainy days, mm)",
        "std_rainy_day_mm": "Std Dev (rainy days, mm)",
        "cv_pct": "Coefficient of Variation (%)",
        "total_rainy_days": "Total rainy days in period",
        "avg_annual_rainy_days": "Average rainy days per year",
        "avg_annual_max_dry_spell_days": "Average annual longest dry spell (days)",
    }
    stats_table = [["Statistic", "Value"]] + [
        [label, f"{stats[k]:.1f}" if isinstance(stats[k], float) else str(stats[k])]
        for k, label in stats_labels.items()
    ]
    t2 = Table(stats_table, repeatRows=1, colWidths=[9 * cm, 5 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor(NAVY)),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, rl_colors.grey),
    ]))
    story.append(t2)
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "Generated by the North Karnataka Taluk Rainfall Dashboard. "
        "Averages are computed as the mean of each selected year's total "
        "(SMW / month / year), not a pooled mean of raw daily values.",
        ParagraphStyle("Footnote", parent=normal, fontSize=7, textColor=rl_colors.grey),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
