import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os
from datetime import datetime

# --- Connect to DB ---
DB_PATH = st.session_state.get("db_path", None)
if not DB_PATH or not os.path.exists(DB_PATH):
    st.error("No dashboard loaded. Please log in and select a dashboard.")
    st.stop()

conn = sqlite3.connect(DB_PATH)

# --- Load Data ---
equipment_df = pd.read_sql_query("SELECT * FROM equipment", conn)

st.title("📊 Inventory Dashboard")

# --- KPI Cards ---
st.subheader("Overview")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Items", len(equipment_df))
with col2:
    st.metric("Active", (equipment_df.status == "Active").sum())
with col3:
    st.metric("In Repair", (equipment_df.status == "In Repair").sum())

# --- Chart: Equipment by Status ---
st.subheader("Equipment Status Distribution")
status_chart = (
    alt.Chart(equipment_df)
    .mark_bar()
    .encode(
        x=alt.X("status:N", title="Status"),
        y=alt.Y("count():Q", title="Count"),
        color="status:N",
        tooltip=["status:N", "count():Q"]
    )
    .properties(height=300)
)
st.altair_chart(status_chart, use_container_width=True)

# --- Add New Inventory Form ---
st.subheader("➕ Add New Equipment")
with st.form("add_item_form"):
    serial = st.text_input("Serial Number")
    type_ = st.text_input("Type")
    model = st.text_input("Model")
    status = st.selectbox("Status", ["Active", "In Repair", "Retired"])
    purchase_date = st.date_input("Purchase Date")
    warranty_expiry = st.date_input("Warranty Expiry")
    notes = st.text_area("Notes")
    submit = st.form_submit_button("Add Equipment")

    if submit:
        try:
            conn.execute(
                "INSERT INTO equipment (serial_number, type, model, status, purchase_date, warranty_expiry, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (serial, type_, model, status, purchase_date.isoformat(), warranty_expiry.isoformat(), notes)
            )
            conn.commit()
            st.success("Equipment added successfully.")
        except sqlite3.IntegrityError:
            st.error("Serial number already exists.")

# --- Editable Table ---
st.subheader("Edit Inventory Table")
edited_df = st.data_editor(equipment_df, num_rows="dynamic", key="editable_inventory")

if st.button("💾 Save Changes"):
    edited_df.to_sql("equipment", conn, if_exists="replace", index=False)
    st.success("Changes saved to database.")

# --- Maintenance Log View ---
st.subheader("🛠️ Maintenance Logs")
conn.execute("""
CREATE TABLE IF NOT EXISTS maintenance (
    maintenance_id INTEGER PRIMARY KEY,
    equipment_id INTEGER,
    maintenance_type TEXT,
    maintenance_date TEXT,
    performed_by TEXT,
    description TEXT,
    next_scheduled TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
);
""")
conn.commit()

maintenance_df = pd.read_sql_query("SELECT * FROM maintenance", conn)

with st.expander("📋 View Maintenance Records"):
    st.dataframe(maintenance_df)

st.subheader("➕ Log New Maintenance")
with st.form("maintenance_form"):
    eq_id = st.selectbox("Select Equipment ID", equipment_df.equipment_id)
    maint_type = st.selectbox("Maintenance Type", ["Preventive", "Corrective"])
    maint_date = st.date_input("Maintenance Date")
    performed_by = st.text_input("Performed By")
    description = st.text_area("Description")
    next_sched = st.date_input("Next Scheduled")
    submit_maint = st.form_submit_button("Add Maintenance Log")

    if submit_maint:
        conn.execute(
            "INSERT INTO maintenance (equipment_id, maintenance_type, maintenance_date, performed_by, description, next_scheduled) VALUES (?, ?, ?, ?, ?, ?)",
            (eq_id, maint_type, maint_date.isoformat(), performed_by, description, next_sched.isoformat())
        )
        conn.commit()
        st.success("Maintenance log added.")

# --- Barcode Scanner via Camera ---
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
from pyzbar import pyzbar

class BarcodeScanner(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        decoded_objs = pyzbar.decode(img)
        for obj in decoded_objs:
            points = obj.polygon
            pts = np.array([(pt.x, pt.y) for pt in points], np.int32)
            cv2.polylines(img, [pts], isClosed=True, color=(0,255,0), thickness=2)
            barcode_data = obj.data.decode("utf-8")
            cv2.putText(img, barcode_data, (pts[0][0], pts[0][1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
            st.session_state.scanned_barcode = barcode_data
        return img

st.subheader("📷 Scan Barcode (Camera)")
webrtc_streamer(key="barcode_stream", video_processor_factory=BarcodeScanner)

if "scanned_barcode" in st.session_state:
    st.success(f"Scanned Barcode: {st.session_state.scanned_barcode}")
    match = equipment_df[equipment_df.serial_number == st.session_state.scanned_barcode]
    if not match.empty:
        st.write("Item Found:", match)
    else:
        st.warning("Item not found in database. Consider adding it manually.")

conn.close()
