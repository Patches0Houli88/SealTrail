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
user_email = st.user.get("email", "unknown@example.com")
user_name = st.user.get("name", "Unknown")
st.sidebar.markdown(f"Logged in as: {user_name}")
st.sidebar.markdown(f"Email: {user_email}")
if st.sidebar.button("Logout"):
    st.logout()

# --- User Directory ---
user_dir = f"data/{user_email.replace('@', '_at_')}"
os.makedirs(user_dir, exist_ok=True)

# --- Load/Create Roles ---
roles_config = {}
if os.path.exists("roles.yaml"):
    with open("roles.yaml") as f:
        roles_config = yaml.safe_load(f) or {}
roles_config.setdefault("users", {})
if user_email not in roles_config["users"]:
    roles_config["users"][user_email] = {"role": "user", "allowed_dbs": []}
    with open("roles.yaml", "w") as f:
        yaml.safe_dump(roles_config, f)

user_role = roles_config["users"][user_email]["role"]
allowed_dbs = roles_config["users"][user_email]["allowed_dbs"]

st.session_state["user_email"] = user_email
st.session_state["user_role"] = user_role

# --- Sidebar: DB Creation ---
st.sidebar.write(f"Role: {user_role.capitalize()}")
new_db_name = st.sidebar.text_input("Create new database", placeholder="example: laptops.db")
if st.sidebar.button("Create DB") and new_db_name:
    if not new_db_name.endswith(".db"):
        new_db_name += ".db"
    full_path = os.path.join(user_dir, new_db_name)
    if not os.path.exists(full_path):
        open(full_path, "w").close()
        st.session_state.selected_db = new_db_name
        if user_role != "admin":
            allowed = roles_config["users"][user_email]["allowed_dbs"]
            if new_db_name not in allowed:
                allowed.append(new_db_name)
                with open("roles.yaml", "w") as f:
                    yaml.safe_dump(roles_config, f)
        st.success(f"Created: {new_db_name}")
        st.rerun()
    else:
        st.sidebar.error("Database already exists.")

# --- Sidebar: DB Selection ---
db_files = [f for f in os.listdir(user_dir) if f.endswith('.db')]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

if db_files:
    selected_db = st.sidebar.selectbox("Choose a database", db_files)
    st.session_state.selected_db = selected_db
else:
    st.sidebar.warning("No databases found. Create one above to continue.")
    st.stop()

# --- DB Path ---
db_path = os.path.join(user_dir, st.session_state.selected_db)
st.session_state.db_path = db_path

# --- Main Interface ---
st.title("Equipment & Inventory Tracking System")
st.markdown(f"**Current DB**: `{st.session_state.selected_db}`")

# --- Table Selection ---
try:
    conn = sqlite3.connect(db_path)
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
    conn.close()
    if tables:
        active_table = st.selectbox("Select active working table", tables, key="table_selector")
        st.session_state.active_table = active_table
        st.markdown(f"**Active Table**: `{active_table}`")
    else:
        st.warning("No tables found in the selected database.")
        st.session_state.active_table = None
except Exception as e:
    st.warning(f"Error fetching tables: {e}")
    st.session_state.active_table = None

# The rest of your inventory upload and summary code remains unchanged
