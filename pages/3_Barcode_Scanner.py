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

# Attempt to scan from camera
scanned = qrcode_scanner(key="scanner")
scanner_active = scanned is not None

if scanner_active:
    st.success("Scanner is active and working.")
else:
    st.warning("Waiting for camera input...")

# Manual fallback input
manual_code = st.text_input("Or manually enter a code")

code_to_save = scanned or manual_code

if code_to_save:
    st.success(f"Code Captured: {code_to_save}")

    conn = sqlite3.connect(db_path)
    try:
        # Save to scanned_items
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

# Show recent scans and match to inventory
with sqlite3.connect(db_path) as conn:
    st.subheader("Recent Scans")
    try:
        scans_df = pd.read_sql("SELECT * FROM scanned_items ORDER BY scanned_at DESC LIMIT 10", conn)
        st.dataframe(scans_df)

        # Export button
        csv = scans_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Scan History", csv, "scan_history.csv", mime="text/csv")
    except:
        st.info("No scans found.")

    # Attempt to match scanned code with equipment table
    st.subheader("Matching Equipment (if any)")
    try:
        equipment_df = pd.read_sql("SELECT * FROM equipment", conn)
        if code_to_save:
            matching = equipment_df[equipment_df.apply(lambda row: row.astype(str).str.contains(code_to_save).any(), axis=1)]
            if not matching.empty:
                st.success("Matching equipment record found:")
                st.dataframe(matching)
            else:
                st.warning("No matching equipment record found.")
    except:
        st.info("No equipment table found.")
