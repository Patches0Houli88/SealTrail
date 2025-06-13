import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import datetime
import yaml
import shared_utils as su

st.set_page_config(page_title="Equipment Dashboard", layout="wide")
st.title("Dashboard")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = su.get_db_path()
active_table = su.get_active_table()

st.sidebar.markdown(f"Role: {user_role} | 📧 Email: {user_email}")
st.sidebar.info(f"Active Table: `{active_table}`")

# --- Sidebar: Layout Toggles ---
layout_file = f"layout_{user_email.replace('@','_at_')}.yaml"
if os.path.exists(layout_file):
    with open(layout_file) as f:
        st.session_state.visible_widgets = yaml.safe_load(f)
else:
    st.session_state.visible_widgets = {
        "kpis": True,
        "status_chart": True,
        "inventory_table": True,
        "maintenance_chart": user_role == "admin",
        "scans_chart": user_role == "admin"
    }

st.sidebar.subheader("Dashboard Sections")
for key in st.session_state.visible_widgets:
    if user_role == "admin" or key not in ["maintenance_chart", "scans_chart"]:
        st.session_state.visible_widgets[key] = st.sidebar.checkbox(
            key.replace("_", " ").title(), st.session_state.visible_widgets[key]
        )

st.sidebar.subheader("Chart Type")
chart_type = st.sidebar.radio("Select chart type", ["Bar", "Pie"])

st.sidebar.subheader("📅 Date Filter")
start_date = st.sidebar.date_input("Start Date", datetime.today().replace(day=1))
end_date = st.sidebar.date_input("End Date", datetime.today())

if st.sidebar.checkbox("🔄 Auto Refresh"):
    st.rerun()

with open(layout_file, "w") as f:
    yaml.dump(st.session_state.visible_widgets, f)

# --- Load Data centrally ---
equipment_df = su.load_equipment()
maintenance_df = su.load_maintenance()
scans_df = su.load_scans()

# --- Merge Maintenance Info ---
if not maintenance_df.empty:
    id_col = su.get_id_column(equipment_df)
    latest_maintenance = (
        maintenance_df.sort_values("date")
        .dropna(subset=["equipment_id"])
        .drop_duplicates(subset=["equipment_id"], keep="last")[["equipment_id", "date"]]
    )
    equipment_df = equipment_df.merge(
        latest_maintenance, how="left",
        left_on=id_col, right_on="equipment_id"
    )
    equipment_df["maintenance_status"] = equipment_df["date"].apply(
        lambda d: "🟢 Recent" if pd.notna(d) and (datetime.today() - d).days <= 30
        else ("🔴 Old" if pd.notna(d) else "⚪ Never")
    )
else:
    equipment_df["maintenance_status"] = "⚪ Never"

# ✅ Audit this dashboard load
su.log_audit(db_path, user_email, "View Dashboard", f"Loaded dashboard for {active_table}")

# --- KPI ---
if st.session_state.visible_widgets.get("kpis"):
    st.subheader("Key Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Records", len(equipment_df))

    type_col = su.get_type_column(equipment_df)
    if type_col:
        top_types = equipment_df[type_col].astype(str).str.strip().value_counts()
        if not top_types.empty:
            col2.metric("Top Type", top_types.index[0])
            if len(top_types) > 1:
                col3.metric("2nd Type", top_types.index[1])

# --- Status Chart ---
if st.session_state.visible_widgets.get("status_chart"):
    st.subheader("Equipment Status")
    status_col = next((col for col in equipment_df.columns if col.lower() == "status"), None)
    if status_col:
        status_data = equipment_df[status_col].dropna().astype(str).str.title().value_counts().reset_index()
        status_data.columns = ["status", "count"]
        if chart_type == "Bar":
            chart = alt.Chart(status_data).mark_bar().encode(x="status:N", y="count:Q", color="status:N")
        else:
            chart = alt.Chart(status_data).mark_arc().encode(theta="count:Q", color="status:N")
        st.altair_chart(chart, use_container_width=True)

# --- Inventory Table ---
if st.session_state.visible_widgets.get("inventory_table"):
    st.subheader("Current Active Table")
    st.dataframe(equipment_df, use_container_width=True)

# --- Maintenance Chart ---
if st.session_state.visible_widgets.get("maintenance_chart") and not maintenance_df.empty:
    st.subheader("🛠 Maintenance Logs Over Time")
    filtered = maintenance_df[
        (maintenance_df["date"] >= pd.to_datetime(start_date)) &
        (maintenance_df["date"] <= pd.to_datetime(end_date))
    ]
    chart = alt.Chart(filtered).mark_bar().encode(
        x="date:T", y="count():Q"
    ).transform_aggregate(count="count()", groupby=["date"])
    st.altair_chart(chart, use_container_width=True)

# --- Scans Chart ---
if st.session_state.visible_widgets.get("scans_chart") and not scans_df.empty:
    st.subheader("Scans Over Time")
    filtered = scans_df[
        (scans_df["timestamp"].dt.date >= start_date) &
        (scans_df["timestamp"].dt.date <= end_date)
    ]
    scan_data = filtered.groupby("timestamp").size().reset_index(name="count")
    chart = alt.Chart(scan_data).mark_line(point=True).encode(
        x="timestamp:T", y="count:Q"
    )
    st.altair_chart(chart, use_container_width=True)
