import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os
from datetime import datetime

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Equipment Dashboard")

# --- Validate DB Path ---
db_path = st.session_state.get("db_path")
active_table = st.session_state.get("active_table", "equipment")

if not db_path or not os.path.exists(db_path):
    st.error("No valid database selected. Please return to the main page.")
    st.stop()

st.sidebar.info(f"Active Table: `{active_table}`")

# --- Load Tables ---
conn = sqlite3.connect(db_path)
def load(name):
    try:
        df = pd.read_sql(f"SELECT * FROM {name}", conn)
        df.columns = [c.lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

main_df = load(active_table)
maintenance_df = load("maintenance")
scans_df = load("scanned_items")
conn.close()

# Normalize IDs
main_df.rename(columns={"asset_id": "equipment_id"}, inplace=True)

# --- Date Range ---
st.sidebar.subheader("📅 Date Filter")
start_date = st.sidebar.date_input("Start Date", datetime.today().replace(day=1))
end_date = st.sidebar.date_input("End Date", datetime.today())

# --- KPIs ---
st.subheader("📌 KPIs")
col1, col2, col3 = st.columns(3)
col1.metric("Total Items", len(main_df))

type_col = next((c for c in main_df.columns if "type" in c), None)
if type_col:
    counts = main_df[type_col].dropna().astype(str).value_counts()
    if not counts.empty:
        col2.metric("Top Type", counts.index[0])
        col3.metric("2nd Type", counts.index[1] if len(counts) > 1 else "—")
    else:
        col2.write("No type data")
        col3.write("—")
else:
    col2.write("No type column")
    col3.write("—")

# --- Status Chart ---
status_col = next((c for c in main_df.columns if "status" in c), None)
if status_col:
    st.subheader("📦 Status Distribution")
    data = main_df[status_col].dropna().astype(str).str.title().value_counts().reset_index()
    data.columns = ["Status", "Count"]
    st.altair_chart(
        alt.Chart(data).mark_bar().encode(
            x="Status:N", y="Count:Q", color="Status:N", tooltip=["Status", "Count"]
        ),
        use_container_width=True
    )

# --- Maintenance Chart ---
if not maintenance_df.empty:
    st.subheader("🛠 Maintenance Over Time")
    if "maintenance_date" in maintenance_df.columns:
        maintenance_df["maintenance_date"] = pd.to_datetime(maintenance_df["maintenance_date"], errors="coerce")
        filtered = maintenance_df.dropna(subset=["maintenance_date"])
        filtered = filtered[
            (filtered["maintenance_date"] >= pd.to_datetime(start_date)) &
            (filtered["maintenance_date"] <= pd.to_datetime(end_date))
        ]
        if not filtered.empty:
            chart = alt.Chart(filtered).mark_bar().encode(
                x="maintenance_date:T",
                y="count():Q",
                tooltip=["maintenance_date"]
            ).transform_aggregate(
                count="count()", groupby=["maintenance_date"]
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No maintenance in selected range.")

# --- Scans Chart ---
if not scans_df.empty:
    st.subheader("📷 Scans Over Time")
    if "timestamp" in scans_df.columns:
        scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"], errors="coerce")
        scans_df = scans_df.dropna(subset=["timestamp"])
        scans_df["date"] = scans_df["timestamp"].dt.date
        filtered = scans_df[
            (scans_df["date"] >= start_date) & (scans_df["date"] <= end_date)
        ]
        if not filtered.empty:
            chart = alt.Chart(filtered.groupby("date").size().reset_index(name="count")).mark_line(point=True).encode(
                x="date:T", y="count:Q", tooltip=["date", "count"]
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No scans in selected range.")

# --- Show Table Data ---
st.subheader(f"📄 `{active_table}` Table")
st.dataframe(main_df, use_container_width=True)
