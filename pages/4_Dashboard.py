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

# --- Connect to DB ---
db_path = st.session_state.get("db_path")
if not db_path or not os.path.exists(db_path):
    st.error("No database loaded. Please go to the main page and select one.")
    st.stop()

conn = sqlite3.connect(db_path)

# --- Load data ---
def load_table(name):
    try:
        return pd.read_sql(f"SELECT * FROM {name}", conn)
    except:
        return pd.DataFrame()

equipment_df = load_table("equipment")
maintenance_df = load_table("maintenance_log")
scan_df = load_table("scanned_items")

conn.close()

# --- Chart Generators ---
def status_chart(df):
    if "status" not in df.columns:
        return "No 'status' column found."
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("status:N", title="Status"),
            y=alt.Y("count():Q", title="Count"),
            color="status:N",
            tooltip=["status:N", "count():Q"]
        )
        .properties(height=300)
    )
    return chart

def type_chart(df):
    if "type" not in df.columns:
        return "No 'type' column found."
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("type:N", title="Equipment Type"),
            y=alt.Y("count():Q", title="Count"),
            color="type:N",
            tooltip=["type:N", "count():Q"]
        )
        .properties(height=300)
    )
    return chart

def purchase_timeline_chart(df):
    if "purchase_date" not in df.columns:
        return "No 'purchase_date' column found."
    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
    counts = df.dropna(subset=["purchase_date"]).groupby(df["purchase_date"].dt.to_period("M")).size().reset_index(name="count")
    counts["purchase_date"] = counts["purchase_date"].astype(str)
    chart = (
        alt.Chart(counts)
        .mark_line(point=True)
        .encode(
            x=alt.X("purchase_date:T", title="Purchase Month"),
            y=alt.Y("count:Q", title="Items Purchased"),
            tooltip=["purchase_date", "count"]
        )
        .properties(height=300)
    )
    return chart

def maintenance_chart(df):
    if "maintenance_type" not in df.columns:
        return "No 'maintenance_type' column found."
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("maintenance_type:N", title="Type"),
            y=alt.Y("count():Q", title="Count"),
            color="maintenance_type:N",
            tooltip=["maintenance_type", "count():Q"]
        )
        .properties(height=300)
    )
    return chart

# --- Layout Definitions ---
chart_blocks = {
    "📊 Equipment Status": lambda: status_chart(equipment_df),
    "🔧 Maintenance Type": lambda: maintenance_chart(maintenance_df),
    "📦 Type Count": lambda: type_chart(equipment_df),
    "📅 Purchase Timeline": lambda: purchase_timeline_chart(equipment_df),
}

st.markdown("🧱 **Drag and drop blocks to build your own dashboard**")

initial_order = list(chart_blocks.keys())
chosen_blocks = sortable(initial_order, direction="vertical", key="dashboard_blocks")

# --- Render Charts ---
for block in chosen_blocks:
    st.markdown(f"#### {block}")
    chart = chart_blocks[block]()
    if isinstance(chart, str):
        st.warning(chart)
    else:
        st.altair_chart(chart, use_container_width=True)
