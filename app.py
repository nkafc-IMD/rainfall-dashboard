"""
app.py -- North Karnataka Taluk Rainfall Dashboard (1996-2025)
Python/Dash re-implementation of the original R/Shiny + Leaflet dashboard.

Run locally:
    python app.py                 (dev server, http://127.0.0.1:8050)

Run for production (see README.md for full IIS instructions):
    waitress-serve --listen=0.0.0.0:8050 app:server
"""
import io
import os
import time
import traceback
from datetime import date

import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx, ALL
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash_extensions.javascript import assign
import plotly.graph_objects as go
import pandas as pd
import numpy as np

import config
import data_loader as dl_data
import map_utils
import analytics as an
import advanced_charts as ac
import spatial as sp
import exports as ex
import crop_calendar as cropcal
from plotly.colors import sample_colorscale

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
# When running locally (python app.py) the app is served from "/". When
# deployed behind IIS at a sub-path (e.g. /NKAFC/IMD/RainfallDashboard/),
# set the DASH_URL_PREFIX environment variable to that path (see README.md
# "Deploying behind IIS") so Dash builds every asset/callback URL correctly.
URL_PREFIX = os.environ.get("DASH_URL_PREFIX", "/")
<<<<<<< HEAD
=======
print("=" * 60)
print("DASH_URL_PREFIX =", os.environ.get("DASH_URL_PREFIX"))
print("URL_PREFIX      =", URL_PREFIX)
print("=" * 60)
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
if not URL_PREFIX.endswith("/"):
    URL_PREFIX += "/"

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    title=config.APP_TITLE,
    suppress_callback_exceptions=True,
    requests_pathname_prefix=URL_PREFIX,
<<<<<<< HEAD
=======
    routes_pathname_prefix=URL_PREFIX,
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
)
server = app.server  # exposed for waitress / IIS (Phase 13)

geojson_style = assign("""function(feature) {
    return {
        fillColor: feature.properties.color,
        color: feature.properties.borderColor || '#8a5a1e',
        weight: feature.properties.borderWeight !== undefined ? feature.properties.borderWeight
                : (feature.properties.color === '#e07b1a' ? 2.5 : 1),
        fillOpacity: feature.properties.fillOpacity
    };
}""")

geojson_style_plain = assign("""function(feature) {
    return {
        fillColor: feature.properties.color,
        color: '#666666',
        weight: 1,
        fillOpacity: feature.properties.fillOpacity
    };
}""")

# ---------------------------------------------------------------------------
# Filters bar (district / taluk / date range / actions) -- horizontal, full
# width, sitting above the KPI cards (matches the requested reference layout)
# ---------------------------------------------------------------------------
default_district = "Dharwad" if "Dharwad" in dl_data.DISTRICTS else dl_data.DISTRICTS[0]
default_taluks = dl_data.TALUKS_BY_DISTRICT[default_district]
default_taluk = "Hubballi" if "Hubballi" in default_taluks else default_taluks[0]

filters_bar = dbc.Card(
    dbc.CardBody(
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("District", className="ctrl-label"),
                        dcc.Dropdown(
                            id="district-dd",
                            options=[{"label": d, "value": d} for d in dl_data.DISTRICTS],
                            value=default_district,
                            clearable=False,
                        ),
                    ],
                    xs=12, sm=6, lg=3,
                ),
                dbc.Col(
                    [
                        dbc.Label("Taluk", className="ctrl-label"),
                        dcc.Dropdown(
                            id="taluk-dd",
                            options=[{"label": t, "value": t} for t in default_taluks],
                            value=default_taluk,
                            clearable=False,
                        ),
                    ],
                    xs=12, sm=6, lg=3,
                ),
                dbc.Col(
                    [
                        dbc.Label("Date Range", className="ctrl-label"),
                        dcc.DatePickerRange(
                            id="date-range",
                            min_date_allowed=date(config.MIN_YEAR, 1, 1),
                            max_date_allowed=date(config.MAX_YEAR, 12, 31),
                            start_date=date(config.MIN_YEAR, 1, 1),
                            end_date=date(config.MAX_YEAR, 12, 31),
                            display_format="YYYY-MM-DD",
                            className="w-100",
                        ),
                    ],
                    xs=12, sm=8, lg=4,
                ),
                dbc.Col(
                    [
                        html.Div(className="d-none d-lg-block", style={"height": "22px"}),
                        dbc.Button("GO", id="go-btn", color="primary", className="w-100 go-btn"),
                    ],
                    xs=12, sm=4, lg=2,
                ),
            ],
            className="g-3 align-items-end",
        )
    ),
    className="filters-bar-card",
)

quick_map_card = dbc.Card(
    dbc.CardBody(
        [
            html.Div(
                [
                    html.I(className="fa-solid fa-map-location-dot me-2"),
                    html.Span("Tap any taluk to select it", className="quick-map-title"),
                ],
                className="quick-map-header",
            ),
            dl.Map(
                id="taluk-map",
                center=config.MAP_CENTER,
                zoom=config.MAP_ZOOM,
                children=[
                    dl.TileLayer(),
                    dl.GeoJSON(id="taluk-geojson", style=geojson_style,
                               hoverStyle=dict(weight=3, color="#333", fillOpacity=0.9)),
                ],
                style={"width": "100%", "height": "260px", "marginTop": "8px"},
            ),
        ]
    ),
    className="quick-map-card",
)


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
def _kpi_card(icon, label, value_id, color, xs=6, lg=3):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.I(className=f"{icon} kpi-card-icon", style={"color": color}),
                    html.Div(label, className="kpi-card-label"),
                    html.Div(id=value_id, className="kpi-card-value"),
                ]
            ),
            className="kpi-card",
        ),
        xs=xs, lg=lg,
    )


def _home_feature_card(icon, title, body):
    return dbc.Card(
        dbc.CardBody(
            [
                html.I(className=f"{icon} home-feature-icon"),
                html.H5(title, className="home-feature-title"),
                html.P(body, className="home-feature-body"),
            ]
        ),
        className="home-feature-card",
    )


kpi_row = dbc.Row(
    [
        _kpi_card("fa-solid fa-cloud-rain", "Annual Average Rainfall", "kpi-annual-avg", "#1f4e79",
                  xs=12, lg=5),
    ],
    className="g-3 mb-3",
)

weekly_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H6("Weekly Average Rainfall (SMW)", className="chart-title"),
                dcc.Graph(id="weekly-graph", config={"displaylogo": False}),
            ]
        )
    ],
    className="chart-card",
)

monthly_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H6("Monthly Average Rainfall", className="chart-title"),
                dcc.Graph(id="monthly-graph", config={"displaylogo": False}),
            ]
        )
    ],
    className="chart-card",
)

def _chart_card(title, graph_id, height=None, description=None):
    children = [html.H6(title, className="chart-title")]
    if description:
        children.append(html.P(description, className="chart-desc"))
    children.append(dcc.Graph(id=graph_id, config={"displaylogo": False}))
    return dbc.Card(dbc.CardBody(children), className="chart-card")


analytics_tab = html.Div(
    [
        html.Div(id="trend-note", className="irrigation-heading"),
        _chart_card("Annual Rainfall Trend & 5-Year Moving Average", "trend-graph"),
        _chart_card(
            "Cumulative Rainfall (climatological build-up)", "cumulative-graph",
            description=(
                "Shows how the season's rain typically accumulates day by day: for each "
                "day of the year, the average rainfall across the selected years is added "
                "to a running total. The curve rises fastest during the monsoon months and "
                "flattens in the dry season, so its shape shows when most of the year's "
                "rain usually falls, and the final value matches the Annual Average Rainfall KPI."
            ),
        ),
        dbc.Row(
            [
                dbc.Col(_chart_card(
                    "Rainfall Anomaly (% departure from period mean)", "anomaly-graph",
                    description="How far each year's total rainfall is above (blue) or below (red) the average for the selected period.",
                ), md=6),
                dbc.Col(_chart_card(
                    "Standardized Rainfall (Z-score)", "spi-graph",
                    description="Each year's rainfall expressed in standard deviations from the mean — a simple SPI-style drought/wet-year indicator.",
                ), md=6),
            ]
        ),
        _chart_card("Seasonal Rainfall", "seasonal-graph"),
        html.H6("Wettest & Driest Taluks (selected period, all 112 taluks)", className="chart-title mt-2"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div("Top 10 Wettest", className="ranking-subtitle"),
                        dash_table.DataTable(
                            id="wettest-table",
                            style_cell={"textAlign": "left", "padding": "6px", "fontSize": "13px"},
                            style_header={"fontWeight": "bold", "backgroundColor": "#f0f2f5"},
                        ),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        html.Div("Top 10 Driest", className="ranking-subtitle"),
                        dash_table.DataTable(
                            id="driest-table",
                            style_cell={"textAlign": "left", "padding": "6px", "fontSize": "13px"},
                            style_header={"fontWeight": "bold", "backgroundColor": "#f0f2f5"},
                        ),
                    ],
                    md=6,
                ),
            ]
        ),
    ],
    className="analytics-panel",
)

statistics_tab = html.Div(
    [
        html.Div(id="stats-heading", className="irrigation-heading"),
        html.P(
            "Mean / median / percentiles / CV are computed on rainy days only "
            "(daily rainfall > 0 mm); including the long dry season would make "
            "these figures meaningless. \"Dry spell\" uses the IMD convention "
            "of a dry day as < 2.5 mm.",
            className="stats-note",
        ),
        dash_table.DataTable(
            id="stats-table",
            columns=[
                {"name": "Statistic", "id": "Statistic"},
                {"name": "Value", "id": "Value"},
                {"name": "What it means", "id": "Description"},
            ],
            style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
            style_cell_conditional=[{"if": {"column_id": "Description"}, "minWidth": "280px", "whiteSpace": "normal"}],
            style_header={"fontWeight": "bold", "backgroundColor": "#f0f2f5"},
            style_table={"maxWidth": "820px"},
        ),
    ],
    className="statistics-panel",
)

advanced_tab = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(_chart_card("Histogram — Daily Rainfall (rainy days)", "histogram-graph"), md=6),
                dbc.Col(_chart_card("Scatter — Annual Rainfall vs Rainy Days (+ trend)", "scatter-graph"), md=6),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(_chart_card("Box Plot — Monthly Rainfall Distribution", "boxplot-graph"), md=6),
                dbc.Col(_chart_card("Violin Plot — Monthly Rainfall Distribution", "violin-graph"), md=6),
            ]
        ),
        _chart_card("Heatmap — Year x Month Rainfall (mm)", "heatmap-graph"),
        _chart_card("Monthly Climatology (mean ± 1 std-dev band)", "climatology-band-graph"),
        _chart_card("Decadal Comparison — Avg Monthly Rainfall by Decade", "decadal-graph"),
        html.Div(
            [
                html.Div("Calendar Plot — pick a year:", className="ranking-subtitle d-inline-block me-2"),
                dcc.Dropdown(id="calendar-year-dd", clearable=False, style={"width": "140px", "display": "inline-block"}),
            ],
            className="mt-2 mb-2",
        ),
        _chart_card("Calendar Plot — Daily Rainfall for Selected Year", "calendar-graph"),
    ],
    className="advanced-panel",
)

spatial_tab = html.Div(
    [
        html.Div("Region Map", className="ranking-subtitle"),
        dbc.RadioItems(
            id="spatial-map-mode",
            options=[
                {"label": "Rainfall Ranking", "value": "ranking"},
                {"label": "Rainfall Zones", "value": "zones"},
                {"label": "Hotspot Analysis (Getis-Ord Gi*)", "value": "hotspot"},
            ],
            value="ranking",
            inline=True,
            className="mb-2",
        ),
        dbc.Card(
            dbc.CardBody(
                [
                    dl.Map(
                        id="spatial-map",
                        center=config.MAP_CENTER, zoom=6,
                        children=[dl.TileLayer(), dl.GeoJSON(id="spatial-geojson",
                                                              style=geojson_style_plain,
                                                              hoverStyle=dict(weight=3, color="#333"))],
                        style={"width": "100%", "height": "420px"},
                    ),
                    html.Div(id="spatial-legend", className="mt-2"),
                ]
            ),
            className="chart-card",
        ),
        _chart_card("District Ranking (avg annual rainfall)", "district-ranking-graph"),
        _chart_card("Spatial Interpolation (IDW, region-wide)", "idw-graph"),
        html.Div(id="hotspot-note", className="irrigation-heading"),
        dash_table.DataTable(
            id="hotspot-table",
            style_cell={"textAlign": "left", "padding": "6px", "fontSize": "13px"},
            style_header={"fontWeight": "bold", "backgroundColor": "#f0f2f5"},
            page_size=10,
            sort_action="native",
        ),
        html.Hr(),
        html.Div("Choropleth Animation / Time Slider", className="ranking-subtitle mt-2"),
        html.Div(
            [
                dbc.Button("Play", id="anim-play-btn", color="primary", size="sm", className="me-2"),
                html.Span(id="anim-year-label", className="kpi-value"),
            ],
            className="d-flex align-items-center mb-2",
        ),
        dcc.Slider(id="year-slider", step=1, tooltip={"placement": "bottom"}),
        dcc.Interval(id="anim-interval", interval=900, disabled=True),
        dbc.Card(
            dbc.CardBody(
                dl.Map(
                    id="animation-map",
                    center=config.MAP_CENTER, zoom=6,
                    children=[dl.TileLayer(), dl.GeoJSON(id="animation-geojson", style=geojson_style_plain)],
                    style={"width": "100%", "height": "420px", "marginTop": "10px"},
                )
            ),
            className="chart-card",
        ),
    ],
    className="spatial-panel",
)

def _download_row(label, description, btn_id, dl_id, icon="fa-download"):
    return dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(label, className="dl-row-title"),
                    html.Div(description, className="dl-row-desc"),
                ],
                md=8,
            ),
            dbc.Col(
                [
                    dbc.Button([html.I(className=f"fa {icon} me-2"), "Download"],
                               id=btn_id, color="light", className="w-100 dl-btn"),
                    dcc.Download(id=dl_id),
                ],
                md=4,
            ),
        ],
        className="dl-row",
    )


download_tab = html.Div(
    [
        html.P(
            "All downloads use the taluk / date range currently selected in the sidebar "
            "(click GO first to apply a new selection).",
            className="stats-note",
        ),
        _download_row("CSV — Daily Rainfall", "Raw daily rainfall for the selected taluk and period.",
                      "dl-csv-btn", "dl-csv"),
        _download_row("Excel Workbook", "Daily / Weekly / Monthly / Annual / Trend / Anomaly / Statistics sheets.",
                      "dl-excel-btn", "dl-excel"),
        _download_row("PDF Report", "A formatted summary report: KPI, map, charts, irrigation calendar, statistics.",
                      "dl-pdf-btn", "dl-pdf"),
        _download_row("PNG Map", "Static image of the selected district with the chosen taluk highlighted.",
                      "dl-mappng-btn", "dl-mappng"),
        _download_row("Graph Images (ZIP)", "PNG images of the weekly, monthly, and trend charts, plus the map.",
                      "dl-images-btn", "dl-images"),
        _download_row("JSON Export", "Full processed data package (daily/weekly/monthly/annual/statistics) as JSON.",
                      "dl-json-btn", "dl-json"),
    ],
    className="download-panel",
)

feedback_tab = html.Div(
    [
        html.P(
            "Spot something missing, unclear, or wrong? Tell us here and we'll use it "
            "to prioritise the next update.",
            className="stats-note",
        ),
        dbc.Button(
            [html.I(className="fa-solid fa-arrow-up-right-from-square me-2"), "Open Feedback Form"],
            href=config.FEEDBACK_FORM_URL, target="_blank",
            color="primary", className="mb-4 mt-2",
        ),
        html.Div(
            [
                html.Div(
                    [html.I(className="fa-solid fa-envelope contact-icon"), html.Span(config.CONTACT_EMAIL)],
                    className="contact-row",
                ),
                html.Div(
                    [html.I(className="fa-solid fa-location-dot contact-icon"), html.Span(config.CONTACT_ADDRESS)],
                    className="contact-row",
                ),
            ],
            className="contact-details",
        ),
    ],
    className="feedback-panel",
)

default_crop_value = cropcal.available_crops()[0]["value"] if cropcal.available_crops() else None

crop_filters_bar = dbc.Card(
    dbc.CardBody(
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("District", className="ctrl-label"),
                        dcc.Dropdown(
                            id="crop-district-dd",
                            options=[{"label": d, "value": d} for d in dl_data.DISTRICTS],
                            value=default_district,
                            clearable=False,
                        ),
                    ],
                    xs=12, sm=6, lg=2,
                    xs=12, sm=6, lg=3,
                ),
                dbc.Col(
                    [
                        dbc.Label("Taluk", className="ctrl-label"),
                        dcc.Dropdown(
                            id="crop-taluk-dd",
                            options=[{"label": t, "value": t} for t in default_taluks],
                            value=default_taluk,
                            clearable=False,
                        ),
                    ],
                    xs=12, sm=6, lg=2,
                    xs=12, sm=6, lg=3,
                ),
                dbc.Col(
                    [
                        dbc.Label("Crop", className="ctrl-label"),
                        dcc.Dropdown(
                            id="crop-select-dd",
                            options=cropcal.available_crops(),
                            value=default_crop_value,
                            clearable=False,
                        ),
                    ],
                    xs=12, sm=6, lg=3,
                ),
                dbc.Col(
                    [
                        dbc.Label("Sowing Week (SMW)", className="ctrl-label"),
                        dcc.Dropdown(
                            id="sowing-smw-dd",
                            options=cropcal.smw_options(),
                            value=39,
                            clearable=False,
                        ),
                    ],
                    xs=12, sm=6, lg=4,
                        dbc.Label("Sowing Date", className="ctrl-label"),
                        dcc.DatePickerSingle(
                            id="sowing-date-picker",
                            min_date_allowed=date(2000, 1, 1),
                            max_date_allowed=date(2035, 12, 31),
                            date=date(2025, 9, 25),
                            display_format="YYYY-MM-DD",
                            className="w-100",
                        ),
                    ],
                    xs=12, sm=6, lg=2,
                ),
                dbc.Col(
                    [
                        html.Div(className="d-none d-lg-block", style={"height": "22px"}),
                        dbc.Button("GO", id="crop-go-btn", color="primary", className="w-100 go-btn"),
                    ],
                    xs=12, sm=12, lg=1,
                ),
            ],
            className="g-3 align-items-end",
        )
    ),
    className="filters-bar-card",
)

crop_kpi_row = dbc.Row(
    [
        _kpi_card("fa-solid fa-calendar-week", "Crop Duration", "crop-kpi-weeks", "#1f4e79", xs=6, lg=3),
        _kpi_card("fa-solid fa-droplet", "Total Crop Water Requirement", "crop-kpi-cwr", "#2e7d32", xs=6, lg=3),
        _kpi_card("fa-solid fa-cloud-rain", "Total Expected Rainfall", "crop-kpi-rain", "#1f77b4", xs=6, lg=3),
        _kpi_card("fa-solid fa-triangle-exclamation", "Net Irrigation Requirement", "crop-kpi-net", "#c0392b",
                  xs=6, lg=3),
    ],
    className="g-3 mb-3",
)

crop_calendar_card = dbc.Card(
    dbc.CardBody(
        [
            html.Div(id="crop-cal-heading", className="irrigation-heading"),
            dash_table.DataTable(
                id="crop-cal-table",
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center", "padding": "6px", "fontSize": "13px", "minWidth": "90px"},
                style_header={"fontWeight": "bold", "backgroundColor": "#f0f2f5"},
                style_header_conditional=[
                    {"if": {"column_id": "Weekly CWR (ETc mm)"}, "backgroundColor": "#dceefb", "color": "#0b5394"},
                    {"if": {"column_id": "Avg Rain (mm)"}, "backgroundColor": "#eaf7e1", "color": "#1e8449"},
                ],
                style_data_conditional=[
                    {
                        "if": {"filter_query": '{Advisory} = "Irrigation Required"', "column_id": "Advisory"},
                        "backgroundColor": "#fdecea", "color": "#c0392b", "fontWeight": "600",
                    },
                    {
                        "if": {"filter_query": '{Advisory} = "No Irrigation Required"', "column_id": "Advisory"},
                        "backgroundColor": "#eafaf1", "color": "#1e8449", "fontWeight": "600",
                    },
                    {
                        "if": {"column_id": "Weekly CWR (ETc mm)"},
                        "backgroundColor": "#eef7fd", "color": "#0b5394", "fontWeight": "600",
                    },
                    {
                        "if": {"column_id": "Avg Rain (mm)"},
                        "backgroundColor": "#f2faed", "color": "#1e8449", "fontWeight": "600",
                    },
                ],
            ),
            html.Br(),
            dbc.Button(
                [html.I(className="fa fa-download me-2"), "Download Crop Calendar"],
                id="crop-dl-btn", color="light", className="dl-btn",
            ),
            dcc.Download(id="crop-dl"),
            html.Hr(),
            html.Div(
                [
                    html.Div("What the terms mean", className="ranking-subtitle"),
                    html.Ul(
                        [
                            html.Li([html.B("Kc (Crop Coefficient): "),
                                      "a number describing how much water the crop uses at its current "
                                      "growth stage, relative to a reference grass surface. It's low at "
                                      "germination and rises as the crop develops more leaf cover."]),
                            html.Li([html.B("ETc / CWR (Crop Water Requirement): "),
                                      "the actual amount of water the crop needs that week, in millimetres "
                                      "(mm). Calculated as ETc = Kc × ET0, where ET0 is the reference "
                                      "(benchmark) evapotranspiration for that week."]),
                            html.Li([html.B("mm (millimetres): "),
                                      "the standard unit for both rainfall and crop water requirement here "
                                      "-- 1 mm of water spread over 1 square metre is 1 litre, so it's "
                                      "directly comparable between what a crop needs and what the rain "
                                      "provides."]),
                        ],
                        className="crop-glossary-list",
                    ),
                ],
                className="crop-glossary",
            ),
            html.P(
                "* Note: This crop irrigation calendar is generated using the last 30 years "
                "(1996-2025) of IMD rainfall data for the selected taluk. Weekly rainfall "
                "figures are climatological averages, not a forecast for any specific year.",
                className="crop-footnote",
            ),
        ]
    ),
    className="chart-card",
)

crop_page_content = html.Div(
    [
        crop_filters_bar,
        html.Div(className="mb-3"),
        crop_kpi_row,
        crop_calendar_card,
    ]
)


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------
home_page_content = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H2("Welcome to the NKAFC Rainfall Dashboard", className="home-title"),
                                html.P(
                                    "The North Karnataka Agrometeorological Forecasting and Research Centre "
                                    "(NKAFC) is a centre of the India Meteorological Department, set up jointly "
                                    "with the University of Agricultural Sciences (UAS), Dharwad, and the "
                                    "Karnataka State Natural Disaster Monitoring Centre. Inaugurated in "
                                    "February 2019, it was the first centre of its kind in India, combining "
                                    "weather observation, forecasting, and agromet research with the aim of "
                                    "getting timely, field-level weather and crop advisories to farmers across "
                                    "North Karnataka.",
                                    className="home-body",
                                ),
                                html.P(
                                    "This dashboard is built on that mission: 30 years (1996-2025) of daily "
                                    "IMD rainfall data across all 112 taluks of North Karnataka, turned into "
                                    "the kind of week-by-week, taluk-level picture a farmer or agromet officer "
                                    "actually needs.",
                                    className="home-body",
                                ),
                                html.Div(
                                    [
                                        dbc.Button(
                                            [html.I(className="fa-solid fa-cloud-rain me-2"), "Open Rainfall Dashboard"],
                                            id="home-goto-rainfall-btn",
                                            color="primary", className="me-3 mt-2",
                                        ),
                                        dbc.Button(
                                            [html.I(className="fa-solid fa-seedling me-2"), "Open Crop Irrigation Calendar"],
                                            id="home-goto-crop-btn",
                                            color="light", className="mt-2 home-secondary-btn",
                                        ),
                                    ]
                                ),
                            ]
                        ),
                        className="home-hero-card",
                    ),
                    lg=8,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Img(src=app.get_asset_url("imd_150years_logo.png"), className="home-150-logo"),
                            ],
                            className="text-center",
                        ),
                        className="home-hero-card",
                    ),
                    lg=4,
                ),
            ],
            className="g-3 mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(_home_feature_card("fa-solid fa-cloud-rain", "Rainfall Dashboard",
                        "District/taluk rainfall, weekly & monthly climatology, trends, statistics, "
                        "advanced charts, and spatial analysis, all in one place — or just tap a taluk "
                        "on the map."), md=6),
                dbc.Col(_home_feature_card("fa-solid fa-seedling", "Crop Irrigation Calendar",
                        "Pick a crop and sowing date and get a week-by-week irrigation advisory, built "
                        "from the crop's actual water requirement compared against 30 years of rainfall."),
                        md=6),
            ],
            className="g-3",
        ),
    ]
)


SECTIONS = [
    ("tab-analytics", "Rainfall Analytics", "fa-solid fa-chart-line", analytics_tab),
    ("tab-statistics", "Statistical Analysis", "fa-solid fa-chart-column", statistics_tab),
    ("tab-advanced", "Advanced Charts", "fa-solid fa-chart-area", advanced_tab),
    ("tab-spatial", "Spatial Analysis", "fa-solid fa-map-location-dot", spatial_tab),
    ("tab-download", "Download Centre", "fa-solid fa-download", download_tab),
]
DEFAULT_SECTION = SECTIONS[0][0]

section_nav = dbc.Nav(
    [
        dbc.NavLink(
            [html.I(className=f"{icon} section-nav-icon"), html.Span(label, className="section-nav-label")],
            id={"type": "section-navlink", "index": tab_id},
            active=(tab_id == DEFAULT_SECTION),
            n_clicks=0,
            className="section-navlink",
        )
        for tab_id, label, icon, _ in SECTIONS
    ],
    vertical=True, pills=True, className="section-nav-list",
)

sections_content = html.Div(
    [
        html.Div(
            comp, id={"type": "section-content", "index": tab_id},
            style={"display": "block" if tab_id == DEFAULT_SECTION else "none"},
        )
        for tab_id, label, icon, comp in SECTIONS
    ],
    className="section-content-area",
)

main_content = html.Div(
    [
        dbc.Row([dbc.Col(quick_map_card, width=12)], className="g-3 mb-3"),
        kpi_row,
        dbc.Row(
            [
                dbc.Col(weekly_card, xs=12, lg=6),
                dbc.Col(monthly_card, xs=12, lg=6),
            ],
            className="g-3 mb-1",
        ),
        dbc.Row(
            [
                dbc.Col(section_nav, width=12, md=3, className="mb-3"),
                dbc.Col(sections_content, width=12, md=9),
            ],
            className="mt-2 g-3",
        ),
    ]
)

rainfall_page_content = html.Div([filters_bar, html.Div(className="mb-3"), main_content])

# ---------------------------------------------------------------------------
# Top-level pages: Home / Rainfall / Crop Irrigation Calendar / Contact Us
# ---------------------------------------------------------------------------
PAGES = [
    ("page-home", "Home", "fa-solid fa-house", home_page_content),
    ("page-rainfall", "Rainfall", "fa-solid fa-cloud-rain", rainfall_page_content),
    ("page-crop", "Crop Irrigation Calendar", "fa-solid fa-seedling", crop_page_content),
    ("page-contact", "Contact Us", "fa-solid fa-comment-dots", feedback_tab),
]
DEFAULT_PAGE = "page-home"

page_nav = dbc.Nav(
    [
        dbc.NavLink(
            [html.I(className=f"{icon} page-nav-icon"), html.Span(label, className="page-nav-label")],
            id={"type": "page-navlink", "index": page_id},
            active=(page_id == DEFAULT_PAGE),
            n_clicks=0,
            className="page-navlink",
        )
        for page_id, label, icon, _ in PAGES
    ],
    pills=True, className="page-nav-list",
)

page_content_area = html.Div(
    [
        html.Div(
            comp, id={"type": "page-content", "index": page_id},
            style={"display": "block" if page_id == DEFAULT_PAGE else "none"},
        )
        for page_id, label, icon, comp in PAGES
    ],
)

navbar = dbc.Navbar(
    dbc.Container(
        [
            html.Img(src=app.get_asset_url("imd_logo.png"), height="72px", className="navbar-imd-logo"),
            html.Div(
                [
                    html.Div(
                        "North Karnataka Agrometeorological Forecasting and Research Centre (NKAFC)",
                        className="navbar-org-title",
                    ),
                    html.Div("India Meteorological Department (IMD), Dharwad", className="navbar-subtitle"),
                ],
                className="navbar-title-block",
            ),
            html.Img(src=app.get_asset_url("imd_150years_logo.png"), height="60px", className="navbar-150-logo"),
        ],
        fluid=True,
        className="py-2 d-flex justify-content-between align-items-center",
    ),
    className="app-navbar mb-0",
)

app.layout = dbc.Container(
    [
        dcc.Store(id="filters-store"),
        dcc.Store(id="active-section", data=DEFAULT_SECTION),
        dcc.Store(id="active-page", data=DEFAULT_PAGE),
        html.Div(id="resize-dummy", style={"display": "none"}),
        html.Div(
            [navbar, html.Div(page_nav, className="page-nav-wrapper mb-3")],
            className="app-header-sticky",
        ),
        page_content_area,
        html.Footer(
            "North Karnataka Agrometeorological Forecasting and Research Centre  |  IMD Rainfall Dashboard",
            className="app-footer",
        ),
    ],
    fluid=True,
    className="app-container",
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
# dash-leaflet maps that sit inside a Bootstrap Tab initialize with a
# zero-size container while that tab is hidden (display:none), so the tiles
# and GeoJSON layer never lay out correctly even after the tab is opened.
# Dispatching a window 'resize' event after the tab switch makes Leaflet
# (which listens for resize by default) recompute its size against the now-
# visible container -- the standard fix for this well-known Dash/Leaflet +
# Bootstrap-tabs interaction.
app.clientside_callback(
    """
    function(active_section, active_page) {
        var triggered = dash_clientside.callback_context.triggered.map(function(t) { return t.prop_id; });
        if (triggered.some(function(p) { return p.indexOf('active-page') === 0; })) {
            window.scrollTo({top: 0, behavior: 'instant'});
        }
        setTimeout(function() {
            window.dispatchEvent(new Event('resize'));
        }, 200);
        setTimeout(function() {
            window.dispatchEvent(new Event('resize'));
        }, 600);
        return '';
    }
    """,
    Output("resize-dummy", "children"),
    Input("active-section", "data"),
    Input("active-page", "data"),
)


@app.callback(
    Output("active-section", "data"),
    Output({"type": "section-navlink", "index": ALL}, "active"),
    Output({"type": "section-content", "index": ALL}, "style"),
    Input({"type": "section-navlink", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def switch_section(_n_clicks_list):
    """Drives the vertical icon nav: whichever NavLink was clicked becomes
    the active section, its content Div is shown, and all the others are
    hidden. Uses pattern-matching IDs so this one callback covers every
    section without a bespoke Output per tab."""
    triggered = ctx.triggered_id
    section_ids = [s[0] for s in SECTIONS]
    active = triggered["index"] if triggered else DEFAULT_SECTION
    if active not in section_ids:
        active = DEFAULT_SECTION
    actives = [tid == active for tid in section_ids]
    styles = [{"display": "block"} if tid == active else {"display": "none"} for tid in section_ids]
    return active, actives, styles


@app.callback(
    Output("active-page", "data"),
    Input({"type": "page-navlink", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def switch_page_from_navbar(_n_clicks_list):
    triggered = ctx.triggered_id
    page_ids = [p[0] for p in PAGES]
    active = triggered["index"] if triggered else DEFAULT_PAGE
    return active if active in page_ids else DEFAULT_PAGE


@app.callback(
    Output("active-page", "data", allow_duplicate=True),
    Input("home-goto-rainfall-btn", "n_clicks"),
    Input("home-goto-crop-btn", "n_clicks"),
    prevent_initial_call=True,
)
def switch_page_from_home_shortcuts(_rainfall_clicks, _crop_clicks):
    if ctx.triggered_id == "home-goto-rainfall-btn":
        return "page-rainfall"
    if ctx.triggered_id == "home-goto-crop-btn":
        return "page-crop"
    raise dash.exceptions.PreventUpdate


@app.callback(
    Output({"type": "page-navlink", "index": ALL}, "active"),
    Output({"type": "page-content", "index": ALL}, "style"),
    Input("active-page", "data"),
)
def apply_active_page(active_page):
    """Applies whatever page is current in the 'active-page' store to the
    nav highlighting and page visibility -- fed by either the top menu bar
    or the Home page's shortcut buttons, so both sources of navigation stay
    in sync through the one store."""
    page_ids = [p[0] for p in PAGES]
    active = active_page if active_page in page_ids else DEFAULT_PAGE
    actives = [pid == active for pid in page_ids]
    styles = [{"display": "block"} if pid == active else {"display": "none"} for pid in page_ids]
    return actives, styles


@app.callback(
    Output("district-dd", "value"),
    Output("taluk-dd", "options"),
    Output("taluk-dd", "value"),
    Input("district-dd", "value"),
    Input("taluk-geojson", "clickData"),
    prevent_initial_call=False,
)
def sync_district_taluk(district_value, click_feature):
    """Keeps the district/taluk dropdowns in sync, whether the change came
    from the dropdowns themselves or from tapping a taluk directly on the
    sidebar map (handy on mobile). All 112 taluks are in that map's GeoJSON
    layer, so any taluk anywhere in the region can be tapped, not just the
    ones in the currently selected district."""
    if ctx.triggered_id == "taluk-geojson" and click_feature:
        props = click_feature.get("properties", {})
        clicked_taluk = props.get("taluk")
        clicked_district = props.get("district")
        if clicked_taluk and clicked_district:
            taluks = dl_data.TALUKS_BY_DISTRICT.get(clicked_district, [])
            return clicked_district, [{"label": t, "value": t} for t in taluks], clicked_taluk

    taluks = dl_data.TALUKS_BY_DISTRICT.get(district_value, [])
    value = taluks[0] if taluks else None
    return district_value, [{"label": t, "value": t} for t in taluks], value


@app.callback(
    Output("filters-store", "data"),
    Input("go-btn", "n_clicks"),
    Input("taluk-geojson", "clickData"),
    State("district-dd", "value"),
    State("taluk-dd", "value"),
    State("date-range", "start_date"),
    State("date-range", "end_date"),
)
def store_filters(n_clicks, click_feature, district, taluk, start_date, end_date):
    # Tapping a taluk on the map applies immediately (no need to press GO) --
    # take the district/taluk straight from the clicked feature so it's not
    # racing the dropdown-sync callback above for the same click event.
    if ctx.triggered_id == "taluk-geojson" and click_feature:
        props = click_feature.get("properties", {})
        district = props.get("district", district)
        taluk = props.get("taluk", taluk)
    return {"district": district, "taluk": taluk, "start_date": start_date, "end_date": end_date}


@app.callback(
    Output("taluk-geojson", "data"),
    Output("taluk-map", "bounds"),
    Output("kpi-annual-avg", "children"),
    Output("weekly-graph", "figure"),
    Output("monthly-graph", "figure"),
    Input("filters-store", "data"),
)
def update_dashboard(store):
    if not store or not store.get("taluk"):
        district, taluk = default_district, default_taluk
        start_date, end_date = config.MIN_DATE, config.MAX_DATE
    else:
        district = store["district"]
        taluk = store["taluk"]
        start_date = store["start_date"]
        end_date = store["end_date"]

    # ---- Map ----
    fc, bounds = map_utils.full_map_geojson(district, taluk)

    # ---- KPI ----
    avg_annual = dl_data.annual_average(taluk, start_date, end_date)
    kpi_text = f"{avg_annual:.1f} mm/year"

    # ---- Weekly chart ----
    wk = dl_data.weekly_climatology(taluk, start_date, end_date)
    weekly_fig = go.Figure()
    weekly_fig.add_trace(go.Scatter(
        x=wk["smw"], y=wk["avg_rain"], mode="lines",
        line=dict(color="#2e7d32", width=2), name="Avg Weekly Rainfall",
    ))
    weekly_fig.update_layout(
        margin=dict(l=40, r=20, t=10, b=40),
        xaxis_title="SMW", yaxis_title="Avg Weekly Rainfall (mm)",
        plot_bgcolor="white", paper_bgcolor="white", height=280,
    )
    weekly_fig.update_xaxes(tickmode="linear", tick0=1, dtick=1, tickfont=dict(size=9), tickangle=0)

    # ---- Monthly chart ----
    mo = dl_data.monthly_climatology(taluk, start_date, end_date)
    month_labels = [f"{m:02d}" for m in mo["month"]]
    monthly_fig = go.Figure()
    monthly_fig.add_trace(go.Bar(
        x=month_labels, y=mo["avg_rain"], marker_color="#7ec8e3", name="Avg Monthly Rainfall",
    ))
    monthly_fig.update_layout(
        margin=dict(l=40, r=20, t=10, b=40),
        xaxis_title="Month", yaxis_title="Avg Monthly Rainfall (mm)",
        plot_bgcolor="white", paper_bgcolor="white", height=260,
    )

    return (fc, bounds, kpi_text, weekly_fig, monthly_fig)


@app.callback(
    Output("trend-note", "children"),
    Output("trend-graph", "figure"),
    Output("cumulative-graph", "figure"),
    Output("anomaly-graph", "figure"),
    Output("spi-graph", "figure"),
    Output("seasonal-graph", "figure"),
    Output("wettest-table", "data"),
    Output("wettest-table", "columns"),
    Output("driest-table", "data"),
    Output("driest-table", "columns"),
    Output("stats-heading", "children"),
    Output("stats-table", "data"),
    Input("filters-store", "data"),
)
def update_analytics(store):
    if not store or not store.get("taluk"):
        district, taluk = default_district, default_taluk
        start_date, end_date = config.MIN_DATE, config.MAX_DATE
    else:
        district = store["district"]
        taluk = store["taluk"]
        start_date = store["start_date"]
        end_date = store["end_date"]

    # ---- Trend + moving average ----
    trend_df = an.rainfall_trend(taluk, start_date, end_date)
    mov_df = an.moving_average(taluk, start_date, end_date)
    slope = trend_df.attrs.get("slope_mm_per_year", 0.0)
    trend_note = (
        f"{taluk}: linear trend of {slope:+.1f} mm/year over the selected period "
        f"({'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'flat'})."
    )
    trend_fig = go.Figure()
    trend_fig.add_trace(go.Bar(x=trend_df["year"], y=trend_df["annual_rainfall"],
                                marker_color="#7ec8e3", name="Annual Rainfall"))
    trend_fig.add_trace(go.Scatter(x=trend_df["year"], y=trend_df["trend"], mode="lines",
                                    line=dict(color="#c0392b", width=2), name="Linear Trend"))
    trend_fig.add_trace(go.Scatter(x=mov_df["year"], y=mov_df["moving_avg"], mode="lines",
                                    line=dict(color="#1f4e79", width=2, dash="dot"),
                                    name="5-Year Moving Avg"))
    trend_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), xaxis_title="Year",
                             yaxis_title="Annual Rainfall (mm)", plot_bgcolor="white",
                             paper_bgcolor="white", height=280, legend=dict(orientation="h", y=-0.25))

    # ---- Cumulative climatology ----
    cum_df = an.cumulative_climatology(taluk, start_date, end_date)
    cum_fig = go.Figure()
    cum_fig.add_trace(go.Scatter(x=cum_df["doy"], y=cum_df["cumulative_rain"], mode="lines",
                                  fill="tozeroy", line=dict(color="#2e7d32", width=2)))
    cum_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), xaxis_title="Day of Year",
                           yaxis_title="Cumulative Rainfall (mm)", plot_bgcolor="white",
                           paper_bgcolor="white", height=260)

    # ---- Anomaly ----
    ano_df = an.rainfall_anomaly(taluk, start_date, end_date)
    ano_colors = ["#c0392b" if v < 0 else "#1f77b4" for v in ano_df["anomaly_pct"]]
    ano_fig = go.Figure()
    ano_fig.add_trace(go.Bar(x=ano_df["year"], y=ano_df["anomaly_pct"], marker_color=ano_colors))
    ano_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), xaxis_title="Year",
                           yaxis_title="Anomaly (%)", plot_bgcolor="white",
                           paper_bgcolor="white", height=260)

    # ---- Standardized rainfall (Z-score) ----
    spi_df = an.standardized_rainfall(taluk, start_date, end_date)
    spi_colors = ["#c0392b" if v < 0 else "#1f77b4" for v in spi_df["z_score"]]
    spi_fig = go.Figure()
    spi_fig.add_trace(go.Bar(x=spi_df["year"], y=spi_df["z_score"], marker_color=spi_colors))
    spi_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), xaxis_title="Year",
                           yaxis_title="Z-score", plot_bgcolor="white",
                           paper_bgcolor="white", height=260)

    # ---- Seasonal rainfall ----
    seas_df = an.seasonal_rainfall(taluk, start_date, end_date)
    seas_fig = go.Figure()
    seas_fig.add_trace(go.Bar(x=seas_df["season"], y=seas_df["avg_rain"], marker_color="#8e6c8a"))
    seas_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), xaxis_title="Season",
                            yaxis_title="Avg Seasonal Rainfall (mm)", plot_bgcolor="white",
                            paper_bgcolor="white", height=260)

    # ---- Wettest / driest taluks ----
    wet = an.wettest_taluks(start_date, end_date, 10).round({"avg_annual_rainfall": 1})
    dry = an.driest_taluks(start_date, end_date, 10).round({"avg_annual_rainfall": 1})
    wet_cols = [{"name": c, "id": c} for c in ["rank", "taluk", "district", "avg_annual_rainfall"]]
    dry_cols = wet_cols

    # ---- Statistics ----
    stats = an.summary_statistics(taluk, start_date, end_date)
    stats_labels = {
        "mean_rainy_day_mm": "Mean (rainy days, mm)",
        "median_rainy_day_mm": "Median (rainy days, mm)",
        "max_daily_mm": "Maximum daily rainfall (mm)",
        "min_nonzero_daily_mm": "Minimum non-zero daily rainfall (mm)",
        "std_rainy_day_mm": "Standard deviation (rainy days, mm)",
        "cv_pct": "Coefficient of variation (%)",
        "p25_mm": "25th percentile (mm)",
        "p50_mm": "50th percentile / median (mm)",
        "p75_mm": "75th percentile (mm)",
        "p90_mm": "90th percentile (mm)",
        "total_rainy_days": "Total rainy days in period",
        "avg_annual_rainy_days": "Average rainy days per year",
        "avg_annual_max_dry_spell_days": "Average annual longest dry spell (days)",
        "overall_max_dry_spell_days": "Longest dry spell in whole period (days)",
    }
    stats_descriptions = {
        "mean_rainy_day_mm": "The average amount of rain that falls on a day when it actually rains (dry days are excluded so they don't drag the average down).",
        "median_rainy_day_mm": "The middle value of daily rainfall on rainy days — half of all rainy days see less than this, half see more. Less skewed by the odd very heavy downpour than the mean.",
        "max_daily_mm": "The single heaviest day of rainfall recorded anywhere in the selected period.",
        "min_nonzero_daily_mm": "The lightest amount of rain recorded on a day that still counted as 'rainy' (>0 mm).",
        "std_rainy_day_mm": "How much daily rainfall amounts vary, day to day, on rainy days. A larger number means rainy days swing between light drizzle and heavy downpours.",
        "cv_pct": "Standard deviation as a percentage of the mean — a scale-free way to compare rainfall variability across taluks or periods regardless of how much rain they get on average.",
        "p25_mm": "25% of rainy days in the period had less rainfall than this amount.",
        "p50_mm": "Same as the median above — the midpoint of rainy-day rainfall amounts.",
        "p75_mm": "75% of rainy days in the period had less rainfall than this amount (i.e. this is a 'moderately heavy' day).",
        "p90_mm": "Only 10% of rainy days exceeded this amount — a rough threshold for an unusually heavy rain day.",
        "total_rainy_days": "The total count of days with any measurable rainfall across the whole selected period.",
        "avg_annual_rainy_days": "The average number of rainy days per year, across the selected years.",
        "avg_annual_max_dry_spell_days": "For each selected year, the longest unbroken run of dry days (<2.5 mm) is found, then those yearly figures are averaged.",
        "overall_max_dry_spell_days": "The single longest unbroken run of dry days anywhere within the whole selected period (not averaged).",
    }
    stats_data = [
        {
            "Statistic": label,
            "Value": (f"{stats[key]:.1f}" if isinstance(stats[key], float) else str(stats[key])),
            "Description": stats_descriptions.get(key, ""),
        }
        for key, label in stats_labels.items()
    ]
    stats_heading = f"District: {district} | Taluk: {taluk} | Period: {start_date} to {end_date}"

    return (
        trend_note, trend_fig, cum_fig, ano_fig, spi_fig, seas_fig,
        wet.to_dict("records"), wet_cols, dry.to_dict("records"), dry_cols,
        stats_heading, stats_data,
    )


@app.callback(
    Output("histogram-graph", "figure"),
    Output("scatter-graph", "figure"),
    Output("boxplot-graph", "figure"),
    Output("violin-graph", "figure"),
    Output("heatmap-graph", "figure"),
    Output("climatology-band-graph", "figure"),
    Output("decadal-graph", "figure"),
    Output("calendar-year-dd", "options"),
    Output("calendar-year-dd", "value"),
    Input("filters-store", "data"),
)
def update_advanced_charts(store):
    if not store or not store.get("taluk"):
        taluk = default_taluk
        start_date, end_date = config.MIN_DATE, config.MAX_DATE
    else:
        taluk = store["taluk"]
        start_date = store["start_date"]
        end_date = store["end_date"]

    # ---- Histogram ----
    hist_vals = ac.histogram_data(taluk, start_date, end_date)
    hist_fig = go.Figure(go.Histogram(x=hist_vals, marker_color="#2e7d32", nbinsx=30))
    hist_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), xaxis_title="Daily Rainfall (mm)",
                            yaxis_title="Count of rainy days", plot_bgcolor="white",
                            paper_bgcolor="white", height=260)

    # ---- Scatter + trend ----
    sc = ac.scatter_rainfall_vs_rainydays(taluk, start_date, end_date)
    scatter_fig = go.Figure()
    scatter_fig.add_trace(go.Scatter(x=sc["rainy_days"], y=sc["annual_rainfall"], mode="markers",
                                      marker=dict(color="#1f4e79", size=9), text=sc["year"],
                                      name="Years"))
    scatter_fig.add_trace(go.Scatter(x=sc["rainy_days"], y=sc["trend"], mode="lines",
                                      line=dict(color="#c0392b", width=2), name="Trend"))
    scatter_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), xaxis_title="Rainy Days / Year",
                               yaxis_title="Annual Rainfall (mm)", plot_bgcolor="white",
                               paper_bgcolor="white", height=260, showlegend=False)

    # ---- Box plot (monthly distribution) ----
    dist = ac.monthly_distribution(taluk, start_date, end_date)
    box_fig = go.Figure()
    for m, name in enumerate(ac.MONTH_NAMES, start=1):
        vals = dist.loc[dist["month"] == m, "monthly_rainfall"]
        box_fig.add_trace(go.Box(y=vals, name=name, marker_color="#7ec8e3", showlegend=False))
    box_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), yaxis_title="Monthly Rainfall (mm)",
                           plot_bgcolor="white", paper_bgcolor="white", height=280)

    # ---- Violin plot (monthly distribution) ----
    violin_fig = go.Figure()
    for m, name in enumerate(ac.MONTH_NAMES, start=1):
        vals = dist.loc[dist["month"] == m, "monthly_rainfall"]
        violin_fig.add_trace(go.Violin(y=vals, name=name, line_color="#8e6c8a",
                                        box_visible=True, meanline_visible=True, showlegend=False))
    violin_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), yaxis_title="Monthly Rainfall (mm)",
                              plot_bgcolor="white", paper_bgcolor="white", height=280)

    # ---- Heatmap (year x month) ----
    mat = ac.heatmap_matrix(taluk, start_date, end_date)
    heatmap_fig = go.Figure(go.Heatmap(
        z=mat.values, x=mat.columns.tolist(), y=[str(y) for y in mat.index.tolist()],
        colorscale="YlGnBu", colorbar=dict(title="mm"),
    ))
    heatmap_fig.update_layout(margin=dict(l=50, r=20, t=10, b=40), height=max(280, 18 * len(mat)),
                               plot_bgcolor="white", paper_bgcolor="white")

    # ---- Monthly climatology band ----
    band = ac.monthly_climatology_band(taluk, start_date, end_date)
    clim_fig = go.Figure()
    clim_fig.add_trace(go.Scatter(x=band["month_name"].tolist() + band["month_name"].tolist()[::-1],
                                   y=band["upper"].tolist() + band["lower"].tolist()[::-1],
                                   fill="toself", fillcolor="rgba(31,78,121,0.15)",
                                   line=dict(color="rgba(255,255,255,0)"), showlegend=False,
                                   hoverinfo="skip"))
    clim_fig.add_trace(go.Scatter(x=band["month_name"], y=band["mean"], mode="lines+markers",
                                   line=dict(color="#1f4e79", width=2), name="Mean"))
    clim_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), yaxis_title="Monthly Rainfall (mm)",
                            plot_bgcolor="white", paper_bgcolor="white", height=260, showlegend=False)

    # ---- Decadal comparison ----
    dec = ac.decadal_comparison(taluk, start_date, end_date)
    decadal_fig = go.Figure()
    for decade in sorted(dec["decade"].unique()):
        sub = dec[dec["decade"] == decade]
        decadal_fig.add_trace(go.Bar(x=sub["month_name"], y=sub["monthly_rainfall"], name=decade))
    decadal_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), yaxis_title="Avg Monthly Rainfall (mm)",
                               plot_bgcolor="white", paper_bgcolor="white", height=280, barmode="group",
                               legend=dict(orientation="h", y=-0.2))

    # ---- Calendar-year dropdown options ----
    years = dl_data.years_in_range(start_date, end_date)
    year_options = [{"label": str(y), "value": y} for y in years]
    year_value = years[-1] if years else config.MAX_YEAR

    return (hist_fig, scatter_fig, box_fig, violin_fig, heatmap_fig, clim_fig, decadal_fig,
            year_options, year_value)


@app.callback(
    Output("calendar-graph", "figure"),
    Input("calendar-year-dd", "value"),
    State("filters-store", "data"),
)
def update_calendar_plot(year, store):
    if year is None:
        year = config.MAX_YEAR
    taluk = store["taluk"] if store and store.get("taluk") else default_taluk

    cal = ac.calendar_year_data(taluk, year)
    if cal.empty:
        fig = go.Figure()
        fig.update_layout(height=200, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    n_weeks = int(cal["week"].max()) + 1
    z = np.full((7, n_weeks), np.nan)
    hover = np.full((7, n_weeks), "", dtype=object)
    for _, row in cal.iterrows():
        z[int(row["dow"]), int(row["week"])] = row["rainfall"]
        hover[int(row["dow"]), int(row["week"])] = f"{row['date'].date()}: {row['rainfall']:.1f} mm"

    cal_fig = go.Figure(go.Heatmap(
        z=z, text=hover, hoverinfo="text", colorscale="YlGnBu",
        y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        colorbar=dict(title="mm"),
    ))
    cal_fig.update_layout(margin=dict(l=50, r=20, t=10, b=20), height=240,
                           plot_bgcolor="white", paper_bgcolor="white",
                           xaxis=dict(showticklabels=False, title="Week of year"))
    return cal_fig


def _continuous_color_map(df: pd.DataFrame, value_col: str, colorscale="YlGnBu"):
    vmin, vmax = df[value_col].min(), df[value_col].max()
    span = (vmax - vmin) or 1.0
    normed = ((df[value_col] - vmin) / span).clip(0, 1)
    colors = sample_colorscale(colorscale, normed.tolist())
    return dict(zip(df["taluk"], colors)), vmin, vmax


@app.callback(
    Output("spatial-map", "invalidateSize"),
    Output("animation-map", "invalidateSize"),
    Input("active-section", "data"),
)
def refresh_spatial_maps_on_tab_open(active_section):
    # Leaflet maps mounted inside a hidden section Div measure their
    # container as 0x0 at creation time and never redraw tiles once the
    # section becomes visible. Sending a fresh value here each time the
    # Spatial Analysis section is opened forces Leaflet to call
    # invalidateSize() and redraw at the correct size. (The sidebar's
    # taluk-map isn't inside a hidden section, so it doesn't need this.)
    if active_section != "tab-spatial":
        return dash.no_update, dash.no_update
    trigger = str(time.time())
    return trigger, trigger


@app.callback(
    Output("spatial-map", "invalidateSize", allow_duplicate=True),
    Output("animation-map", "invalidateSize", allow_duplicate=True),
    Input("spatial-map-mode", "value"),
    prevent_initial_call=True,
)
def refresh_spatial_maps_on_mode_change(mode):
    trigger = str(time.time())
    return trigger, trigger


@app.callback(
    Output("spatial-geojson", "data"),
    Output("spatial-map", "bounds"),
    Output("spatial-legend", "children"),
    Output("district-ranking-graph", "figure"),
    Output("idw-graph", "figure"),
    Output("hotspot-note", "children"),
    Output("hotspot-table", "data"),
    Output("hotspot-table", "columns"),
    Input("filters-store", "data"),
    Input("spatial-map-mode", "value"),
)
def update_spatial(store, mode):
    if not store or not store.get("taluk"):
        start_date, end_date = config.MIN_DATE, config.MAX_DATE
    else:
        start_date, end_date = store["start_date"], store["end_date"]

    # ---- Region map (ranking / zones / hotspot) ----
    if mode == "zones":
        zones = sp.rainfall_zones(start_date, end_date)
        color_map = dict(zip(zones["taluk"], zones["zone_color"]))
        legend_items = [(label, color) for _, _, label, color in sp.RAINFALL_ZONES]
    elif mode == "hotspot":
        hs = sp.hotspot_analysis(start_date, end_date)
        color_map = dict(zip(hs["taluk"], hs["category"].map(sp.HOTSPOT_COLORS)))
        legend_items = list(sp.HOTSPOT_COLORS.items())
    else:  # ranking
        tv = sp.taluk_ranking_map_values(start_date, end_date)
        color_map, vmin, vmax = _continuous_color_map(tv, "annual_rainfall")
        legend_items = None

    fc, bounds = map_utils.region_geojson(color_map)

    if legend_items is not None:
        legend = html.Div(
            [
                html.Span(
                    [html.Span(style={"backgroundColor": c, "display": "inline-block",
                                       "width": "14px", "height": "14px", "marginRight": "4px",
                                       "border": "1px solid #999"}), label],
                    className="legend-chip",
                )
                for label, c in legend_items
            ],
            className="legend-row",
        )
    else:
        legend = html.Div(
            [
                html.Span(f"{vmin:.0f} mm", className="me-2"),
                html.Span(style={
                    "display": "inline-block", "width": "160px", "height": "12px",
                    "background": "linear-gradient(to right, #ffffcc, #253494)",
                    "verticalAlign": "middle", "marginRight": "8px",
                }),
                html.Span(f"{vmax:.0f} mm"),
            ]
        )

    # ---- District ranking ----
    dr = sp.district_ranking(start_date, end_date)
    dr_fig = go.Figure(go.Bar(x=dr["district"], y=dr["avg_annual_rainfall"], marker_color="#1f4e79"))
    dr_fig.update_layout(margin=dict(l=40, r=20, t=10, b=90), yaxis_title="Avg Annual Rainfall (mm)",
                          plot_bgcolor="white", paper_bgcolor="white", height=320)
    dr_fig.update_xaxes(tickangle=-45)

    # ---- IDW interpolation ----
    lon_grid, lat_grid, z, pts = sp.idw_grid(start_date, end_date)
    idw_fig = go.Figure(go.Contour(
        x=lon_grid, y=lat_grid, z=z, colorscale="YlGnBu",
        colorbar=dict(title="mm"), contours=dict(showlines=False),
    ))
    idw_fig.add_trace(go.Scatter(
        x=pts["lon"], y=pts["lat"], mode="markers", marker=dict(size=4, color="black"),
        text=pts["taluk"], hovertemplate="%{text}<extra></extra>", showlegend=False,
    ))
    idw_fig.update_layout(margin=dict(l=40, r=20, t=10, b=40), xaxis_title="Longitude",
                           yaxis_title="Latitude", height=380, plot_bgcolor="white", paper_bgcolor="white")
    idw_fig.update_yaxes(scaleanchor="x", scaleratio=1)

    # ---- Hotspot table ----
    hs_full = sp.hotspot_analysis(start_date, end_date).sort_values("z_score", ascending=False)
    hs_full = hs_full.round({"annual_rainfall": 1, "z_score": 2})
    hs_cols = [{"name": c, "id": c} for c in ["taluk", "district", "annual_rainfall", "z_score", "category"]]
    hotspot_note = (
        "Getis-Ord Gi*-style local statistic: a taluk and its bordering taluks are compared to the "
        "regional mean. Hot Spot = a cluster of unusually high rainfall; Cold Spot = unusually low."
    )

    return fc, bounds, legend, dr_fig, idw_fig, hotspot_note, hs_full.to_dict("records"), hs_cols


@app.callback(
    Output("year-slider", "min"),
    Output("year-slider", "max"),
    Output("year-slider", "value"),
    Output("year-slider", "marks"),
    Input("filters-store", "data"),
)
def init_year_slider(store):
    if not store or not store.get("taluk"):
        start_date, end_date = config.MIN_DATE, config.MAX_DATE
    else:
        start_date, end_date = store["start_date"], store["end_date"]
    years = dl_data.years_in_range(start_date, end_date)
    if not years:
        years = [config.MIN_YEAR]
    marks = {y: str(y) for y in years if y % 5 == 0 or y == years[0] or y == years[-1]}
    return years[0], years[-1], years[0], marks


@app.callback(
    Output("animation-geojson", "data"),
    Output("animation-map", "bounds"),
    Output("anim-year-label", "children"),
    Input("year-slider", "value"),
    State("filters-store", "data"),
)
def update_animation_map(year, store):
    if not store or not store.get("taluk"):
        start_date, end_date = config.MIN_DATE, config.MAX_DATE
    else:
        start_date, end_date = store["start_date"], store["end_date"]
    if year is None:
        year = config.MIN_YEAR

    yv = sp.yearly_taluk_values(start_date, end_date)
    yv_year = yv[yv["year"] == year]
    if yv_year.empty:
        return dash.no_update, dash.no_update, f"Year: {year} (no data)"

    color_map, vmin, vmax = _continuous_color_map(yv_year, "annual_rainfall")
    fc, bounds = map_utils.region_geojson(color_map)
    label = f"Year: {year}  |  region range {vmin:.0f}-{vmax:.0f} mm"
    return fc, bounds, label


@app.callback(
    Output("anim-interval", "disabled"),
    Output("anim-play-btn", "children"),
    Input("anim-play-btn", "n_clicks"),
    State("anim-interval", "disabled"),
    prevent_initial_call=True,
)
def toggle_play(n_clicks, is_disabled):
    now_disabled = not is_disabled
    return now_disabled, ("Play" if now_disabled else "Pause")


@app.callback(
    Output("year-slider", "value", allow_duplicate=True),
    Input("anim-interval", "n_intervals"),
    State("year-slider", "value"),
    State("year-slider", "min"),
    State("year-slider", "max"),
    prevent_initial_call=True,
)
def advance_year(n_intervals, value, ymin, ymax):
    if value is None:
        return ymin
    nxt = value + 1
    return ymin if nxt > ymax else nxt


def _resolve_filters(store):
    """Common default-handling used by every download / export callback."""
    if not store or not store.get("taluk"):
        return default_district, default_taluk, config.MIN_DATE, config.MAX_DATE
    return store["district"], store["taluk"], store["start_date"], store["end_date"]


# ---------------------------------------------------------------------------
# Phase 7 -- Download Centre callbacks
# ---------------------------------------------------------------------------
def _guard_download(fn):
    """Wraps a download callback so a failure prints a full traceback to the
    server console (grep for 'DOWNLOAD FAILED') and just no-ops in the
    browser, instead of showing the person a raw Flask/Werkzeug error page."""
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            print(f"=== DOWNLOAD FAILED in {fn.__name__} ===")
            traceback.print_exc()
            raise dash.exceptions.PreventUpdate
    wrapped.__name__ = fn.__name__
    return wrapped


@app.callback(
    Output("dl-csv", "data"),
    Input("dl-csv-btn", "n_clicks"),
    State("filters-store", "data"),
    prevent_initial_call=True,
)
@_guard_download
def download_csv(n_clicks, store):
    district, taluk, start_date, end_date = _resolve_filters(store)
    daily = dl_data.daily_series(taluk, start_date, end_date)
    fname = f"{taluk}_daily_rainfall_{start_date}_{end_date}.csv"
    return dcc.send_data_frame(daily.to_csv, fname, index=False)


def _build_excel_bytes(taluk, start_date, end_date) -> bytes:
    daily = dl_data.daily_series(taluk, start_date, end_date)
    weekly = dl_data.weekly_by_year_pivot(taluk, start_date, end_date)
    monthly = dl_data.monthly_by_year_pivot(taluk, start_date, end_date)
    annual = dl_data.annual_breakdown_with_average(taluk, start_date, end_date)
    trend = an.rainfall_trend(taluk, start_date, end_date)
    anomaly = an.rainfall_anomaly(taluk, start_date, end_date)
    spi = an.standardized_rainfall(taluk, start_date, end_date)
    seasonal = an.seasonal_rainfall(taluk, start_date, end_date)
    stats = pd.DataFrame(
        [{"statistic": k, "value": v} for k, v in an.summary_statistics(taluk, start_date, end_date).items()]
    )

    # Force plain python dtypes before handing frames to xlsxwriter. Pandas'
    # newer "str" extension dtype (default since pandas 3.0) and pyarrow-
    # backed dtypes aren't always handled the same way by every xlsxwriter
    # version, so normalising here avoids a whole class of "workbook won't
    # open / won't download" issues that only show up with certain
    # pandas/xlsxwriter version pairs.
    #
    # Weekly_SMW / Monthly / Annual are year-by-year breakdowns: one column
    # per selected year (e.g. 2000, 2001, 2002 if that's the sidebar range),
    # plus a final "Average (2000-2002)" column/row -- the same mean-of-
    # yearly-totals figure used everywhere else in the app, just with the
    # individual years shown alongside it instead of only the final result.
    sheets = {
        "Daily": daily,
        "Weekly_SMW": weekly,
        "Monthly": monthly,
        "Annual": annual,
        "Trend": trend[["year", "annual_rainfall", "trend"]],
        "Anomaly": anomaly,
        "Standardized_Rainfall": spi,
        "Seasonal": seasonal,
        "Statistics": stats,
    }
    for name, df in sheets.items():
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == object or str(df[col].dtype) in ("str", "string"):
                df[col] = df[col].astype(str)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
        sheets[name] = df

    buf = io.BytesIO()
    try:
        import xlsxwriter  # noqa: F401  -- just probing availability
        engine = "xlsxwriter"
    except ImportError:
        # Falls back to openpyxl, which this app already requires elsewhere
        # (crop_calendar.py reads xlsx with it), so this path always works
        # even if xlsxwriter specifically wasn't installed -- see the
        # requirements.txt note about exactly this failure mode.
        engine = "openpyxl"
    with pd.ExcelWriter(buf, engine=engine) as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    buf.seek(0)
    return buf.getvalue()


@app.callback(
    Output("dl-excel", "data"),
    Input("dl-excel-btn", "n_clicks"),
    State("filters-store", "data"),
    prevent_initial_call=True,
)
@_guard_download
def download_excel(n_clicks, store):
    district, taluk, start_date, end_date = _resolve_filters(store)
    fname = f"{taluk}_rainfall_{start_date}_{end_date}.xlsx"
    return dcc.send_bytes(_build_excel_bytes(taluk, start_date, end_date), fname)


@app.callback(
    Output("dl-pdf", "data"),
    Input("dl-pdf-btn", "n_clicks"),
    State("filters-store", "data"),
    prevent_initial_call=True,
)
@_guard_download
def download_pdf(n_clicks, store):
    district, taluk, start_date, end_date = _resolve_filters(store)
    pdf_bytes = ex.build_pdf_report(taluk, district, start_date, end_date)
    fname = f"{taluk}_rainfall_report_{start_date}_{end_date}.pdf"
    return dcc.send_bytes(pdf_bytes, fname)


@app.callback(
    Output("dl-mappng", "data"),
    Input("dl-mappng-btn", "n_clicks"),
    State("filters-store", "data"),
    prevent_initial_call=True,
)
@_guard_download
def download_map_png(n_clicks, store):
    district, taluk, start_date, end_date = _resolve_filters(store)
    png_bytes = ex.render_map_png(district, taluk)
    fname = f"{taluk}_map_{district}.png"
    return dcc.send_bytes(png_bytes, fname)


@app.callback(
    Output("dl-images", "data"),
    Input("dl-images-btn", "n_clicks"),
    State("filters-store", "data"),
    prevent_initial_call=True,
)
@_guard_download
def download_images_zip(n_clicks, store):
    district, taluk, start_date, end_date = _resolve_filters(store)
    zip_bytes = ex.build_graph_images_zip(taluk, district, start_date, end_date)
    fname = f"{taluk}_graph_images_{start_date}_{end_date}.zip"
    return dcc.send_bytes(zip_bytes, fname)


@app.callback(
    Output("dl-json", "data"),
    Input("dl-json-btn", "n_clicks"),
    State("filters-store", "data"),
    prevent_initial_call=True,
)
@_guard_download
def download_json(n_clicks, store):
    district, taluk, start_date, end_date = _resolve_filters(store)
    json_bytes = ex.build_json_export(taluk, district, start_date, end_date)
    fname = f"{taluk}_data_export_{start_date}_{end_date}.json"
    return dcc.send_bytes(json_bytes, fname)


# ---------------------------------------------------------------------------
# Crop Irrigation Calendar page
# ---------------------------------------------------------------------------
@app.callback(
    Output("crop-taluk-dd", "options"),
    Output("crop-taluk-dd", "value"),
    Input("crop-district-dd", "value"),
)
def update_crop_taluk_options(district):
    taluks = dl_data.TALUKS_BY_DISTRICT.get(district, [])
    value = taluks[0] if taluks else None
    return [{"label": t, "value": t} for t in taluks], value


CROP_TABLE_COLUMN_MAP = [
    ("crop_week", "Crop Week"),
    ("calendar_smw", "Calendar SMW"),
    ("growth_stage", "Growth Stage"),
    ("kc", "Kc"),
    ("weekly_cwr_mm", "Weekly CWR (ETc mm)"),
    ("cumulative_cwr_mm", "Cumulative CWR (mm)"),
    ("avg_rain_mm", "Avg Rain (mm)"),
    ("min_rain_mm", "Min Rain (mm)"),
    ("max_rain_mm", "Max Rain (mm)"),
    ("deficit_mm", "Deficit (mm)"),
    ("advisory", "Advisory"),
]


def _crop_table_payload(cal: pd.DataFrame):
    renamed = cal.rename(columns=dict(CROP_TABLE_COLUMN_MAP))
    cols = [{"name": disp, "id": disp} for _, disp in CROP_TABLE_COLUMN_MAP]
    return renamed.to_dict("records"), cols


@app.callback(
    Output("crop-kpi-weeks", "children"),
    Output("crop-kpi-cwr", "children"),
    Output("crop-kpi-rain", "children"),
    Output("crop-kpi-net", "children"),
    Output("crop-cal-heading", "children"),
    Output("crop-cal-table", "data"),
    Output("crop-cal-table", "columns"),
    Input("crop-go-btn", "n_clicks"),
    State("crop-district-dd", "value"),
    State("crop-taluk-dd", "value"),
    State("crop-select-dd", "value"),
<<<<<<< HEAD
    State("sowing-smw-dd", "value"),
)
def update_crop_calendar(n_clicks, district, taluk, crop_value, sowing_smw):
    if not crop_value or not taluk or not sowing_smw:
        raise dash.exceptions.PreventUpdate

    cal = cropcal.build_crop_calendar(crop_value, taluk, sowing_smw)
=======
    State("sowing-date-picker", "date"),
)
def update_crop_calendar(n_clicks, district, taluk, crop_value, sowing_date):
    if not crop_value or not taluk or not sowing_date:
        raise dash.exceptions.PreventUpdate

    cal = cropcal.build_crop_calendar(crop_value, taluk, sowing_date)
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
    summary = cropcal.crop_calendar_summary(cal)
    table_data, table_cols = _crop_table_payload(cal)

    crop_label = crop_value
    heading = (
        f"{crop_label}  |  District: {district}  |  Taluk: {taluk}  |  "
<<<<<<< HEAD
        f"Sowing Week: {cal.attrs['sowing_smw_label']}"
=======
        f"Sowing Date: {sowing_date}  (SMW {cal.attrs['sowing_smw']})"
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
    )

    return (
        f"{summary['total_weeks']} weeks",
        f"{summary['total_cwr_mm']:.1f} mm",
        f"{summary['total_expected_rain_mm']:.1f} mm",
        f"{summary['net_irrigation_mm']:.1f} mm",
        heading, table_data, table_cols,
    )


@app.callback(
    Output("crop-dl", "data"),
    Input("crop-dl-btn", "n_clicks"),
    State("crop-district-dd", "value"),
    State("crop-taluk-dd", "value"),
    State("crop-select-dd", "value"),
<<<<<<< HEAD
    State("sowing-smw-dd", "value"),
    prevent_initial_call=True,
)
@_guard_download
def download_crop_calendar(n_clicks, district, taluk, crop_value, sowing_smw):
    if not crop_value or not taluk or not sowing_smw:
        raise dash.exceptions.PreventUpdate
    cal = cropcal.build_crop_calendar(crop_value, taluk, sowing_smw)
    renamed = cal.rename(columns=dict(CROP_TABLE_COLUMN_MAP))
    crop_label = crop_value.replace(" ", "_").replace("/", "-")
    fname = f"{crop_label}_{taluk}_irrigation_calendar_SMW{sowing_smw}.csv"
=======
    State("sowing-date-picker", "date"),
    prevent_initial_call=True,
)
@_guard_download
def download_crop_calendar(n_clicks, district, taluk, crop_value, sowing_date):
    if not crop_value or not taluk or not sowing_date:
        raise dash.exceptions.PreventUpdate
    cal = cropcal.build_crop_calendar(crop_value, taluk, sowing_date)
    renamed = cal.rename(columns=dict(CROP_TABLE_COLUMN_MAP))
    crop_label = crop_value.replace(" ", "_").replace("/", "-")
    fname = f"{crop_label}_{taluk}_irrigation_calendar_{sowing_date}.csv"
>>>>>>> a673546b8c4bf8179612c777b424c9ca88b038af
    return dcc.send_data_frame(renamed.to_csv, fname, index=False)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=8050)
