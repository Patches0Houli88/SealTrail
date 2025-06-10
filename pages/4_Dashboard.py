import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os
from datetime import datetime
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
import yaml

# --- Page Setup ---
st.set_page_config(page_title="Custom Dashboard", layout="wide")
st.title("Equipment Dashboard")

# --- Get User Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"Role: `{user_role}`  \n📧 **Email:** {user_email}")

# --- Validate DB Path ---
db_path = st.session_state.get("db_path", None)
if not db_path or not os.path.exists(db_path):
    st.error("No valid database selected. Please return to the main page.")
    st.stop()

# --- Get Active Table Name ---
active_table = st.session_state.get("active_table", "equipment")
st.sidebar.info(f"Active Table: `{active_table}`")

conn = sqlite3.connect(db_path)

# --- Ensure Support Tables Exist ---
try:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT,
            description TEXT,
            maintenance_date TEXT,
            technician TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
except Exception as e:
    st.warning(f"⚠️ Failed to ensure table `maintenance` exists: {e}")

try:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scanned_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Asset_ID TEXT,
            Equipment_Type TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
except Exception as e:
    st.warning(f"⚠️ Failed to ensure table `scanned_items` exists: {e}")

# --- Load Tables Safely ---
def load_table(name):
    try:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except Exception as e:
        st.warning(f"Could not load table {name}: {e}")
        return pd.DataFrame()

equipment_df = load_table(active_table)
maintenance_df = load_table("maintenance")
scans_df = load_table("scanned_items")

conn.close()

# --- KPI Cards ---
if st.session_state.get("visible_widgets", {}).get("kpis", True):
    st.subheader("Key Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Equipment", len(equipment_df))

    type_col = next((col for col in equipment_df.columns if col.lower() == "type" or col.lower() == "equipment_type"), None)
    if type_col:
        top_types = equipment_df[type_col].dropna().astype(str).value_counts()
        if not top_types.empty:
            col2.metric(f"Top Type: {top_types.index[0]}", top_types.iloc[0])
            if len(top_types) > 1:
                col3.metric(f"2nd Type: {top_types.index[1]}", top_types.iloc[1])
            else:
                col3.write("Only one type found.")
        else:
            col2.write("No type data.")
            col3.write("—")
    else:
        col2.write("No 'type' column.")
        col3.write("—")

# --- Status Chart ---
if st.session_state.get("visible_widgets", {}).get("status_chart", True):
    st.subheader("Equipment Status")
    status_col = next((col for col in equipment_df.columns if col.lower() == "status"), None)
    if status_col:
        status_data = equipment_df[status_col].dropna().astype(str).str.strip().str.title().value_counts().reset_index()
        status_data.columns = ["status", "count"]
        chart = alt.Chart(status_data).mark_bar().encode(
            x="status:N", y="count:Q", color="status:N", tooltip=["status", "count"]
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No 'status' column found.")

# --- Inventory Table ---
if st.session_state.get("visible_widgets", {}).get("inventory_table", True):
    st.subheader("Inventory Table")
    st.dataframe(equipment_df, use_container_width=True)

# --- Maintenance Chart ---
if st.session_state.get("visible_widgets", {}).get("maintenance_chart", True) and not maintenance_df.empty:
    st.subheader("🛠 Maintenance Activity")
    maintenance_date_col = next((col for col in maintenance_df.columns if "date" in col.lower()), None)
    if maintenance_date_col:
        maintenance_df[maintenance_date_col] = pd.to_datetime(maintenance_df[maintenance_date_col], errors="coerce")
        maintenance_df = maintenance_df.dropna(subset=[maintenance_date_col])
        filtered = maintenance_df[(maintenance_df[maintenance_date_col] >= pd.to_datetime(datetime.today().replace(day=1))) & (maintenance_df[maintenance_date_col] <= pd.to_datetime(datetime.today()))]
        if not filtered.empty:
            chart = alt.Chart(filtered).mark_bar().encode(
                x=f"{maintenance_date_col}:T", y="count():Q", tooltip=[maintenance_date_col]
            ).transform_aggregate(count="count()", groupby=[maintenance_date_col])
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No maintenance logs found for selected range.")
    else:
        st.warning("No date column found in maintenance logs.")

# --- Scans Chart ---
if st.session_state.get("visible_widgets", {}).get("scans_chart", True) and not scans_df.empty:
    st.subheader("📷 Barcode Scans Over Time")
    timestamp_col = next((col for col in scans_df.columns if "timestamp" in col.lower()), None)
    if timestamp_col:
        scans_df[timestamp_col] = pd.to_datetime(scans_df[timestamp_col], errors="coerce")
        scans_df = scans_df.dropna(subset=[timestamp_col])
        scans_df["scan_date"] = scans_df[timestamp_col].dt.date
        filtered = scans_df[(scans_df["scan_date"] >= datetime.today().replace(day=1).date()) & (scans_df["scan_date"] <= datetime.today().date())]
        if not filtered.empty:
            scan_data = filtered.groupby("scan_date").size().reset_index(name="scan_count")
            chart = alt.Chart(scan_data).mark_line(point=True).encode(
                x="scan_date:T", y="scan_count:Q", tooltip=["scan_date", "scan_count"]
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No scans found for selected range.")
    else:
        st.warning("No timestamp column found in scanned items.")
