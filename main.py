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

# --- Load/Create Roles Config ---
roles_config = {}
if os.path.exists("roles.yaml"):
    with open("roles.yaml") as f:
        roles_config = yaml.safe_load(f) or {}
else:
    roles_config = {}

roles_config.setdefault("users", {})

# Auto-add user if not present
if user_email not in roles_config["users"]:
    roles_config["users"][user_email] = {
        "role": "user",
        "allowed_dbs": []
    }
    with open("roles.yaml", "w") as f:
        yaml.safe_dump(roles_config, f)

user_role = roles_config["users"][user_email]["role"]
allowed_dbs = roles_config["users"][user_email]["allowed_dbs"]
st.session_state["user_email"] = user_email
st.session_state["user_role"] = user_role

# --- Sidebar Role + DB Management ---
st.sidebar.write(f"Role: {user_role.capitalize()}")
db_files = [f for f in os.listdir(user_dir) if f.endswith('.db')]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

# --- Create DB ---
new_db_name = st.sidebar.text_input("Create new database", placeholder="example: laptops.db")
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

# --- Active Table Selection ---
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

# --- Upload Inventory ---
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

        # --- Column Mapping ---
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            existing_cols = pd.read_sql("SELECT * FROM equipment LIMIT 1", conn).columns.tolist()
            st.warning("Column mismatch detected. Please map your columns.")
            col_mapping = {}
            for col in existing_cols:
                col_mapping[col] = st.selectbox(f"Map '{col}' to:", df.columns, key=col)
            df = df.rename(columns=col_mapping)[existing_cols]
        except:
            pass

        st.dataframe(df)

        if st.button("Save to DB"):
            df.to_sql("equipment", conn, if_exists="replace", index=False)
            conn.commit()
            st.success("Saved to DB.")
        conn.close()

    except Exception as e:
        st.error(f"Error processing file: {e}")

# --- Show Current Inventory ---
try:
    with sqlite3.connect(db_path) as conn:
        existing_df = pd.read_sql("SELECT * FROM equipment", conn)
        if not existing_df.empty:
            st.subheader("Current Inventory")
            st.dataframe(existing_df)
except:
    st.info("No inventory data found.")

# --- Dashboard Summary ---
st.subheader("📊 Dashboard Summary")
with sqlite3.connect(db_path) as conn:
    try:
        st.metric("Inventory Items", pd.read_sql("SELECT COUNT(*) as count FROM equipment", conn)["count"][0])
    except:
        st.metric("Inventory Items", 0)

    try:
        st.metric("Maintenance Logs", pd.read_sql("SELECT COUNT(*) as count FROM maintenance", conn)["count"][0])
    except:
        st.metric("Maintenance Logs", 0)

    try:
        st.metric("Barcode Scans", pd.read_sql("SELECT COUNT(*) as count FROM scanned_items", conn)["count"][0])
    except:
        st.metric("Barcode Scans", 0)
