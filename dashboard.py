import streamlit as st
import pandas as pd
from io import BytesIO
import plotly.express as px

from database import get_all_weather, fetch_search_analytics


def show_dashboard():
    st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ─── ROOT VARIABLES ─────────────────────────────────────── */
:root {
    --bg-deep:       #071120;
    --bg-mid:        #0b1f3a;
    --bg-surface:    #102a43;
    --accent-sky:    #38bdf8;
    --accent-blue:   #60a5fa;
    --accent-solid:  #2563eb;
    --text-primary:  #f8fafc;
    --text-secondary:#cbd5e1;
    --text-muted:    #94a3b8;
    --glass-bg:      rgba(255,255,255,0.06);
    --glass-border:  rgba(56,189,248,0.18);
    --shadow-card:   0 8px 32px rgba(0,0,0,0.45);
    --radius-card:   18px;
    --radius-btn:    12px;
}

/* ─── GLOBAL FONT ────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* ─── APP BACKGROUND ─────────────────────────────────────── */
[data-testid="stAppViewContainer"]{
    background: linear-gradient(
        135deg,
        #071120 0%,
        #0b1f3a 45%,
        #102a43 100%
    ) !important;
    background-attachment: fixed;
}

.main{
    background: transparent !important;
}

[data-testid="stAppViewContainer"] > .main{
    background: transparent !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
    backdrop-filter: blur(8px);
}

.main .block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* ─── SIDEBAR ────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1628 0%, #0f172a 100%);
    border-right: 1px solid var(--glass-border);
}

/* ─── HEADINGS ───────────────────────────────────────────── */
h1, h2, h3, h4 {
    color: var(--text-primary) !important;
    letter-spacing: -0.02em;
}

h2, h3 {
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(56,189,248,0.15);
    margin-bottom: 1.2rem !important;
}

/* ─── BODY TEXT ──────────────────────────────────────────── */
p, label, span, div {
    color: var(--text-secondary);
}

/* ─── METRIC CARDS ───────────────────────────────────────── */
[data-testid="metric-container"] {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-card);
    padding: 24px 20px;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: var(--shadow-card), inset 0 1px 0 rgba(255,255,255,0.08);
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    position: relative;
    overflow: hidden;
}

[data-testid="metric-container"]::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent-sky), var(--accent-blue));
    border-radius: var(--radius-card) var(--radius-card) 0 0;
}

[data-testid="metric-container"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 48px rgba(0,0,0,0.55), 0 0 0 1px rgba(56,189,248,0.35);
    border-color: rgba(56,189,248,0.4);
}

[data-testid="stMetricLabel"] > div {
    color: var(--text-muted) !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

[data-testid="stMetricValue"] > div {
    color: var(--text-primary) !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #f8fafc, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ─── DIVIDER ────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid rgba(56,189,248,0.12) !important;
    margin: 2rem 0 !important;
}

/* ─── CHART / GRAPH CONTAINERS ───────────────────────────── */
[data-testid="stArrowVegaLiteChart"],
[data-testid="stPlotlyChart"],
.stLineChart,
.stBarChart,
.element-container:has([data-testid="stArrowVegaLiteChart"]),
.element-container:has([data-testid="stPlotlyChart"]) {
    background: var(--glass-bg);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-card);
    padding: 20px 16px;
    backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: box-shadow 0.25s ease;
}

.element-container:has([data-testid="stArrowVegaLiteChart"]):hover,
.element-container:has([data-testid="stPlotlyChart"]):hover {
    box-shadow: 0 12px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(56,189,248,0.25);
}

/* ─── DATA TABLE ─────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-card) !important;
    padding: 12px !important;
    backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    overflow: hidden;
}

[data-testid="stDataFrame"] table {
    border-collapse: separate !important;
    border-spacing: 0 !important;
}

[data-testid="stDataFrame"] thead th {
    background: rgba(37,99,235,0.25) !important;
    color: var(--accent-sky) !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 1px solid rgba(56,189,248,0.2) !important;
    padding: 12px 14px !important;
}

[data-testid="stDataFrame"] tbody tr {
    transition: background 0.15s ease;
}

[data-testid="stDataFrame"] tbody tr:hover td {
    background: rgba(56,189,248,0.07) !important;
}

[data-testid="stDataFrame"] tbody td {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    border-bottom: 1px solid rgba(255,255,255,0.04) !important;
    padding: 10px 14px !important;
}

/* ─── STANDARD BUTTONS ───────────────────────────────────── */
.stButton > button {
    width: 100%;
    border-radius: var(--radius-btn);
    height: 3em;
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: white;
    border: 1px solid rgba(96,165,250,0.3);
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: 0.03em;
    box-shadow: 0 4px 15px rgba(37,99,235,0.4);
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    box-shadow: 0 6px 20px rgba(37,99,235,0.6);
    transform: translateY(-1px);
    border-color: rgba(96,165,250,0.5);
}

/* ─── DOWNLOAD BUTTONS ───────────────────────────────────── */
.stDownloadButton > button {
    width: 100%;
    border-radius: var(--radius-btn);
    height: 3.2em;
    background: linear-gradient(135deg, #16a34a, #15803d);
    color: white;
    border: 1px solid rgba(74,222,128,0.25);
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: 0.03em;
    box-shadow: 0 4px 15px rgba(22,163,74,0.35);
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.stDownloadButton > button::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.08), transparent);
    pointer-events: none;
}

.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #22c55e, #16a34a);
    box-shadow: 0 6px 22px rgba(22,163,74,0.55);
    transform: translateY(-2px);
    border-color: rgba(74,222,128,0.45);
}

/* ─── SUBHEADER LABEL BADGES ─────────────────────────────── */
[data-testid="stMarkdownContainer"] h3 {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    color: var(--text-primary) !important;
}

/* ─── WARNING / INFO BOXES ───────────────────────────────── */
[data-testid="stAlert"] {
    background: rgba(37,99,235,0.15) !important;
    border: 1px solid rgba(56,189,248,0.3) !important;
    border-radius: 12px !important;
    color: var(--text-secondary) !important;
}

/* ─── SCROLLBAR ──────────────────────────────────────────── */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb {
    background: rgba(56,189,248,0.3);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(56,189,248,0.55);
}

</style>
""", unsafe_allow_html=True)
    st.markdown("""
<div style="text-align:center; padding:10px;">
<h1 style="
color:#e2e8f0;
font-size:48px;
font-weight:800;
text-shadow:0px 2px 15px rgba(0,0,0,0.4);
margin-bottom:0px;">
🌦 Weather Analytics Dashboard
</h1>

<p style="
color:#94a3b8;
font-size:18px;
margin-top:5px;">
Real-Time Weather ETL Pipeline Monitoring & Analytics
</p>
</div>
""", unsafe_allow_html=True)

    df = get_all_weather()

    if df.empty:
        st.warning("No weather data found in database. Search for a city on the Live Weather page to populate data.")
        return

    # =========================
    # METRICS  (unchanged)
    # =========================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📦 Records", len(df))

    with col2:
        st.metric(
            "🌡 Avg Temp (°C)",
            round(df["temperature_c"].mean(), 1)
        )

    with col3:
        st.metric(
            "💧 Avg Humidity",
            f"{round(df['humidity_pct'].mean(), 1)}%"
        )

    with col4:
        st.metric(
            "🧭 Avg Pressure",
            f"{round(df['pressure_hpa'].mean(), 1)} hPa"
        )

    st.divider()

    # =========================
    # NEW: RECENT SEARCHES
    # =========================
    analytics = fetch_search_analytics()

    st.subheader("🕐 Recent Searches")

    recent = analytics["recent_searches"]
    if not recent.empty:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("No searches recorded yet.")

    st.divider()

    # =========================
    # NEW: USER BEHAVIOR ANALYTICS
    # =========================
    st.subheader("📍 Most Searched Cities")

    city_counts = analytics["city_search_counts"]
    top5        = analytics["top5_cities"]

    if not city_counts.empty:
        col_tbl, col_chart = st.columns([1, 2])

        with col_tbl:
            st.dataframe(city_counts, use_container_width=True, hide_index=True)

        with col_chart:
            if not top5.empty:
                fig_top5 = px.bar(
                    top5,
                    x="City",
                    y="Search Count",
                    title="Top 5 Most Searched Cities",
                    color="Search Count",
                    color_continuous_scale="Blues",
                )
                fig_top5.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#cbd5e1",
                    title_font_color="#f8fafc",
                    coloraxis_showscale=False,
                )
                fig_top5.update_traces(marker_line_width=0)
                st.plotly_chart(fig_top5, use_container_width=True)
    else:
        st.info("Search activity will appear here as users search for cities.")

    st.divider()

    # =========================
    # NEW: SEARCH ACTIVITY TREND
    # =========================
    activity = analytics["activity_over_time"]

    if not activity.empty and len(activity) > 1:
        st.subheader("📈 Search Activity Over Time")
        fig_activity = px.line(
            activity,
            x="Hour",
            y="Searches",
            title="Searches per Hour",
            markers=True,
        )
        fig_activity.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            title_font_color="#f8fafc",
        )
        fig_activity.update_traces(
            line_color="#38bdf8",
            marker_color="#60a5fa",
        )
        st.plotly_chart(fig_activity, use_container_width=True)
        st.divider()

    # =========================
    # TEMPERATURE TREND  (unchanged)
    # =========================
    st.subheader("🌡 Temperature Trend")

    chart_df = df.copy()

    if "recorded_at" in chart_df.columns:
        chart_df["recorded_at"] = pd.to_datetime(
            chart_df["recorded_at"],
            errors="coerce"
        )
        chart_df = chart_df.sort_values("recorded_at")
        st.line_chart(
            chart_df.set_index("recorded_at")["temperature_c"]
        )

    st.divider()

    # =========================
    # HUMIDITY TREND  (unchanged)
    # =========================
    st.subheader("💧 Humidity Trend")

    if "recorded_at" in chart_df.columns:
        st.line_chart(
            chart_df.set_index("recorded_at")["humidity_pct"]
        )

    st.divider()

    # =========================
    # CITY TEMPERATURE  (unchanged)
    # =========================
    st.subheader("🏙 City Wise Temperature")

    city_temp = (
        df.groupby("city")["temperature_c"]
        .mean()
        .sort_values(ascending=False)
    )

    st.bar_chart(city_temp)

    st.divider()

    # =========================
    # WEATHER CONDITIONS  (unchanged)
    # =========================
    if "weather_condition" in df.columns:

        st.subheader("🌦 Weather Condition Distribution")

        condition_df = (
            df["weather_condition"]
            .fillna("Unknown")
            .value_counts()
        )

        fig = px.pie(
            names=condition_df.index,
            values=condition_df.values,
            title="Weather Conditions"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # =========================
    # DATA TABLE  (unchanged)
    # =========================
    st.subheader("📋 Recent Weather Records")

    st.dataframe(
        df,
        use_container_width=True
    )

    st.divider()

    # =========================
    # DOWNLOAD SECTION  (unchanged)
    # =========================
    st.subheader("⬇ Download Data")

    csv = df.to_csv(index=False)

    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="weather_data.csv",
        mime="text/csv"
    )

    excel_buffer = BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="WeatherData"
        )

    st.download_button(
        label="Download Excel",
        data=excel_buffer.getvalue(),
        file_name="weather_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
