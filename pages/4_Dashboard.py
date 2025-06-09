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
st.title("📊 Equipment Dashboard")

# --- User Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"🔍 Role: `{user_role}`  \n📧 **Email:** {user_email}")

# --- Validate DB ---
db_path = st.session_state.get("db_path", None)
if not db_path or not os.path.exists(db_path):
    st.error("No valid database selected. Please return to the main page.")
    st.stop()

conn = sqlite3.connect(db_path)

# --- Load Tables ---
def load_table(name):
    try:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except:
        return pd.DataFrame()

equipment_df = load_table("equipment")
maintenance_df = load_table("maintenance")
scans_df = load_table("scanned_items")
conn.close()

# --- PDF Export ---
def export_to_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Equipment Dashboard Report", ln=True, align="C")
    pdf.ln()
    pdf.cell(200, 10, txt=f"Total Items: {len(equipment_df)}", ln=True)
    if "type" in equipment_df.columns:
        type_counts = equipment_df["type"].fillna("Unspecified").value_counts()
        for t, count in type_counts.items():
            pdf.cell(200, 10, txt=f"{t}: {count}", ln=True)
    if "status" in equipment_df.columns:
        status_counts = equipment_df["status"].fillna("Unspecified").value_counts()
        for s, count in status_counts.items():
            pdf.cell(200, 10, txt=f"{s}: {count}", ln=True)
    pdf.output("dashboard_report.pdf")
    with open("dashboard_report.pdf", "rb") as f:
        st.download_button("📄 Download PDF Report", f, file_name="dashboard_report.pdf")

# --- Email PDF ---
def email_pdf():
    if st.button("📧 Email PDF Report"):
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
            st.success("📤 Email sent to " + user_email)
        except Exception as e:
            st.error(f"❌ Failed to send email: {e}")

# --- Load Layout ---
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

# --- Sidebar Controls ---
st.sidebar.subheader("🧩 Dashboard Sections")
for key in st.session_state.visible_widgets:
    if user_role == "admin" or key not in ["maintenance_chart", "scans_chart"]:
        st.session_state.visible_widgets[key] = st.sidebar.checkbox(
            key.replace("_", " ").title(), st.session_state.visible_widgets[key]
        )
with open(layout_file, "w") as f:
    yaml.dump(st.session_state.visible_widgets, f)

st.sidebar.subheader("📊 Chart Settings")
chart_type = st.sidebar.radio("Chart Type", ["Bar", "Pie"])

st.sidebar.subheader("📅 Date Filter")
start_date = st.sidebar.date_input("Start Date", datetime.today().replace(day=1))
end_date = st.sidebar.date_input("End Date", datetime.today())

if st.sidebar.checkbox("🔄 Auto Refresh"):
    st.rerun()

# --- KPIs ---
if st.session_state.visible_widgets.get("kpis"):
    st.subheader("📌 Key Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Equipment", len(equipment_df))

    if "type" in equipment_df.columns:
        equipment_df["type"] = equipment_df["type"].astype(str).str.strip().fillna("Unspecified")
        type_counts = equipment_df["type"].value_counts()
        if not type_counts.empty:
            col2.metric(f"Top Type: {type_counts.index[0]}", type_counts.iloc[0])
            if len(type_counts) > 1:
                col3.metric(f"2nd Type: {type_counts.index[1]}", type_counts.iloc[1])
            else:
                col3.write("Only one type found.")
        else:
            col2.write("No type data.")
            col3.write("—")
    else:
        col2.write("No 'type' column.")
        col3.write("—")

# --- Status Chart ---
if st.session_state.visible_widgets.get("status_chart") and "status" in equipment_df.columns:
    st.subheader("📊 Equipment Status")
    status_data = equipment_df["status"].astype(str).str.strip().str.title().fillna("Unspecified").value_counts().reset_index()
    status_data.columns = ["status", "count"]
    chart = (
        alt.Chart(status_data)
        .mark_bar() if chart_type == "Bar" else alt.Chart(status_data).mark_arc()
    ).encode(
        x="status:N" if chart_type == "Bar" else alt.Undefined,
        y="count:Q" if chart_type == "Bar" else alt.Undefined,
        theta="count:Q" if chart_type == "Pie" else alt.Undefined,
        color="status:N",
        tooltip=["status", "count"]
    )
    st.altair_chart(chart, use_container_width=True)

# --- Inventory Table ---
if st.session_state.visible_widgets.get("inventory_table"):
    st.subheader("📋 Inventory Table")
    st.dataframe(equipment_df, use_container_width=True)

# --- Maintenance Chart ---
if st.session_state.visible_widgets.get("maintenance_chart") and not maintenance_df.empty:
    st.subheader("🛠 Maintenance Activity")
    if "maintenance_date" in maintenance_df.columns:
        maintenance_df["maintenance_date"] = pd.to_datetime(maintenance_df["maintenance_date"], errors="coerce")
        maintenance_df = maintenance_df.dropna(subset=["maintenance_date"])
        filtered = maintenance_df[
            (maintenance_df["maintenance_date"] >= pd.to_datetime(start_date)) &
            (maintenance_df["maintenance_date"] <= pd.to_datetime(end_date))
        ]
        if not filtered.empty:
            chart = (
                alt.Chart(filtered)
                .mark_bar()
                .encode(x="maintenance_date:T", y="count():Q", tooltip=["maintenance_date"])
                .transform_aggregate(count="count()", groupby=["maintenance_date"])
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No maintenance logs for selected range.")
    else:
        st.warning("Missing 'maintenance_date' column.")

# --- Scans Chart ---
if st.session_state.visible_widgets.get("scans_chart") and not scans_df.empty:
    st.subheader("📷 Barcode Scans Over Time")
    if "timestamp" in scans_df.columns:
        scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"], errors="coerce")
        scans_df = scans_df.dropna(subset=["timestamp"])
        scans_df["date"] = scans_df["timestamp"].dt.date
        filtered = scans_df[
            (scans_df["date"] >= start_date) & (scans_df["date"] <= end_date)
        ]
        if not filtered.empty:
            scan_data = filtered.groupby("date").size().reset_index(name="scan_count")
            chart = alt.Chart(scan_data).mark_line(point=True).encode(
                x="date:T", y="scan_count:Q", tooltip=["date", "scan_count"]
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No scans found in selected date range.")
    else:
        st.warning("Missing 'timestamp' column.")

# --- Export & Email ---
st.markdown("---")
export_to_pdf()
email_pdf()
st.caption("✅ Customize dashboard layout, filter by date, and export/email reports.")
