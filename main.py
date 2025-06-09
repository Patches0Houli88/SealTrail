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

# --- Load Database List ---
db_files = [f for f in os.listdir(user_dir) if f.endswith('.db')]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

st.sidebar.write(f"Role: {user_role.capitalize()}")

# --- Select or Create Database ---
selected_db = st.session_state.get("selected_db", db_files[0] if db_files else None)

selected_db = st.sidebar.selectbox("Choose a database", db_files + ["➕ Create New"], index=0 if selected_db in db_files else len(db_files))

if selected_db == "➕ Create New":
    new_db_name = st.sidebar.text_input("Enter new DB name", placeholder="example: tools.db")
    if st.sidebar.button("Create Database") and new_db_name:
        if not new_db_name.endswith(".db"):
            new_db_name += ".db"
        new_path = os.path.join(user_dir, new_db_name)
        if not os.path.exists(new_path):
            open(new_path, "w").close()
            st.success(f"Created database {new_db_name}")
            selected_db = new_db_name
            st.session_state.selected_db = selected_db
else:
    st.session_state.selected_db = selected_db

if not st.session_state.get("selected_db"):
    st.warning("No database selected.")
    st.stop()

st.session_state.db_path = os.path.join(user_dir, st.session_state.selected_db)
st.markdown(f"**Current DB**: `{st.session_state.selected_db}`")

# --- Admin DB Management ---
if user_role == "admin":
    with st.expander("Manage Databases"):
        db_to_delete = st.selectbox("Delete database", [db for db in db_files if db != selected_db])
        if st.button("Delete Selected DB"):
            os.remove(os.path.join(user_dir, db_to_delete))
            st.success(f"Deleted {db_to_delete}. Refresh app.")

        rename_db = st.text_input("Rename current DB", selected_db.replace(".db", ""))
        if st.button("Rename DB"):
            new_name = rename_db + ".db"
            new_path = os.path.join(user_dir, new_name)
            old_path = os.path.join(user_dir, selected_db)
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                st.success(f"Renamed to {new_name}. Refresh app.")
                st.session_state.selected_db = new_name
            else:
                st.warning("That DB name already exists.")

# --- Upload File ---
st.subheader("📁 Upload Inventory File")
uploaded_file = st.file_uploader("Upload inventory data", type=["csv", "xlsx", "xls", "tsv", "json"])

if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    try:
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

        conn = sqlite3.connect(st.session_state.db_path)
        df.to_sql("equipment", conn, if_exists="replace", index=False)
        conn.commit()
        conn.close()

        st.success(f"{len(df)} rows saved to the database.")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "inventory_export.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Failed to load file: {e}")
else:
    # Show existing data
    try:
        conn = sqlite3.connect(st.session_state.db_path)
        df = pd.read_sql("SELECT * FROM equipment", conn)
        st.subheader("📦 Existing Inventory")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "inventory_export.csv", mime="text/csv")
    except:
        st.info("No existing inventory data found.")
    finally:
        conn.close()

# --- Dashboard Summary ---
st.subheader("📊 Quick Dashboard")
with sqlite3.connect(st.session_state.db_path) as conn:
    cols = st.columns(3)
    try:
        items = pd.read_sql("SELECT * FROM equipment", conn)
        cols[0].metric("Inventory Items", len(items))
    except:
        cols[0].info("No inventory.")

    try:
        logs = pd.read_sql("SELECT * FROM maintenance_log", conn)
        cols[1].metric("Maintenance Logs", len(logs))
    except:
        cols[1].info("No logs.")

    try:
        scans = pd.read_sql("SELECT * FROM scanned_items", conn)
        cols[2].metric("Barcode Scans", len(scans))
    except:
        cols[2].info("No scans.")
