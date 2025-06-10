import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os
from datetime import datetime
import yaml
from fpdf import FPDF
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="Equipment Dashboard", layout="wide")
st.title("📊 Equipment Dashboard")

# --- Get User Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")

# --- Validate DB Path ---
db_path = st.session_state.get("db_path", None)
if not db_path or not os.path.exists(db_path):
    st.error("No valid database selected. Please return to the main page.")
    st.stop()

# --- Active Table ---
active_table = st.session_state.get("active_table", "equipment")
st.sidebar.info(f"📦 Active Table: `{active_table}`")

# --- Sidebar Layout Settings ---
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
        "scans_chart": user_role == "admin",
        "scan_grouping": user_role == "admin"
    }

st.sidebar.subheader("🧩 Dashboard Sections")
for key in st.session_state.visible_widgets:
    if user_role == "admin" or key not in ["maintenance_chart", "scans_chart", "scan_grouping"]:
        st.session_state.visible_widgets[key] = st.sidebar.checkbox(
            key.replace("_", " ").title(), st.session_state.visible_widgets[key]
        )

st.sidebar.subheader("📊 Chart Type")
chart_type = st.sidebar.radio("Select chart type", ["Bar", "Pie"])

st.sidebar.subheader("📅 Date Filter")
start_date = st.sidebar.date_input("Start Date", datetime.today().replace(day=1))
end_date = st.sidebar.date_input("End Date", datetime.today())

if st.sidebar.checkbox("🔄 Auto Refresh"):
    st.rerun()

# Save layout state
with open(layout_file, "w") as f:
    yaml.dump(st.session_state.visible_widgets, f)

# --- Load Tables ---
conn = sqlite3.connect(db_path)
def load_table(name):
    try:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except:
        return pd.DataFrame()

equipment_df = load_table(active_table)
maintenance_df = load_table("maintenance_log")
scans_df = load_table("scanned_items")
conn.close()

# --- KPI Section ---
if st.session_state.visible_widgets.get("kpis"):
    st.subheader("📌 Key Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Records", len(equipment_df))

    # Normalize for equipment_type
    cols_lower = {c.lower(): c for c in equipment_df.columns}
    type_col = cols_lower.get("equipment_type") or cols_lower.get("type")
    if type_col:
        top_types = equipment_df[type_col].astype(str).str.strip().value_counts()
        if not top_types.empty:
            col2.metric("Top Type", top_types.index[0])
            if len(top_types) > 1:
                col3.metric("2nd Type", top_types.index[1])

# --- Equipment Status Chart ---
if st.session_state.visible_widgets.get("status_chart"):
    st.subheader("📦 Equipment Status")
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
    st.subheader("📋 Current Active Table")
    st.dataframe(equipment_df, use_container_width=True)

# --- Maintenance Chart ---
if st.session_state.visible_widgets.get("maintenance_chart") and not maintenance_df.empty:
    st.subheader("🛠 Maintenance Logs Over Time")
    if "date" in maintenance_df.columns:
        maintenance_df["date"] = pd.to_datetime(maintenance_df["date"], errors="coerce")
        filtered = maintenance_df[
            (maintenance_df["date"] >= pd.to_datetime(start_date)) &
            (maintenance_df["date"] <= pd.to_datetime(end_date))
        ]
        chart = alt.Chart(filtered).mark_bar().encode(
            x="date:T", y="count():Q"
        ).transform_aggregate(count="count()", groupby=["date"])
        st.altair_chart(chart, use_container_width=True)

# --- Scans Over Time Chart ---
if st.session_state.visible_widgets.get("scans_chart") and not scans_df.empty:
    st.subheader("📷 Scans Over Time")
    if "timestamp" in scans_df.columns:
        scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"], errors="coerce")
        scans_df["scan_date"] = scans_df["timestamp"].dt.date
        filtered = scans_df[
            (scans_df["scan_date"] >= start_date) & (scans_df["scan_date"] <= end_date)
        ]
        scan_data = filtered.groupby("scan_date").size().reset_index(name="count")
        chart = alt.Chart(scan_data).mark_line(point=True).encode(
            x="scan_date:T", y="count:Q"
        )
        st.altair_chart(chart, use_container_width=True)

# --- Scan Grouping by User or Location ---
if st.session_state.visible_widgets.get("scan_grouping") and not scans_df.empty:
    st.subheader("👤 Scan Activity by User/Location")
    group_by = st.selectbox("Group scans by:", ["scanned_by", "location"])
    if group_by in scans_df.columns:
        group_data = scans_df[group_by].fillna("Unknown").value_counts().reset_index()
        group_data.columns = [group_by, "count"]
        chart = alt.Chart(group_data).mark_bar().encode(
            x=alt.X(group_by, sort='-y'), y="count:Q", color=group_by
        )
        st.altair_chart(chart, use_container_width=True)

# --- Export or Email Logs ---
st.subheader("📤 Export Scan Logs")
if not scans_df.empty:
    export = scans_df.copy()
    csv = export.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "scanned_items.csv", mime="text/csv")

    if user_role == "admin":
        with st.expander("📧 Email Logs"):
            recipient = st.text_input("Recipient Email")
            if st.button("Send Email"):
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "Scan Logs"
                    msg["From"] = "sealtrail@app.com"
                    msg["To"] = recipient
                    msg.set_content("Attached are the scan logs.")
                    msg.add_attachment(csv, filename="scanned_items.csv", maintype="text", subtype="csv")
                    with smtplib.SMTP("localhost") as server:
                        server.send_message(msg)
                    st.success("Email sent.")
                except Exception as e:
                    st.error(f"Failed to send email: {e}")
