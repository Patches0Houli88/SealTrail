import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from datetime import datetime
import io
import os

st.set_page_config(page_title="Barcode Scanner", layout="wide")
st.title("📷 Scan & Track Equipment")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = st.session_state.get("db_path")
st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")

if not db_path or not os.path.exists(db_path):
    st.error("No database loaded. Please return to the main page.")
    st.stop()

# --- Table Selection ---
conn = sqlite3.connect(db_path)
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
conn.close()

st.sidebar.subheader("📂 Target Table")
target_table = st.sidebar.selectbox("Scan or add entries to this table", tables)

# --- Ensure scanned_items table exists ---
conn = sqlite3.connect(db_path)
conn.execute("""
    CREATE TABLE IF NOT EXISTS scanned_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id TEXT,
        timestamp TEXT,
        scanned_by TEXT
    )
""")
conn.commit()
conn.close()

# --- Scanner UI ---
st.markdown("### 🔍 Scanner Status")
camera_active = st.checkbox("🟢 Start Scanner")
st.info("📸 Scanner is **active**." if camera_active else "⛔ Scanner is **inactive**.")

# --- Asset ID Input ---
st.markdown("### 🏷️ Scan or Enter Equipment ID")
equipment_id = st.text_input("Equipment ID (barcode or manual entry)", placeholder="e.g., EQP-001").strip()

# --- Load Record if Exists ---
record = None
table_columns = []
matching_col = None
if equipment_id and target_table:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql(f"SELECT * FROM {target_table}", conn)
        table_columns = df.columns.tolist()
        matching_col = next((col for col in df.columns if col.lower() in ["asset_id", "equipment_id"]), None)
        if matching_col:
            record_df = df[df[matching_col].astype(str).str.lower() == equipment_id.lower()]
            if not record_df.empty:
                record = record_df.iloc[0].to_dict()
    except Exception as e:
        st.error(f"Error loading table: {e}")
    finally:
        conn.close()

# --- QR Code Preview ---
if equipment_id:
    qr = qrcode.make(equipment_id)
    buf = io.BytesIO()
    qr.save(buf)
    st.image(buf.getvalue(), caption="QR Code", width=150)

# --- QR Batch Mode ---
with st.expander("📦 Generate QR Batch"):
    prefix = st.text_input("Prefix", value="EQP")
    start = st.number_input("Start Number", min_value=1, value=1)
    count = st.number_input("How many?", min_value=1, value=5)
    if st.button("Generate Batch QR Codes"):
        qr_zip = io.BytesIO()
        from zipfile import ZipFile
        with ZipFile(qr_zip, 'w') as zf:
            for i in range(start, start + count):
                id_code = f"{prefix}-{str(i).zfill(3)}"
                qr_img = qrcode.make(id_code)
                img_buf = io.BytesIO()
                qr_img.save(img_buf, format="PNG")
                zf.writestr(f"{id_code}.png", img_buf.getvalue())
        st.download_button("⬇️ Download QR ZIP", qr_zip.getvalue(), "qr_batch.zip")

# --- Record Edit Form ---
if equipment_id:
    st.markdown("### ✏️ Edit or Add Entry")
    with st.form("update_form"):
        updated = {}
        for col in table_columns:
            if col.lower() in ["id", "rowid", "timestamp"]:
                continue
            default = record[col] if record and col in record else ""
            updated[col] = st.text_input(col, value=default)

        submit = st.form_submit_button("✅ Save Entry")

    if submit:
        conn = sqlite3.connect(db_path)
        try:
            if record and matching_col:
                clause = ", ".join([f"{k}=?" for k in updated])
                conn.execute(
                    f"UPDATE {target_table} SET {clause} WHERE {matching_col} = ?",
                    list(updated.values()) + [equipment_id]
                )
                st.success("Record updated.")
            else:
                cols = ", ".join(updated.keys())
                placeholders = ", ".join(["?" for _ in updated])
                conn.execute(
                    f"INSERT INTO {target_table} ({cols}) VALUES ({placeholders})",
                    list(updated.values())
                )
                st.success("New record added.")

            # Log scan
            conn.execute("INSERT INTO scanned_items (equipment_id, timestamp, scanned_by) VALUES (?, ?, ?)", 
                         (equipment_id, str(datetime.now()), user_email))
            conn.commit()
            st.success("Scan recorded.")

        except Exception as e:
            st.error(f"Failed to save: {e}")
        finally:
            conn.close()

        # --- Optional Auto-Attach Maintenance Log ---
        if st.checkbox("🛠 Attach Maintenance Log"):
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("""CREATE TABLE IF NOT EXISTS maintenance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_id TEXT,
                    description TEXT,
                    date TEXT,
                    technician TEXT,
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
                conn.execute("INSERT INTO maintenance_log (equipment_id, description, date, technician) VALUES (?, ?, ?, ?)", 
                    (equipment_id, "Scanned and added via barcode page", str(datetime.today().date()), user_email))
                conn.commit()
                st.success("Maintenance log entry added.")
            except Exception as e:
                st.error(f"Failed to log maintenance: {e}")
            finally:
                conn.close()

# --- Recent Entries Preview ---
st.markdown("### 📋 Recent Scans")
try:
    conn = sqlite3.connect(db_path)
    scan_df = pd.read_sql("SELECT * FROM scanned_items ORDER BY timestamp DESC LIMIT 25", conn)
    st.dataframe(scan_df, use_container_width=True)
    conn.close()
except Exception as e:
    st.warning(f"Unable to preview scans: {e}")
