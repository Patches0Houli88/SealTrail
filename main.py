import streamlit as st
import os
import pandas as pd

# --- Native Login ---
if not st.user.is_logged_in:
    st.button("Log in with Google", on_click=st.login)
    st.stop()

# --- User Info + Logout ---
st.sidebar.markdown(f"👤 Logged in as: `{st.user.name}`")
st.sidebar.markdown(f"📧 {st.user.email}")
if st.sidebar.button("Logout"):
    st.logout()

# --- User Directory & DB ---
user_dir = f"data/{st.user.email.replace('@', '_at_')}"
os.makedirs(user_dir, exist_ok=True)
db_path = f"{user_dir}/default_dashboard.db"
if "db_path" not in st.session_state:
    st.session_state.db_path = db_path
    if not os.path.exists(db_path):
        open(db_path, "w").close()

# --- App Body ---
st.title("📦 Equipment & Inventory Tracking System")

# --- Upload CSV ---
st.subheader("📁 Upload Inventory CSV")
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.session_state.uploaded_df = df
    st.success(f"Uploaded {len(df)} rows.")
    st.dataframe(df)
else:
    st.info("Upload a CSV to preview inventory data.")
