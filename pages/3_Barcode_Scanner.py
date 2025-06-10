import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Barcode Scanner", layout="wide")
st.title("📷 Barcode Scanner")

# --- Session Checks ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")

if "db_path" not in st.session_state:
    st.error("No database selected. Please return to the main page.")
    st.stop()

db_path = st.session_state.db_path

# --- Table Selection ---
conn = sqlite3.connect(db_path)
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
conn.close()

st.sidebar.subheader("📂 Target Table")
target_table = st.sidebar.selectbox("Choose where to store scanned items", tables)

# --- Load Table Schema ---
conn = sqlite3.connect(db_path)
try:
    schema_df = pd.read_sql(f"SELECT * FROM {target_table} LIMIT 1", conn)
    table_columns = schema_df.columns.tolist()
except:
    table_columns = []

conn.close()

# --- Scan or Manual Entry ---
st.subheader("📥 Scan or Enter Barcode")
barcode = st.text_input("Scan Barcode or Enter Manually", placeholder="Scan or type barcode here")

# --- Optional Additional Fields ---
additional_data = {}
if table_columns:
    for col in table_columns:
        if col.lower() in ["id", "timestamp"]:
            continue  # skip standard fields
        additional_data[col] = st.text_input(f"{col}", key=f"field_{col}")

# --- Submit Button ---
if st.button("Save to Table"):
    if not barcode:
        st.warning("Please enter a barcode.")
    else:
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {target_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT,
                    timestamp TEXT,
                    {', '.join([f'{col} TEXT' for col in additional_data.keys()])}
                )
            """)

            timestamp = datetime.utcnow().isoformat()
            columns = ["barcode", "timestamp"] + list(additional_data.keys())
            values = [barcode, timestamp] + list(additional_data.values())
            placeholders = ','.join("?" for _ in values)

            conn.execute(f"INSERT INTO {target_table} ({','.join(columns)}) VALUES ({placeholders})", values)
            conn.commit()
            st.success(f"✅ Saved to `{target_table}` at {timestamp}")
        except Exception as e:
            st.error(f"❌ Error saving scan: {e}")
        finally:
            conn.close()

# --- View Scanned Items ---
st.subheader(f"📋 Recent Entries in `{target_table}`")
try:
    conn = sqlite3.connect(db_path)
    recent_scans = pd.read_sql(f"SELECT * FROM {target_table} ORDER BY ROWID DESC LIMIT 20", conn)
    st.dataframe(recent_scans)
except:
    st.warning("No scan data available yet.")
finally:
    conn.close()
