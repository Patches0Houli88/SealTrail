import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
import sqlite3
import pandas as pd

st.title("Barcode Scanner")

if "db_path" not in st.session_state:
    st.warning("Please log in from the homepage.")
    st.stop()

st.markdown("Activate your scanner below or use the input as a fallback. If using a webcam, make sure browser permissions are granted.")

# Activation button
activate_scan = st.button("Start Scanner")

barcode = None

if activate_scan:
    scanned_code = qrcode_scanner()
    if scanned_code:
        st.success(f"Scanned: {scanned_code}")
        barcode = scanned_code
    else:
        st.info("Waiting for camera input...")

# Manual fallback
manual_code = st.text_input("Or manually enter barcode")

barcode = barcode or manual_code

if barcode:
    conn = sqlite3.connect(st.session_state.db_path)
    df = pd.read_sql("SELECT * FROM equipment WHERE serial_number = ?", conn, params=(barcode,))
    conn.close()

    if not df.empty:
        st.write("Matching Equipment Found:")
        st.dataframe(df)
    else:
        st.warning("No matching equipment found.")
