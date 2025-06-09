import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
import os
from datetime import datetime, timedelta
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Full Dashboard", layout="wide")
st.title("📊 Equipment & Inventory Dashboard")

# Role-based logic
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = "guest"
roles_config = {}

if os.path.exists("roles.yaml"):
    import yaml
    with open("roles.yaml") as f:
        roles_config = yaml.safe_load(f)
    user_role = roles_config.get("users", {}).get(user_email, {}).get("role", "guest")

# Global view option (admin only)
use_global = False
if user_role == "admin":
    use_global = st.checkbox("🌐 Global View (All Databases)")

def load_from_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        equipment = pd.read_sql("SELECT * FROM equipment", conn)
        maintenance = pd.read_sql("SELECT * FROM maintenance_log", conn)
        scans = pd.read_sql("SELECT * FROM scanned_items", conn)
        conn.close()
    except:
        equipment = pd.DataFrame()
        maintenance = pd.DataFrame()
        scans = pd.DataFrame()
    return equipment, maintenance, scans

# --- Load Data ---
if use_global:
    root_dir = f"data/"
    all_equipment, all_maintenance, all_scans = [], [], []
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.endswith(".db"):
                eq, mlog, scan = load_from_db(os.path.join(root, f))
                all_equipment.append(eq)
                all_maintenance.append(mlog)
                all_scans.append(scan)
    equipment_df = pd.concat(all_equipment, ignore_index=True) if all_equipment else pd.DataFrame()
    maintenance_df = pd.concat(all_maintenance, ignore_index=True) if all_maintenance else pd.DataFrame()
    scans_df = pd.concat(all_scans, ignore_index=True) if all_scans else pd.DataFrame()
else:
    if "db_path" not in st.session_state:
        st.warning("No database selected. Please select one from the main page.")
        st.stop()
    equipment_df, maintenance_df, scans_df = load_from_db(st.session_state.db_path)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory", "🛠 Maintenance", "📷 Barcode Scans", "🧩 Custom Charts"])

# --- Inventory Tab ---
with tab1:
    st.subheader("Inventory Overview")
    if not equipment_df.empty:
        st.dataframe(equipment_df)

        if "status" in equipment_df.columns:
            chart = (
                alt.Chart(equipment_df)
                .mark_arc()
                .encode(
                    theta=alt.Theta("count()", type="quantitative"),
                    color="status:N",
                    tooltip=["status", "count()"]
                )
                .transform_aggregate(
                    count='count()',
                    groupby=["status"]
                )
            )
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No inventory data.")

# --- Maintenance Tab ---
with tab2:
    st.subheader("Maintenance Logs")
    if not maintenance_df.empty:
        if "date" in maintenance_df.columns:
            maintenance_df["date"] = pd.to_datetime(maintenance_df["date"], errors="coerce")
            start, end = st.date_input(
                "Filter maintenance by date",
                (datetime.today() - timedelta(days=30), datetime.today())
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
        st.info("No maintenance data.")

# --- Barcode Scans ---
with tab3:
    st.subheader("Scan History")
    if not scans_df.empty:
        st.dataframe(scans_df)
        if "timestamp" in scans_df.columns:
            scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"])
            scans_df["date"] = scans_df["timestamp"].dt.date
            daily = scans_df.groupby("date").size().reset_index(name="scan_count")
            chart = (
                alt.Chart(daily)
                .mark_line(point=True)
                .encode(x="date:T", y="scan_count:Q", tooltip=["date", "scan_count"])
            )
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No scans found.")

# --- Chart Builder ---
with tab4:
    st.subheader("Build Custom Chart")

    dataset = st.radio("Choose dataset", ["equipment", "maintenance_log", "scanned_items"])
    data_map = {
        "equipment": equipment_df,
        "maintenance_log": maintenance_df,
        "scanned_items": scans_df
    }

    chart_data = data_map.get(dataset, pd.DataFrame())
    if not chart_data.empty:
        st.dataframe(chart_data)

        chart_type = st.selectbox("Chart Type", ["Bar", "Line", "Area", "Pie"])
        x_axis = st.selectbox("X-axis", chart_data.columns)
        y_axis = st.selectbox("Y-axis", chart_data.columns)

        if chart_type == "Bar":
            chart = alt.Chart(chart_data).mark_bar().encode(x=x_axis, y=y_axis)
        elif chart_type == "Line":
            chart = alt.Chart(chart_data).mark_line().encode(x=x_axis, y=y_axis)
        elif chart_type == "Area":
            chart = alt.Chart(chart_data).mark_area().encode(x=x_axis, y=y_axis)
        elif chart_type == "Pie":
            chart = (
                alt.Chart(chart_data)
                .mark_arc()
                .encode(
                    theta=alt.Theta(y_axis, type="quantitative"),
                    color=x_axis,
                    tooltip=[x_axis, y_axis]
                )
            )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No data to build chart.")
