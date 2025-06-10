import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import av
from pyzbar.pyzbar import decode
import numpy as np
import cv2

st.set_page_config(page_title="Barcode Scanner", layout="wide")
st.title("📷 Scan Equipment (by Asset ID)")

# --- Session & DB Setup ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")

if "db_path" not in st.session_state:
    st.error("No database selected.")
    st.stop()

db_path = st.session_state.db_path

# --- Setup Connection ---
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Ensure template table exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS templates (
    make TEXT,
    model TEXT,
    field_data TEXT
)
""")
conn.commit()

# --- Target Table Selection ---
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
conn.close()
st.sidebar.subheader("📂 Choose Target Table")
target_table = st.sidebar.selectbox("Scan against table", tables)
# --- Live Camera Scanner Toggle ---
st.subheader("📸 Scanner Options")

scanner_enabled = st.checkbox("Start Scanner", value=False)
scan_status = st.empty()

class BarcodeScanner(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        barcodes = decode(img)
        for obj in barcodes:
            barcode = obj.data.decode("utf-8")
            st.session_state.scanned_barcode = barcode
            cv2.putText(img, f"Scanned: {barcode}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return img

if scanner_enabled:
    st.info("Scanner is active. Hold barcode in front of camera.")
    webrtc_streamer(key="scanner", video_processor_factory=BarcodeScanner)
    scan_status.text("🔍 Scanning...")
else:
    scan_status.text("Scanner is disabled.")

# --- Manual Entry Fallback ---
st.subheader("🔢 Enter Barcode Manually")
manual_entry = st.text_input("Asset ID (manual entry)", key="manual_barcode")

# Use scanned OR manual value
asset_id = st.session_state.get("scanned_barcode") or manual_entry
# --- Barcode Input ---
st.subheader("📥 Scan or Enter Asset ID")
asset_id = st.text_input("Asset ID (scanned or typed)", placeholder="e.g. ABC123")

# --- Template Fallback ---
def get_template(make, model):
    with sqlite3.connect(db_path) as conn:
        result = pd.read_sql(
            "SELECT field_data FROM templates WHERE make=? AND model=?",
            conn,
            params=(make, model)
        )
        if not result.empty:
            return eval(result.iloc[0]['field_data'])  # field_data is stored as stringified dict
        return None

# --- Load or Create Record ---
record = None
table_columns = []
template_data = {}
if asset_id and target_table:
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(f"SELECT * FROM {target_table}", conn)
        table_columns = df.columns.tolist()

        if "Asset_ID" in df.columns:
            match = df[df["Asset_ID"].astype(str) == asset_id]
            if not match.empty:
                record = match.iloc[0].to_dict()
            else:
                # Try loading template if available
                if "make" in df.columns and "model" in df.columns:
                    last = df[["make", "model"]].dropna().iloc[-1]
                    template_data = get_template(last['make'], last['model'])

# --- Display Form for Confirmation ---
if asset_id:
    st.markdown("### 🔧 Review & Confirm Record")
    with st.form("confirm_entry"):
        updated_data = {}
        for col in table_columns:
            if col.lower() in ["id", "rowid", "timestamp"]:
                continue
            prefill = record[col] if record else template_data.get(col, "")
            updated_data[col] = st.text_input(col, value=str(prefill))

        auto_maint = st.checkbox("📎 Log maintenance entry", value=not record)
        submitted = st.form_submit_button("✅ Save Entry")

    if submitted:
        with sqlite3.connect(db_path) as conn:
            if record:
                update_stmt = ", ".join([f"{k}=?" for k in updated_data.keys()])
                conn.execute(
                    f"UPDATE {target_table} SET {update_stmt} WHERE Asset_ID = ?",
                    list(updated_data.values()) + [asset_id]
                )
                st.success("✅ Record updated.")
            else:
                keys = ", ".join(updated_data.keys())
                placeholders = ", ".join("?" for _ in updated_data)
                conn.execute(
                    f"INSERT INTO {target_table} ({keys}) VALUES ({placeholders})",
                    list(updated_data.values())
                )
                st.success("✅ New item added.")

            if auto_maint:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS maintenance_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        equipment_id TEXT,
                        description TEXT,
                        date TEXT,
                        technician TEXT,
                        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute(
                    "INSERT INTO maintenance_log (equipment_id, description, date, technician) VALUES (?, ?, ?, ?)",
                    (asset_id, "Scanned and logged via barcode", str(datetime.today().date()), user_email)
                )
            conn.commit()

# --- Recent Scans Display ---
st.markdown("### 🧾 Recent Scans")
try:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql(f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT 20", conn)
    st.dataframe(df)
    conn.close()
except:
    st.warning("No data found yet.")
