import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os
from datetime import datetime
from streamlit_sortable import sortable

# --- Setup ---
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
db_path = st.session_state.get("db_path")
if not db_path or not os.path.exists(db_path):
    st.error("No database selected. Please choose one from the main page.")
    st.stop()

conn = sqlite3.connect(db_path)

def load_table(name):
    try:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except:
        return pd.DataFrame()

equipment_df = load_table("equipment")
maintenance_df = load_table("maintenance")
scans_df = load_table("scanned_items")

conn.close()

# --- User Control ---
with st.expander("🎛️ Build Your Dashboard"):
    selected_widgets = dragzone(
        items=[
            {"id": "status_chart", "content": "📊 Equipment Status Chart"},
            {"id": "inventory_table", "content": "📋 Equipment Table"},
            {"id": "maintenance_chart", "content": "🛠 Maintenance Logs Chart"},
            {"id": "scan_chart", "content": "📷 Barcode Scan Timeline"},
        ],
        drop_style={"background-color": "#f0f2f6", "padding": "1rem"}
    )

st.markdown("---")

# --- Render Widgets ---
for item in selected_widgets:
    if item == "status_chart" and "status" in equipment_df.columns:
        st.subheader("📊 Equipment by Status")
        chart = alt.Chart(equipment_df).mark_bar().encode(
            x=alt.X("status:N", title="Status"),
            y=alt.Y("count():Q", title="Count"),
            color="status:N",
            tooltip=["status", "count()"]
        ).transform_aggregate(
            count='count()',
            groupby=["status"]
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

    elif item == "inventory_table":
        st.subheader("📋 Inventory Data")
        st.dataframe(equipment_df, use_container_width=True)

    elif item == "maintenance_chart" and not maintenance_df.empty:
        st.subheader("🛠 Maintenance Timeline")
        if "maintenance_date" in maintenance_df.columns:
            maintenance_df["maintenance_date"] = pd.to_datetime(maintenance_df["maintenance_date"], errors="coerce")
            line = alt.Chart(maintenance_df).mark_bar().encode(
                x=alt.X("maintenance_date:T", title="Date"),
                y=alt.Y("count():Q", title="Events"),
                tooltip=["maintenance_date", "count()"]
            ).transform_aggregate(
                count='count()',
                groupby=["maintenance_date"]
            )
            st.altair_chart(line, use_container_width=True)

    elif item == "scan_chart" and not scans_df.empty:
        st.subheader("📷 Scans Over Time")
        if "timestamp" in scans_df.columns:
            scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"], errors="coerce")
            scans_df["date"] = scans_df["timestamp"].dt.date
            scan_data = scans_df.groupby("date").size().reset_index(name="scan_count")
            chart = alt.Chart(scan_data).mark_line(point=True).encode(
                x="date:T",
                y="scan_count:Q",
                tooltip=["date", "scan_count"]
            )
            st.altair_chart(chart, use_container_width=True)

st.markdown("---")
st.caption("Drag and reorder widgets above to customize your dashboard.")
