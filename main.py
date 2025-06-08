import streamlit as st
import os

# --- Native OIDC Authentication ---
if not st.user.is_logged_in:
    st.button("🔐 Log in with Google", on_click=st.login)
    st.stop()

# --- Show user info and logout ---
st.sidebar.markdown(f"👤 Logged in as: `{st.user.name}`")
st.sidebar.markdown(f"📧 {st.user.email}")
if st.sidebar.button("Logout"):
    st.logout()

# --- Set up user-specific directory and default dashboard DB ---
user_dir = f"data/{st.user.email.replace('@', '_at_')}"
os.makedirs(user_dir, exist_ok=True)

default_db = f"{user_dir}/default_dashboard.db"
if "db_path" not in st.session_state:
    st.session_state.db_path = default_db
    if not os.path.exists(default_db):
        open(default_db, "w").close()

# --- Load dashboard or app logic ---
st.title("📦 Equipment & Inventory Tracking System")
st.success("Dashboard loaded.")

# You can import or include your main dashboard logic here, e.g.:
# from dashboard import load_dashboard
# load_dashboard(st.session_state.db_path)
