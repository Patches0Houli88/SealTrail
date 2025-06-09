import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Full Dashboard", layout="wide")
st.title("📊 Equipment & Inventory Dashboard")

if "db_path" not in st.session_state:
    st.warning("No database selected. Please select one from the main page.")
    st.stop()

conn = sqlite3.connect(st.session_state.db_path)

# --- Load Data ---
try:
    equipment_df = pd.read_sql("SELECT * FROM equipment", conn)
except:
    equipment_df = pd.DataFrame()

try:
    maintenance_df = pd.read_sql("SELECT * FROM maintenance_log", conn)
except:
    maintenance_df = pd.DataFrame()

try:
    scans_df = pd.read_sql("SELECT * FROM scanned_items", conn)
except:
    scans_df = pd.DataFrame()

conn.close()

tab1, tab2, tab3 = st.tabs(["📦 Inventory", "🛠 Maintenance", "📷 Barcode Scans"])

# --- Inventory Tab ---
with tab1:
    st.subheader("Inventory Overview")
    if not equipment_df.empty:
        st.dataframe(equipment_df)

        # Pie Chart by Status
        if "status" in equipment_df.columns:
            status_chart = (
                alt.Chart(equipment_df)
                .mark_arc()
                .encode(
                    theta=alt.Theta(field="count", type="quantitative"),
                    color=alt.Color(field="status", type="nominal"),
                    tooltip=["status", "count"],
                )
                .transform_aggregate(
                    count='count()',
                    groupby=["status"]
                )
            )
            st.altair_chart(status_chart, use_container_width=True)
    else:
        st.info("No inventory data to display.")

# --- Maintenance Tab ---
with tab2:
    st.subheader("Maintenance Logs")
    if not maintenance_df.empty:
        if "date" in maintenance_df.columns:
            maintenance_df["date"] = pd.to_datetime(maintenance_df["date"], errors="coerce")

            default_start = datetime.today() - timedelta(days=30)
            default_end = datetime.today()

            start, end = st.date_input(
                "Filter maintenance by date",
                (default_start, default_end),
                key="maintenance_date_range"
            )

            if start and end:
                maintenance_df = maintenance_df[
                    (maintenance_df["date"] >= pd.to_datetime(start)) &
                    (maintenance_df["date"] <= pd.to_datetime(end))
                ]

        st.dataframe(maintenance_df)

        if "equipment_id" in maintenance_df.columns:
            chart = (
                alt.Chart(maintenance_df)
                .mark_bar()
                .encode(
                    x="equipment_id:N",
                    y="count():Q",
                    tooltip=["equipment_id", "count()"]
                )
            )
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No maintenance logs available.")

# --- Scans Tab ---
with tab3:
    st.subheader("Barcode Scan History")
    if not scans_df.empty:
        st.dataframe(scans_df)

        if "timestamp" in scans_df.columns:
            scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"])
            scans_df["date"] = scans_df["timestamp"].dt.date
            daily_counts = scans_df.groupby("date").size().reset_index(name="scan_count")

            chart = (
                alt.Chart(daily_counts)
                .mark_line(point=True)
                .encode(
                    x="date:T",
                    y="scan_count:Q",
                    tooltip=["date", "scan_count"]
                )
            )
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No barcode scan data found.")
