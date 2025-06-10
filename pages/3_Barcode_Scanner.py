import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
from pyzbar import pyzbar

st.set_page_config(page_title="Barcode Scanner", layout="wide")
st.title("📷 Barcode Equipment Scanner")

# --- Session Setup ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = st.session_state.get("db_path", None)

st.sidebar.markdown(f"🔐 Role: `{user_role}`\n📧 Email: {user_email}")

if not db_path or not os.path.exists(db_path):
    st.error("No valid database selected.")
    st.stop()

# --- Table Selection ---
conn = sqlite3.connect(db_path)
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
conn.close()

st.sidebar.subheader("📂 Choose Target Table")
target_table = st.sidebar.selectbox("Scan against table", tables)

# --- Load Template ---
template_file = f"template_{user_email.replace('@', '_at_')}.yaml"
if os.path.exists(template_file):
    template_map = pd.read_yaml(template_file)
else:
    template_map = {}

# --- Scanner Section ---
st.subheader("📥 Scan or Enter Asset ID")

scanner_active = st.checkbox("🟢 Start Scanner", value=False)

# Manual fallback
manual_asset_id = st.text_input("🔤 Or type barcode manually")

# Status Display
if scanner_active:
    st.success("Scanner is ON")
else:
    st.warning("Scanner is OFF")

# --- Live Scanner Capture ---
class BarcodeScanner(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        decoded_objs = pyzbar.decode(img)
        for obj in decoded_objs:
            barcode = obj.data.decode("utf-8")
            st.session_state.barcode_result = barcode
            points = obj.polygon
            pts = np.array([(pt.x, pt.y) for pt in points], np.int32)
            cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
            cv2.putText(img, barcode, (pts[0][0], pts[0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        return img

if scanner_active:
    webrtc_streamer(key="barcode_stream", video_processor_factory=BarcodeScanner)

# --- Barcode Detection Result ---
asset_id = st.session_state.get("barcode_result") or manual_asset_id
if asset_id:
    st.success(f"Scanned Asset ID: {asset_id}")

# --- Load and Map Record ---
record = None
template = template_map.get(asset_id, {})
conn = sqlite3.connect(db_path)
try:
    df = pd.read_sql(f"SELECT * FROM {target_table}", conn)
    if "Asset_ID" in df.columns:
        match = df[df["Asset_ID"].astype(str) == asset_id]
        if not match.empty:
            record = match.iloc[0].to_dict()
except:
    st.warning("Error loading or matching from table.")
conn.close()

# --- Display Editable Record ---
if asset_id:
    st.markdown("### 🔧 Review & Edit Equipment Info")
    with st.form("record_form"):
        conn = sqlite3.connect(db_path)
        columns = pd.read_sql(f"PRAGMA table_info({target_table})", conn)["name"].tolist()
        editable = {}
        for col in columns:
            if col.lower() in ["id", "rowid", "timestamp"]:
                continue
            default_val = record.get(col) if record else template.get(col, "")
            editable[col] = st.text_input(col, value=default_val)

        save_btn = st.form_submit_button("✅ Save to DB")
        conn.close()

    if save_btn:
        conn = sqlite3.connect(db_path)
        try:
            if record:
                update_clause = ", ".join([f"{k}=?" for k in editable])
                conn.execute(f"UPDATE {target_table} SET {update_clause} WHERE Asset_ID = ?",
                             list(editable.values()) + [asset_id])
                st.success("Record updated.")
            else:
                columns = ", ".join(editable.keys())
                placeholders = ", ".join("?" for _ in editable)
                conn.execute(f"INSERT INTO {target_table} ({columns}) VALUES ({placeholders})", list(editable.values()))
                st.success("New record added.")

            # Attach to maintenance log automatically
            conn.execute("""CREATE TABLE IF NOT EXISTS maintenance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id TEXT,
                description TEXT,
                date TEXT,
                technician TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            conn.execute("INSERT INTO maintenance_log (equipment_id, description, date, technician) VALUES (?, ?, ?, ?)",
                         (asset_id, "Scanned entry added or updated", str(datetime.today().date()), user_email))
            conn.commit()
        except Exception as e:
            st.error(f"Error saving: {e}")
        finally:
            conn.close()

# --- Show Scans ---
st.markdown("### 🧾 Latest Scanned Records")
try:
    conn = sqlite3.connect(db_path)
    latest = pd.read_sql(f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT 20", conn)
    st.dataframe(latest)
    conn.close()
except:
    st.info("No data to show.")
