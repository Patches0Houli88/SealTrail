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
active_table = st.session_state.get("active_table", "equipment")

st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")
st.sidebar.markdown(f"📦 Active Table: `{active_table}`")

if not db_path or not os.path.exists(db_path):
    st.error("No database loaded. Please return to the main page.")
    st.stop()

# --- Scanner UI ---
st.markdown("### 🔍 Scanner Status")
camera_active = st.checkbox("🟢 Start Scanner")
st.info("📸 Scanner is **active**." if camera_active else "⛔ Scanner is **inactive**.")

# --- Asset ID Input ---
st.markdown("### 🏷️ Scan or Enter Equipment ID")
equipment_id = st.text_input("Equipment ID (barcode or manual entry)", placeholder="e.g., EQP-001")

# --- Load Record if Exists ---
record = None
table_columns = []
id_col = None

if equipment_id and active_table:
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql(f"SELECT * FROM {active_table}", conn)
            table_columns = df.columns.tolist()
            id_col = next((col for col in df.columns if col.lower() in ["asset_id", "equipment_id"]), None)
            if id_col:
                record_df = df[df[id_col].astype(str).str.lower() == equipment_id.lower()]
                if not record_df.empty:
                    record = record_df.iloc[0].to_dict()
    except Exception as e:
        st.error(f"Error loading table: {e}")

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

    if submit and id_col:
        try:
            with sqlite3.connect(db_path) as conn:
                if record:
                    clause = ", ".join([f"{k}=?" for k in updated])
                    conn.execute(f"UPDATE {active_table} SET {clause} WHERE {id_col} = ?", list(updated.values()) + [equipment_id])
                    st.success("Record updated.")
                else:
                    cols = ", ".join(updated.keys())
                    placeholders = ", ".join(["?" for _ in updated])
                    conn.execute(f"INSERT INTO {active_table} ({cols}) VALUES ({placeholders})", list(updated.values()))
                    st.success("New record added.")
                conn.commit()
        except Exception as e:
            st.error(f"Failed to save: {e}")

        # --- Optional Auto-Attach Maintenance Log ---
        if st.checkbox("🛠 Attach Maintenance Log"):
            try:
                with sqlite3.connect(db_path) as conn:
                    conn.execute("""CREATE TABLE IF NOT EXISTS maintenance_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        equipment_id TEXT,
                        description TEXT,
                        date TEXT,
                        technician TEXT,
                        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )""")
                    conn.execute("INSERT INTO maintenance_log (equipment_id, description, date, technician) VALUES (?, ?, ?, ?)", 
                        (equipment_id, "Scanned and added via batch", str(datetime.today().date()), user_email))
                    conn.commit()
                    st.success("Maintenance log entry added.")
            except Exception as e:
                st.error(f"Failed to log maintenance: {e}")

# --- Recent Entries Preview ---
st.markdown("### 📋 Recent Records")
try:
    with sqlite3.connect(db_path) as conn:
        df_preview = pd.read_sql(f"SELECT * FROM {active_table} ORDER BY rowid DESC LIMIT 25", conn)
        st.dataframe(df_preview, use_container_width=True)
except Exception as e:
    st.warning(f"Unable to preview table: {e}")
