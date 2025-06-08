import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
import sqlite3
import pandas as pd

st.title("Barcode Scanner")

if "db_path" not in st.session_state:
    st.warning("Please log in from the homepage.")
    st.stop()

st.markdown("Use your device camera to scan a barcode, or manually enter it below:")

# Try scanning
code = qrcode_scanner()

# Fallback manual input
manual_code = st.text_input("Or manually enter barcode")

# Use whichever is available
barcode = code or manual_code

if barcode:
    st.success(f"Scanned: {barcode}")

    # Query equipment table
    conn = sqlite3.connect(st.session_state.db_path)
    df = pd.read_sql("SELECT * FROM equipment WHERE serial_number = ?", conn, params=(barcode,))
    conn.close()

    if not df.empty:
        st.write("Matching Equipment Found:")
        st.dataframe(df)
    else:
        st.warning("No matching equipment found.")
