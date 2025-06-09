import streamlit as st
import os
import pandas as pd
import sqlite3
import yaml

# --- Native Login ---
if not st.user.is_logged_in:
    st.button("Log in with Google", on_click=st.login)
    st.stop()

# --- User Info + Logout ---
st.sidebar.markdown(f"Logged in as: {st.user.get('name', 'Unknown')}")
st.sidebar.markdown(f"Email: {st.user.get('email', 'unknown@example.com')}")
if st.sidebar.button("Logout"):
    st.logout()

# --- Load Roles ---
roles_config = {}
if os.path.exists("roles.yaml"):
    with open("roles.yaml") as f:
        roles_config = yaml.safe_load(f)

user_email = st.user.get("email", "unknown@example.com")
st.session_state.user_email = user_email
user_role = roles_config.get("users", {}).get(user_email, {}).get("role", "guest")
allowed_dbs = roles_config.get("users", {}).get(user_email, {}).get("allowed_dbs", [])

# --- User Directory ---
user_dir = f"data/{user_email.replace('@', '_at_')}"
os.makedirs(user_dir, exist_ok=True)

# --- Sidebar: Select or Create Database ---
st.sidebar.write(f"Role: {user_role.capitalize()}")
db_files = [f for f in os.listdir(user_dir) if f.endswith('.db')]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

# Dropdown to choose DB
if db_files:
    selected_db = st.sidebar.selectbox("Choose a database", db_files)
    st.session_state.selected_db = selected_db
else:
    st.sidebar.warning("No databases found. Create one below.")

# Create DB
new_db_name = st.sidebar.text_input("Create new database", placeholder="example: laptops.db")
if st.sidebar.button("Create DB") and new_db_name:
    if not new_db_name.endswith(".db"):
        new_db_name += ".db"
    full_path = os.path.join(user_dir, new_db_name)
    if not os.path.exists(full_path):
        open(full_path, "w").close()
        st.success(f"Created: {new_db_name}")
        st.session_state.selected_db = new_db_name
        st.rerun()
    else:
        st.sidebar.error("Database already exists.")

# --- Main Section ---
if "selected_db" not in st.session_state:
    st.warning("No database selected.")
    st.stop()

db_path = os.path.join(user_dir, st.session_state.selected_db)
st.session_state.db_path = db_path
st.title("Equipment & Inventory Tracking System")
st.markdown(f"**Current DB**: `{st.session_state.selected_db}`")

# Upload inventory
st.subheader("Upload Inventory File")
uploaded_file = st.file_uploader("Upload CSV, Excel, JSON or TSV", type=["csv", "xlsx", "xls", "tsv", "json"])
if uploaded_file:
    try:
        ext = uploaded_file.name.split(".")[-1].lower()
        if ext == "csv":
            df = pd.read_csv(uploaded_file)
        elif ext == "tsv":
            df = pd.read_csv(uploaded_file, sep="\t")
        elif ext in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file)
        elif ext == "json":
            df = pd.read_json(uploaded_file)
        else:
            st.error("Unsupported file type.")
            st.stop()

        st.dataframe(df)

        if st.button("Save to DB"):
            with sqlite3.connect(db_path) as conn:
                df.to_sql("equipment", conn, if_exists="replace", index=False)
            st.success("Saved to DB.")

    except Exception as e:
        st.error(f"Error processing file: {e}")

# Load and display saved inventory
try:
    with sqlite3.connect(db_path) as conn:
        existing_df = pd.read_sql("SELECT * FROM equipment", conn)
        if not existing_df.empty:
            st.subheader("Current Inventory")
            st.dataframe(existing_df)
except:
    st.info("No inventory data found.")

# Condensed Dashboard
st.subheader("📊 Dashboard Summary")
with sqlite3.connect(db_path) as conn:
    try:
        st.metric("Inventory Items", pd.read_sql("SELECT COUNT(*) as count FROM equipment", conn)["count"][0])
    except:
        st.metric("Inventory Items", 0)

    try:
        st.metric("Maintenance Logs", pd.read_sql("SELECT COUNT(*) as count FROM maintenance_log", conn)["count"][0])
    except:
        st.metric("Maintenance Logs", 0)

    try:
        st.metric("Barcode Scans", pd.read_sql("SELECT COUNT(*) as count FROM scanned_items", conn)["count"][0])
    except:
        st.metric("Barcode Scans", 0)
