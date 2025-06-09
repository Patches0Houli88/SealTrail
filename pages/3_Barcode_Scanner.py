import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
import sqlite3
import pandas as pd

st.title("Barcode Scanner")
st.write("Scan equipment codes using your camera. If unsupported, manually enter a code.")

# Ensure active database
if "db_path" not in st.session_state:
    st.warning("No database selected. Please upload data first in the main page.")
    st.stop()

db_path = st.session_state.db_path

# Try to scan
scanned = qrcode_scanner(key="scanner")

# Scanner fallback input
manual_code = st.text_input("Or manually enter a code")

code_to_save = scanned or manual_code

if code_to_save:
    st.success(f"Code Captured: {code_to_save}")

    # Optional: Insert into scanned_items table
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS scanned_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute("INSERT INTO scanned_items (code) VALUES (?)", (code_to_save,))
        conn.commit()
        st.success("Saved to scanned_items table.")
    except Exception as e:
        st.error(f"Failed to save scan: {e}")
    finally:
        conn.close()

    # Show last few scans
    with sqlite3.connect(db_path) as conn:
        try:
            df = pd.read_sql("SELECT * FROM scanned_items ORDER BY scanned_at DESC LIMIT 5", conn)
            st.subheader("Recent Scans")
            st.dataframe(df)
        except:
            st.info("No scans found.")
