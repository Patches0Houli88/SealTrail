import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Custom Dashboard", layout="wide")
st.title("Equipment Dashboard")

# --- Get user role and email ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")

st.sidebar.markdown(f" Role: {user_role} | Email: {user_email}")

if "user_email" not in st.session_state or "user_role" not in st.session_state:
    st.error("User not recognized. Please go to the main page and log in again.")
    st.stop()


# --- DB Connection ---
DB_PATH = st.session_state.get("db_path")
if not DB_PATH or not os.path.exists(DB_PATH):
    st.error("No dashboard loaded. Please select a database.")
    st.stop()

conn = sqlite3.connect(DB_PATH)

# --- Load Data ---
def load_table(name):
    try:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except:
        return pd.DataFrame()

equipment_df = load_table("equipment")
maintenance_df = load_table("maintenance")
scans_df = load_table("scanned_items")

# --- Sidebar Filters ---
with st.sidebar:
    st.header("📌 Filters")

    if not equipment_df.empty and "status" in equipment_df.columns:
        selected_status = st.multiselect("Filter by Status", equipment_df["status"].dropna().unique())
    else:
        selected_status = []

    date_range = st.date_input("Maintenance Date Range", (datetime.now() - timedelta(days=30), datetime.now()))

# --- Inventory Block ---
st.subheader("📦 Inventory Overview")

if not equipment_df.empty:
    if selected_status:
        filtered_eq = equipment_df[equipment_df["status"].isin(selected_status)]
    else:
        filtered_eq = equipment_df

    col1, col2 = st.columns(2)
    col1.metric("Total Items", len(filtered_eq))
    col2.metric("Unique Types", filtered_eq["type"].nunique() if "type" in filtered_eq.columns else 0)

    st.dataframe(filtered_eq, use_container_width=True)

    if "status" in filtered_eq.columns:
        status_chart = (
            alt.Chart(filtered_eq)
            .mark_bar()
            .encode(
                x=alt.X("status:N", title="Status"),
                y=alt.Y("count():Q", title="Count"),
                color="status:N",
                tooltip=["status:N", "count():Q"]
            )
        )
        st.altair_chart(status_chart, use_container_width=True)
else:
    st.info("No equipment data available.")

# --- Maintenance Block ---
st.subheader("🛠 Maintenance Summary")

if not maintenance_df.empty and "maintenance_date" in maintenance_df.columns:
    maintenance_df["maintenance_date"] = pd.to_datetime(maintenance_df["maintenance_date"], errors="coerce")

    if date_range:
        start, end = date_range
        maintenance_df = maintenance_df[
            (maintenance_df["maintenance_date"] >= pd.to_datetime(start)) &
            (maintenance_df["maintenance_date"] <= pd.to_datetime(end))
        ]

    st.dataframe(maintenance_df, use_container_width=True)

    if "maintenance_type" in maintenance_df.columns:
        maint_chart = (
            alt.Chart(maintenance_df)
            .mark_bar()
            .encode(
                x="maintenance_type:N",
                y="count():Q",
                color="maintenance_type:N",
                tooltip=["maintenance_type", "count()"]
            )
        )
        st.altair_chart(maint_chart, use_container_width=True)
else:
    st.info("No maintenance data found.")

# --- Scans Block ---
st.subheader("📷 Scan Activity")

if not scans_df.empty and "timestamp" in scans_df.columns:
    scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"])
    scans_df["date"] = scans_df["timestamp"].dt.date
    scan_summary = scans_df.groupby("date").size().reset_index(name="scans")

    st.line_chart(scan_summary.set_index("date"))
    st.dataframe(scans_df, use_container_width=True)
else:
    st.info("No scan data available.")

conn.close()
