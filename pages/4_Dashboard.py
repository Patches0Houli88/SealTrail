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

# --- PDF Export Function ---
def export_to_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Equipment Dashboard Report", ln=True, align="C")
    pdf.ln()
    pdf.cell(200, 10, txt="Total Items: {}".format(len(equipment_df)), ln=True)
    if "status" in equipment_df.columns:
        status_counts = equipment_df["status"].fillna("Unspecified").value_counts()
        for status, count in status_counts.items():
            pdf.cell(200, 10, txt=f"{status}: {count}", ln=True)
    pdf.output("dashboard_report.pdf")

    with open("dashboard_report.pdf", "rb") as f:
        st.download_button("📄 Download PDF Report", f, file_name="dashboard_report.pdf")

# --- Email PDF Function ---
def email_pdf():
    if st.button("Email PDF Report"):
        msg = EmailMessage()
        msg["Subject"] = "Your Equipment Dashboard Report"
        msg["From"] = "youremail@example.com"
        msg["To"] = user_email
        msg.set_content("Attached is your latest equipment dashboard report.")

        with open("dashboard_report.pdf", "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename="dashboard_report.pdf")

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login("youremail@example.com", "yourpassword")
                server.send_message(msg)
            st.success("Email sent to " + user_email)
        except Exception as e:
            st.error("Failed to send email: " + str(e))

# --- Load layout YAML ---
layout_file = f"layout_{user_email.replace('@','_at_')}.yaml"
if os.path.exists(layout_file):
    with open(layout_file) as f:
        st.session_state.visible_widgets = yaml.safe_load(f)
else:
    st.session_state.visible_widgets = {
        "status_chart": True,
        "inventory_table": True,
        "maintenance_chart": user_role == "admin",
        "scans_chart": user_role == "admin",
        "kpis": True
    }

# --- Sidebar Toggles ---
st.sidebar.subheader("Dashboard Sections")
for key in st.session_state.visible_widgets:
    if user_role == "admin" or key not in ["maintenance_chart", "scans_chart"]:
        st.session_state.visible_widgets[key] = st.sidebar.checkbox(
            key.replace("_", " ").title(), st.session_state.visible_widgets[key]
        )

# Save layout
with open(layout_file, "w") as f:
    yaml.dump(st.session_state.visible_widgets, f)

# Auto-refresh
if st.sidebar.checkbox("🔄 Auto-refresh"):
    st.experimental_rerun()

# Chart Type
chart_type = st.sidebar.radio("Chart Style", ["Bar", "Pie"])

# Filter Date
st.sidebar.subheader("📅 Filter Date Range")
start_date = st.sidebar.date_input("Start", datetime.today().replace(day=1))
end_date = st.sidebar.date_input("End", datetime.today())

# --- KPI Section ---
if st.session_state.visible_widgets.get("kpis"):
    st.subheader("📌 Key Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Equipment", len(equipment_df))
    if "status" in equipment_df.columns:
        active_count = equipment_df["status"].astype(str).str.lower().eq("active").sum()
        repair_count = equipment_df["status"].astype(str).str.lower().eq("in repair").sum()
        col2.metric("Active", active_count)
        col3.metric("In Repair", repair_count)

# --- Status Chart ---
if st.session_state.visible_widgets.get("status_chart") and "status" in equipment_df.columns:
    st.subheader("Equipment by Status")
    equipment_df["status"] = (
        equipment_df["status"].astype(str).str.strip().str.title().fillna("Unspecified")
    )
    chart_data = equipment_df["status"].value_counts().reset_index()
    chart_data.columns = ["status", "count"]

    if chart_type == "Bar":
        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(x="status:N", y="count:Q", color="status:N", tooltip=["status", "count"])
        )
    else:
        chart = (
            alt.Chart(chart_data)
            .mark_arc()
            .encode(theta="count:Q", color="status:N", tooltip=["status", "count"])
        )

    st.altair_chart(chart, use_container_width=True)

if st.session_state.visible_widgets.get("inventory_table"):
    st.subheader("Inventory Table")
    st.dataframe(equipment_df, use_container_width=True)

if st.session_state.visible_widgets.get("maintenance_chart") and not maintenance_df.empty:
    st.subheader("🛠 Maintenance Timeline")
    if "maintenance_date" in maintenance_df.columns:
        maintenance_df["maintenance_date"] = pd.to_datetime(maintenance_df["maintenance_date"], errors="coerce")
        filtered = maintenance_df[
            (maintenance_df["maintenance_date"] >= pd.to_datetime(start_date)) &
            (maintenance_df["maintenance_date"] <= pd.to_datetime(end_date))
        ]
        chart = alt.Chart(filtered).mark_bar().encode(
            x="maintenance_date:T", y="count():Q", tooltip=["maintenance_date", "count()"]
        ).transform_aggregate(
            count="count()",
            groupby=["maintenance_date"]
        )
        st.altair_chart(chart, use_container_width=True)

if st.session_state.visible_widgets.get("scans_chart") and not scans_df.empty:
    st.subheader("📷 Barcode Scans Timeline")
    if "timestamp" in scans_df.columns:
        scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"], errors="coerce")
        scans_df["date"] = scans_df["timestamp"].dt.date
        filtered = scans_df[
            (scans_df["date"] >= start_date) & (scans_df["date"] <= end_date)
        ]
        scan_data = filtered.groupby("date").size().reset_index(name="scan_count")
        chart = alt.Chart(scan_data).mark_line(point=True).encode(
            x="date:T", y="scan_count:Q", tooltip=["date", "scan_count"]
        )
        st.altair_chart(chart, use_container_width=True)

# --- Export and Email ---
st.markdown("---")
export_to_pdf()
email_pdf()
st.caption("Configure dashboard layout, filter data, and export or email your results.")
