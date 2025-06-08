import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner

st.title("📷 Barcode Scanner")

if "db_path" not in st.session_state:
    st.warning("Please log in from the homepage.")
    st.stop()

code = qrcode_scanner()

if code:
    st.success(f"Scanned: {code}")

    # Optional: lookup in database
    import sqlite3
    import pandas as pd
    conn = sqlite3.connect(st.session_state.db_path)
    df = pd.read_sql("SELECT * FROM equipment WHERE serial_number = ?", conn, params=(code,))
    conn.close()

    if not df.empty:
        st.write("Matching Equipment Found:", df)
    else:
        st.warning("No matching equipment found.")
