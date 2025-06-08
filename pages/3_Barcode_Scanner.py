import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
from pyzbar import pyzbar

st.title("📷 Barcode Scanner")

if "db_path" not in st.session_state:
    st.warning("🔐 Please log in first from the homepage.")
    st.stop()

class BarcodeScanner(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        decoded = pyzbar.decode(img)
        for obj in decoded:
            pts = np.array([(pt.x, pt.y) for pt in obj.polygon], np.int32)
            cv2.polylines(img, [pts], True, (0, 255, 0), 2)
            barcode_text = obj.data.decode("utf-8")
            cv2.putText(img, barcode_text, (pts[0][0], pts[0][1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            st.session_state.last_scanned = barcode_text
        return img

webrtc_streamer(key="scanner", video_processor_factory=BarcodeScanner)

if "last_scanned" in st.session_state:
    st.success(f"Scanned: {st.session_state.last_scanned}")
