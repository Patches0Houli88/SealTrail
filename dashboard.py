import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os
from datetime import datetime

# --- Page Setup ---
st.set_page_config(page_title="Custom Dashboard", layout="wide")
st.title("Equipment Dashboard")

# --- Get User Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"🔍 Role: {user_role} | **Email:** {user_email}")

# --- Validate DB Path ---
db_path = st.session_state.get("db_path", None)
if not db_path or not os.path.exists(db_path):
    st.error("No valid database selected. Please go to the main page and load a database.")
    st.stop()

conn = sqlite3.connect(db_path)

# --- Load Tables Safely ---
def load_table(name):
    try:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except:
        return pd.DataFrame()

equipment_df = load_table("equipment")
maintenance_df = load_table("maintenance")
scans_df = load_table("scanned_items")

conn.close()

# --- Chart Builder ---
st.sidebar.subheader("🧩 Add Dashboard Widgets")
show_status_chart = st.sidebar.checkbox("Equipment Status", value=True)
show_inventory_table = st.sidebar.checkbox("Equipment Table")
show_maintenance_chart = st.sidebar.checkbox("Maintenance Logs")
show_scans_chart = st.sidebar.checkbox("Barcode Scans")

st.markdown("---")

if show_status_chart and "status" in equipment_df.columns:
    st.subheader("Equipment by Status")
    chart = (
        alt.Chart(equipment_df)
        .mark_bar()
        .encode(
            x=alt.X("status:N", title="Status"),
            y=alt.Y("count():Q", title="Count"),
            color="status:N",
            tooltip=["status", "count()"]
        )
        .transform_aggregate(
            count="count()",
            groupby=["status"]
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)

if show_inventory_table:
    st.subheader("📋 Inventory Data")
    st.dataframe(equipment_df, use_container_width=True)

if show_maintenance_chart and not maintenance_df.empty:
    st.subheader("🛠 Maintenance Timeline")
    if "maintenance_date" in maintenance_df.columns:
        maintenance_df["maintenance_date"] = pd.to_datetime(maintenance_df["maintenance_date"], errors="coerce")
        timeline = (
            alt.Chart(maintenance_df)
            .mark_bar()
            .encode(
                x=alt.X("maintenance_date:T", title="Date"),
                y=alt.Y("count():Q", title="Events"),
                tooltip=["maintenance_date", "count()"]
            )
            .transform_aggregate(
                count="count()",
                groupby=["maintenance_date"]
            )
        )
        st.altair_chart(timeline, use_container_width=True)

if show_scans_chart and not scans_df.empty:
    st.subheader("Barcode Scans Over Time")
    if "timestamp" in scans_df.columns:
        scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"], errors="coerce")
        scans_df["date"] = scans_df["timestamp"].dt.date
        scan_counts = scans_df.groupby("date").size().reset_index(name="scan_count")
        chart = (
            alt.Chart(scan_counts)
            .mark_line(point=True)
            .encode(
                x="date:T",
                y="scan_count:Q",
                tooltip=["date", "scan_count"]
            )
        )
        st.altair_chart(chart, use_container_width=True)

st.markdown("---")
st.caption("Use the sidebar to customize your dashboard layout.")
