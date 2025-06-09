import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner

st.title("Barcode Scanner")
st.write("Scan equipment codes using your camera.")

scanned = qrcode_scanner(key="scanner")

if scanned:
    st.success(f"Scanned Code: {scanned}")
