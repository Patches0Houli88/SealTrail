import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from io import BytesIO
from fpdf import FPDF
import os

st.set_page_config(page_title="Full Dashboard", layout="wide")
st.title("📊 Equipment & Inventory Dashboard")

if "db_path" not in st.session_state:
    st.warning("No database selected. Please select one from the main page.")
    st.stop()

db_path = st.session_state.db_path
conn = sqlite3.connect(db_path)

# --- Load Data ---
def safe_read_sql(query):
    try:
        return pd.read_sql(query, conn)
    except Exception:
        return pd.DataFrame()

equipment_df = safe_read_sql("SELECT * FROM equipment")
maintenance_df = safe_read_sql("SELECT * FROM maintenance_log")
scans_df = safe_read_sql("SELECT * FROM scanned_items")

conn.close()

tab1, tab2, tab3 = st.tabs(["📦 Inventory", "🛠 Maintenance", "📷 Barcode Scans"])

# --- Tab 1: Inventory Overview ---
with tab1:
    st.subheader("Inventory Data")
    if not equipment_df.empty:
        st.dataframe(equipment_df)

        if "status" in equipment_df.columns:
            chart_data = equipment_df["status"].value_counts().reset_index()
            chart_data.columns = ["status", "count"]

            pie_chart = (
                alt.Chart(chart_data)
                .mark_arc()
                .encode(
                    theta="count:Q",
                    color="status:N",
                    tooltip=["status", "count"]
                )
            )
            st.altair_chart(pie_chart, use_container_width=True)
        else:
            st.info("No 'status' column found for pie chart.")
    else:
        st.info("No inventory data to display.")

# --- Tab 2: Maintenance Logs ---
with tab2:
    st.subheader("Maintenance Logs")
    if not maintenance_df.empty:
        st.dataframe(maintenance_df)

        if "date" in maintenance_df.columns:
            maintenance_df["date"] = pd.to_datetime(maintenance_df["date"], errors="coerce")
            default_start = datetime.today() - timedelta(days=30)
            default_end = datetime.today()

            date_range = st.date_input("Filter by date", (default_start, default_end))
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                maintenance_df = maintenance_df[
                    (maintenance_df["date"] >= pd.to_datetime(start)) &
                    (maintenance_df["date"] <= pd.to_datetime(end))
                ]

        if "equipment_id" in maintenance_df.columns:
            bar_chart = (
                alt.Chart(maintenance_df)
                .mark_bar()
                .encode(
                    x="equipment_id:N",
                    y="count():Q",
                    tooltip=["equipment_id", "count()"]
                )
            )
            st.altair_chart(bar_chart, use_container_width=True)
        else:
            st.info("No 'equipment_id' column found for bar chart.")
    else:
        st.info("No maintenance logs available.")

# --- Tab 3: Barcode Scans ---
with tab3:
    st.subheader("Scan History")
    if not scans_df.empty:
        st.dataframe(scans_df)

        if "timestamp" in scans_df.columns:
            scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"], errors="coerce")
            scans_df["date"] = scans_df["timestamp"].dt.date
            chart_data = scans_df.groupby("date").size().reset_index(name="scan_count")

            scan_chart = (
                alt.Chart(chart_data)
                .mark_line(point=True)
                .encode(
                    x="date:T",
                    y="scan_count:Q",
                    tooltip=["date", "scan_count"]
                )
            )
            st.altair_chart(scan_chart, use_container_width=True)
        else:
            st.info("No 'timestamp' column found for time series chart.")
    else:
        st.info("No barcode scan data available.")
