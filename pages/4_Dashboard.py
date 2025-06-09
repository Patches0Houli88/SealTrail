import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os
from datetime import datetime
from streamlit_sortable import sortable

st.set_page_config(page_title="Custom Dashboard", layout="wide")
st.title("Equipment Dashboard")

# --- Get user role and email ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")

st.sidebar.markdown(f" Role: {user_role} | Email: {user_email}")

if "user_email" not in st.session_state or "user_role" not in st.session_state:
    st.error("User not recognized. Please go to the main page and log in again.")
    st.stop()

# --- DB Validation ---
DB_PATH = st.session_state.get("db_path")
if not DB_PATH or not os.path.exists(DB_PATH):
    st.error("No database selected. Please select one from the main page.")
    st.stop()

conn = sqlite3.connect(DB_PATH)

# --- Load Tables ---
def try_load(table):
    try:
        return pd.read_sql(f"SELECT * FROM {table}", conn)
    except:
        return pd.DataFrame()

equipment_df = try_load("equipment")
maintenance_df = try_load("maintenance_log")
scan_df = try_load("scanned_items")

# --- User Layout Session ---
if "dashboard_layout" not in st.session_state:
    st.session_state.dashboard_layout = ["KPI", "Status Chart", "Maintenance History", "Scan Trend"]

# --- Sortable Layout ---
blocks = {
    "KPI": lambda: show_kpis(equipment_df),
    "Status Chart": lambda: show_status_chart(equipment_df),
    "Maintenance History": lambda: show_maintenance_timeline(maintenance_df),
    "Scan Trend": lambda: show_scan_trend(scan_df),
}

order = sortable(
    st.session_state.dashboard_layout,
    direction="vertical",
    label="📦 Drag to rearrange dashboard blocks",
    key="dashboard_sort",
    ghost_style={"backgroundColor": "#f0f0f0"},
)

# Render blocks in order
for name in order:
    if name in blocks:
        st.markdown(f"### {name}")
        blocks[name]()
        st.markdown("---")

st.session_state.dashboard_layout = order

# --- Chart Functions ---
def show_kpis(df):
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Items", len(df))
    if "status" in df.columns:
        col2.metric("Active", df[df["status"].str.lower() == "active"].shape[0])
        col3.metric("In Repair", df[df["status"].str.lower() == "in repair"].shape[0])
    else:
        col2.metric("Active", "N/A")
        col3.metric("In Repair", "N/A")

def show_status_chart(df):
    if "status" in df.columns:
        chart_data = df["status"].value_counts().reset_index()
        chart_data.columns = ["status", "count"]
        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(x="status", y="count", color="status", tooltip=["status", "count"])
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("No 'status' column found.")

def show_maintenance_timeline(df):
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        timeline = (
            alt.Chart(df)
            .mark_bar()
            .encode(x="date:T", y="count()", tooltip=["date"])
        )
        st.altair_chart(timeline, use_container_width=True)
    else:
        st.info("No valid maintenance log date found.")

def show_scan_trend(df):
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["date"] = df["timestamp"].dt.date
        trend = df.groupby("date").size().reset_index(name="scans")
        chart = (
            alt.Chart(trend)
            .mark_line(point=True)
            .encode(x="date:T", y="scans:Q", tooltip=["date", "scans"])
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No timestamp data available.")

conn.close()
