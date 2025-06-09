import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
from datetime import datetime
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Full Dashboard", layout="wide")
st.title("📊 Equipment & Inventory Dashboard")

# --- DB Connection ---
db_path = st.session_state.get("db_path")
if not db_path:
    st.error("No database selected. Please return to the main page and select one.")
    st.stop()

conn = sqlite3.connect(db_path)

# --- Load Tables ---
equipment_df, maintenance_df, scan_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

try:
    equipment_df = pd.read_sql("SELECT * FROM equipment", conn)
except:
    st.warning("No equipment data found.")

try:
    maintenance_df = pd.read_sql("SELECT * FROM maintenance_log", conn)
except:
    st.warning("No maintenance logs found.")

try:
    scan_df = pd.read_sql("SELECT * FROM scanned_items", conn)
except:
    st.warning("No scan history found.")

conn.close()

# --- Layout ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Inventory Items", len(equipment_df))
with col2:
    st.metric("Maintenance Logs", len(maintenance_df))
with col3:
    st.metric("Scans Logged", len(scan_df))

# --- Filters ---
st.markdown("---")
st.subheader("Interactive Charts and Reports")

tab1, tab2, tab3 = st.tabs(["Inventory Overview", "Maintenance Timeline", "Scan Activity"])

with tab1:
    if not equipment_df.empty:
        category_col = st.selectbox("Select inventory column to visualize", options=equipment_df.columns)
        category_filter = st.multiselect("Filter by value", options=equipment_df[category_col].unique())
        filtered_df = equipment_df[equipment_df[category_col].isin(category_filter)] if category_filter else equipment_df
        chart = alt.Chart(filtered_df).mark_bar().encode(
            x=alt.X(f"{category_col}:N", sort="-y"),
            y='count()',
            tooltip=[category_col, 'count()']
        ).properties(width=700, height=400)
        st.altair_chart(chart)

with tab2:
    if not maintenance_df.empty:
        maintenance_df['date'] = pd.to_datetime(maintenance_df['date'], errors='coerce')
        start, end = st.date_input("Filter maintenance by date", [], key="maint_range")
        if start and end:
            maintenance_df = maintenance_df[(maintenance_df['date'] >= pd.to_datetime(start)) & (maintenance_df['date'] <= pd.to_datetime(end))]
        chart = alt.Chart(maintenance_df).mark_bar().encode(
            x=alt.X("date:T", title="Maintenance Date"),
            y=alt.Y("count():Q", title="Logs"),
            tooltip=["date", "count()"]
        ).properties(width=700, height=400)
        st.altair_chart(chart)

with tab3:
    if not scan_df.empty:
        scan_df['timestamp'] = pd.to_datetime(scan_df['timestamp'], errors='coerce')
        user_filter = st.multiselect("Filter by user", options=scan_df['scanned_by'].dropna().unique())
        filtered = scan_df[scan_df['scanned_by'].isin(user_filter)] if user_filter else scan_df
        date_start, date_end = st.date_input("Date range for scans", [])
        if date_start and date_end:
            filtered = filtered[(filtered['timestamp'] >= pd.to_datetime(date_start)) & (filtered['timestamp'] <= pd.to_datetime(date_end))]
        scan_counts = filtered.groupby(filtered['timestamp'].dt.date)['code'].count().reset_index(name='count')
        chart = alt.Chart(scan_counts).mark_area().encode(
            x=alt.X("timestamp:T", title="Date"),
            y=alt.Y("count:Q", title="Scans"),
            tooltip=["timestamp", "count"]
        ).properties(width=700, height=400)
        st.altair_chart(chart)

# --- Download Data ---
st.markdown("---")
st.subheader("Export Data")
col1, col2, col3 = st.columns(3)

with col1:
    if not equipment_df.empty:
        st.download_button("Download Equipment CSV", equipment_df.to_csv(index=False).encode(), file_name="equipment.csv")

with col2:
    if not maintenance_df.empty:
        st.download_button("Download Maintenance CSV", maintenance_df.to_csv(index=False).encode(), file_name="maintenance_log.csv")

with col3:
    if not scan_df.empty:
        st.download_button("Download Scan History CSV", scan_df.to_csv(index=False).encode(), file_name="scan_log.csv")

# --- PDF Export ---
if st.button("📄 Generate Summary Report PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Inventory Dashboard Summary", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Inventory Items: {len(equipment_df)}", ln=True)
    pdf.cell(200, 10, txt=f"Maintenance Logs: {len(maintenance_df)}", ln=True)
    pdf.cell(200, 10, txt=f"Scan Records: {len(scan_df)}", ln=True)

    output = BytesIO()
    pdf.output(output)
    st.download_button("Download Summary PDF", output.getvalue(), file_name="dashboard_summary.pdf", mime="application/pdf")
