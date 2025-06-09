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

# --- Validate database path ---
db_path = st.session_state.get("db_path")
if not db_path or not os.path.exists(db_path):
    st.warning("No valid database found. Please return to the main page and select one.")
    st.stop()

st.markdown(f"**Current DB:** `{db_path}`")

# --- Connect and inspect available tables ---
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

# --- Load Data Safely ---
def try_load(table):
    if table in tables:
        try:
            return pd.read_sql(f"SELECT * FROM {table}", conn)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

equipment_df = try_load("equipment")
maintenance_df = try_load("maintenance_log")
scans_df = try_load("scanned_items")

conn.close()

tab1, tab2, tab3 = st.tabs(["📦 Inventory", "🛠 Maintenance", "📷 Barcode Scans"])

# --- Inventory Tab ---
with tab1:
    st.subheader("Inventory Overview")
    if not equipment_df.empty:
        st.dataframe(equipment_df)

        if "status" in equipment_df.columns:
            status_chart = (
                alt.Chart(equipment_df)
                .mark_arc()
                .encode(
                    theta=alt.Theta("count()", type="quantitative"),
                    color=alt.Color("status:N"),
                    tooltip=["status", "count()"],
                )
                .transform_aggregate(count='count()', groupby=["status"])
            )
            st.altair_chart(status_chart, use_container_width=True)
    else:
        st.info("No inventory data found in this database.")

# --- Maintenance Tab ---
with tab2:
    st.subheader("Maintenance Logs")
    if not maintenance_df.empty:
        if "date" in maintenance_df.columns:
            maintenance_df["date"] = pd.to_datetime(maintenance_df["date"], errors="coerce")
            default_start = datetime.today() - timedelta(days=30)
            default_end = datetime.today()

            date_range = st.date_input("Filter maintenance by date", (default_start, default_end))
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
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
        st.info("No maintenance data available.")

# --- Barcode Scans Tab ---
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
