# -----------------------------
# 📄 main.py
# -----------------------------
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

# Auto-add user if not exists
if user_email not in roles_config["users"]:
    roles_config["users"][user_email] = {"role": "user", "allowed_dbs": []}
    with open("roles.yaml", "w") as f:
        yaml.safe_dump(roles_config, f)

user_role = roles_config["users"][user_email]["role"]
allowed_dbs = roles_config["users"][user_email]["allowed_dbs"]

st.session_state["user_email"] = user_email
st.session_state["user_role"] = user_role

# --- Sidebar: Role and DB Management ---
st.sidebar.write(f"Role: {user_role.capitalize()}")
db_files = [f for f in os.listdir(user_dir) if f.endswith(".db")]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

# --- Create DB ---
new_db_name = st.sidebar.text_input("Create new database", placeholder="example: my_inventory.db")
if st.sidebar.button("Create DB") and new_db_name:
    if not new_db_name.endswith(".db"):
        new_db_name += ".db"
    full_path = os.path.join(user_dir, new_db_name)
    if not os.path.exists(full_path):
        open(full_path, "w").close()
        st.session_state.selected_db = new_db_name
        if user_role != "admin":
            roles_config["users"][user_email]["allowed_dbs"].append(new_db_name)
            with open("roles.yaml", "w") as f:
                yaml.safe_dump(roles_config, f)
        st.success(f"Created: {new_db_name}")
        st.rerun()
    else:
        st.sidebar.error("Database already exists.")

# --- Select DB ---
if db_files:
    selected_db = st.sidebar.selectbox("Choose a database", db_files)
    st.session_state.selected_db = selected_db
else:
    st.sidebar.warning("No databases found. Create one above.")

# --- Delete DB ---
if db_files:
    deletable = db_files if user_role == "admin" else [db for db in db_files if db in allowed_dbs]
    with st.sidebar.expander("Delete Database"):
        db_to_delete = st.selectbox("Delete which?", deletable)
        if st.button("Delete DB"):
            os.remove(os.path.join(user_dir, db_to_delete))
            if db_to_delete in roles_config["users"][user_email]["allowed_dbs"]:
                roles_config["users"][user_email]["allowed_dbs"].remove(db_to_delete)
                with open("roles.yaml", "w") as f:
                    yaml.safe_dump(roles_config, f)
            st.success(f"{db_to_delete} deleted.")
            st.rerun()

# --- Main Section ---
if "selected_db" not in st.session_state:
    st.warning("No database selected.")
    st.stop()

db_path = os.path.join(user_dir, st.session_state.selected_db)
st.session_state.db_path = db_path
st.title("Equipment & Inventory Tracking System")
st.markdown(f"**Current DB**: `{st.session_state.selected_db}`")

# --- Upload Inventory ---
st.subheader("Upload File to Working Table")
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

        # Normalize column names
        df.columns = df.columns.str.strip()
        if "Asset_ID" in df.columns and "equipment_id" not in df.columns:
            df.rename(columns={"Asset_ID": "equipment_id"}, inplace=True)

        st.dataframe(df)

        table_name = st.text_input("Save to which table?", value="equipment")
        if st.button("Save to DB") and table_name:
            with sqlite3.connect(db_path) as conn:
                df.to_sql(table_name, conn, if_exists="replace", index=False)
            st.session_state.active_table = table_name
            st.success(f"Saved to '{table_name}' table.")

    except Exception as e:
        st.error(f"Error processing file: {e}")

# --- Active Table Selection ---
try:
    with sqlite3.connect(db_path) as conn:
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
    if tables:
        active_table = st.selectbox("Select active working table", tables, key="table_selector")
        st.session_state.active_table = active_table
        st.markdown(f"**Active Table**: `{active_table}`")
except Exception as e:
    st.warning(f"Error fetching tables: {e}")

# --- Show Current Active Table ---
try:
    with sqlite3.connect(db_path) as conn:
        current_df = pd.read_sql(f"SELECT * FROM {st.session_state.active_table}", conn)
        if not current_df.empty:
            st.subheader("📋 Current Active Table")
            st.dataframe(current_df, use_container_width=True)
except:
    st.info("No data found in active table.")
