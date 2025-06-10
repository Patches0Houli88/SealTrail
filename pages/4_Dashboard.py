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
st.sidebar.info(f"📦 Active Table: `{active_table}`")

# --- Ensure Tables Exist ---
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute("""
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
    st.warning(f"Failed to ensure table maintenance exists: {e}")

try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scanned_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Asset_ID TEXT,
            timestamp TEXT,
            scanned_by TEXT
        )
    """)
except Exception as e:
    st.warning(f"Failed to ensure table scanned_items exists: {e}")
conn.commit()

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

# --- Helper for Column Lookup (case-insensitive) ---
def find_column(df, candidates):
    for col in df.columns:
        if col.lower() in [c.lower() for c in candidates]:
            return col
    return None

# --- PDF Export Function ---
def export_to_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Equipment Dashboard Report", ln=True, align="C")
    pdf.ln()
    pdf.cell(200, 10, txt=f"Total Items: {len(equipment_df)}", ln=True)
    
    type_col = find_column(equipment_df, ["type", "equipment_type"])
    if type_col:
        type_counts = equipment_df[type_col].dropna().astype(str).value_counts()
        for t, count in type_counts.items():
            pdf.cell(200, 10, txt=f"{t}: {count}", ln=True)

    status_col = find_column(equipment_df, ["status"])
    if status_col:
        status_counts = equipment_df[status_col].dropna().astype(str).value_counts()
        for s, count in status_counts.items():
            pdf.cell(200, 10, txt=f"{s}: {count}", ln=True)

    pdf.output("dashboard_report.pdf")
    with open("dashboard_report.pdf", "rb") as f:
        st.download_button("📄 Download PDF Report", f, file_name="dashboard_report.pdf")

# --- Email PDF Function ---
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

# --- Layout Memory ---
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

# --- Sidebar Toggles ---
st.sidebar.subheader("🧩 Dashboard Sections")
for key in st.session_state.visible_widgets:
    if user_role == "admin" or key not in ["maintenance_chart", "scans_chart"]:
        st.session_state.visible_widgets[key] = st.sidebar.checkbox(
            key.replace("_", " ").title(), st.session_state.visible_widgets[key]
        )

# Save layout
with open(layout_file, "w") as f:
    yaml.dump(st.session_state.visible_widgets, f)

# Sidebar controls
st.sidebar.subheader("📊 Chart Settings")
chart_type = st.sidebar.radio("Chart Type", ["Bar", "Pie"])

st.sidebar.subheader("📅 Date Filter")
start_date = st.sidebar.date_input("Start Date", datetime.today().replace(day=1))
end_date = st.sidebar.date_input("End Date", datetime.today())

if st.sidebar.checkbox("🔄 Auto Refresh"):
    st.rerun()

# --- KPI Cards ---
if st.session_state.visible_widgets.get("kpis"):
    st.subheader("📌 Key Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Equipment", len(equipment_df))

    type_col = find_column(equipment_df, ["type", "equipment_type"])
    if type_col:
        equipment_df[type_col] = equipment_df[type_col].dropna().astype(str).str.strip()
        type_counts = equipment_df[type_col].value_counts()
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
status_col = find_column(equipment_df, ["status"])
if st.session_state.visible_widgets.get("status_chart") and status_col:
    st.subheader("Equipment Status")
    status_data = equipment_df[status_col].dropna().astype(str).str.strip().str.title().value_counts().reset_index()
    status_data.columns = ["status", "count"]
    if chart_type == "Bar":
        chart = alt.Chart(status_data).mark_bar().encode(
            x="status:N", y="count:Q", color="status:N", tooltip=["status", "count"]
        )
    else:
        chart = alt.Chart(status_data).mark_arc().encode(
            theta="count:Q", color="status:N", tooltip=["status", "count"]
        )
    st.altair_chart(chart, use_container_width=True)

# --- Inventory Table ---
if st.session_state.visible_widgets.get("inventory_table"):
    st.subheader("Inventory Table")
    st.dataframe(equipment_df, use_container_width=True)

# --- Maintenance Chart ---
maint_date_col = find_column(maintenance_df, ["maintenance_date"])
if st.session_state.visible_widgets.get("maintenance_chart") and not maintenance_df.empty and maint_date_col:
    st.subheader("🛠 Maintenance Activity")
    maintenance_df[maint_date_col] = pd.to_datetime(maintenance_df[maint_date_col], errors="coerce")
    maintenance_df = maintenance_df.dropna(subset=[maint_date_col])
    filtered = maintenance_df[
        (maintenance_df[maint_date_col] >= pd.to_datetime(start_date)) &
        (maintenance_df[maint_date_col] <= pd.to_datetime(end_date))
    ]
    if not filtered.empty:
        chart = alt.Chart(filtered).mark_bar().encode(
            x=f"{maint_date_col}:T", y="count():Q", tooltip=[maint_date_col]
        ).transform_aggregate(
            count="count()", groupby=[maint_date_col]
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No maintenance logs found for selected range.")

# --- Scans Chart ---
timestamp_col = find_column(scans_df, ["timestamp"])
if st.session_state.visible_widgets.get("scans_chart") and not scans_df.empty and timestamp_col:
    st.subheader("📷 Barcode Scans Over Time")
    scans_df[timestamp_col] = pd.to_datetime(scans_df[timestamp_col], errors="coerce")
    scans_df = scans_df.dropna(subset=[timestamp_col])
    scans_df["date"] = scans_df[timestamp_col].dt.date
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
        st.info("No scans found for selected range.")

# --- Export & Email Report ---
st.markdown("---")
export_to_pdf()
email_pdf()
st.caption("Customize dashboard layout, filter by date, and export or email your results.")
