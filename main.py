import streamlit as st
import os
import pandas as pd
import sqlite3
import yaml

# --- Native Login ---
if not st.user.is_logged_in:
    st.button("Log in with Google", on_click=st.login)
    st.stop()

# --- User Info ---
user_email = st.user.get("email", "unknown@example.com")
user_name = st.user.get("name", "Unknown")
st.session_state["user_email"] = user_email

# --- Sidebar User Info ---
st.sidebar.markdown(f"Logged in as: {user_name}")
st.sidebar.markdown(f"Email: {user_email}")
if st.sidebar.button("Logout"):
    st.logout()

# --- Load/Create Roles ---
roles_config = {}
if os.path.exists("roles.yaml"):
    with open("roles.yaml") as f:
        roles_config = yaml.safe_load(f) or {}
else:
    roles_config = {}

roles_config.setdefault("users", {})
roles_config["users"].setdefault(user_email, {"role": "user", "allowed_dbs": []})

user_role = roles_config["users"][user_email]["role"]
allowed_dbs = roles_config["users"][user_email]["allowed_dbs"]
st.session_state["user_role"] = user_role

# --- User Directory ---
user_dir = f"data/{user_email.replace('@', '_at_')}"
os.makedirs(user_dir, exist_ok=True)

# --- DB Selection ---
st.sidebar.write(f"Role: {user_role.capitalize()}")
db_files = [f for f in os.listdir(user_dir) if f.endswith('.db')]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

selected_db = None
if db_files:
    selected_db = st.sidebar.selectbox("Choose a database", db_files)
    st.session_state["selected_db"] = selected_db
else:
    st.sidebar.warning("No databases found. Create one below.")

# --- DB Creation ---
new_db_name = st.sidebar.text_input("Create new database", placeholder="example: inventory.db")
if st.sidebar.button("Create DB") and new_db_name:
    if not new_db_name.endswith(".db"):
        new_db_name += ".db"
    full_path = os.path.join(user_dir, new_db_name)
    if not os.path.exists(full_path):
        open(full_path, "w").close()
        if user_role != "admin":
            roles_config["users"][user_email]["allowed_dbs"].append(new_db_name)
            with open("roles.yaml", "w") as f:
                yaml.safe_dump(roles_config, f)
        st.session_state["selected_db"] = new_db_name
        st.success(f"Created: {new_db_name}")
        st.rerun()
    else:
        st.sidebar.error("Database already exists.")

# --- DB Deletion ---
if db_files:
    with st.sidebar.expander("Delete Database"):
        to_delete = st.selectbox("Delete which?", db_files)
        if st.button("Delete DB"):
            os.remove(os.path.join(user_dir, to_delete))
            if to_delete in roles_config["users"][user_email]["allowed_dbs"]:
                roles_config["users"][user_email]["allowed_dbs"].remove(to_delete)
                with open("roles.yaml", "w") as f:
                    yaml.safe_dump(roles_config, f)
            st.success(f"{to_delete} deleted.")
            st.rerun()

# --- MAIN APP ---
if "selected_db" not in st.session_state:
    st.warning("No database selected.")
    st.stop()

db_path = os.path.join(user_dir, st.session_state["selected_db"])
st.session_state["db_path"] = db_path

st.title("Equipment & Inventory Tracking System")
st.markdown(f"**Current DB**: `{st.session_state['selected_db']}`")

# Continue with Upload, Inventory Table, and Dashboard Summary as before...
