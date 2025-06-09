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

# --- Refresh DB list
db_files = [f for f in os.listdir(user_dir) if f.endswith(".db")]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

# --- Create new DB ---
new_db_name = st.sidebar.text_input("Create new database", placeholder="example: laptops.db")
if st.sidebar.button("Create DB") and new_db_name:
    if not new_db_name.endswith(".db"):
        new_db_name += ".db"
    full_path = os.path.join(user_dir, new_db_name)
    if not os.path.exists(full_path):
        open(full_path, "w").close()
        st.session_state.selected_db = new_db_name
        st.success(f"Created new database: {new_db_name}")
        st.rerun()
    else:
        st.warning("A database with that name already exists.")

# --- Choose existing DB
if db_files:
    current_selection = st.session_state.get("selected_db", db_files[0])
    selected_db = st.sidebar.selectbox("Choose a database", db_files, index=db_files.index(current_selection) if current_selection in db_files else 0)
    st.session_state.selected_db = selected_db
else:
    st.sidebar.warning("No databases available. Please create one.")
    st.stop()

# --- Admin: Delete / Rename ---
if user_role == "admin":
    with st.sidebar.expander("Manage Databases"):
        db_to_delete = st.selectbox("Delete database", [f for f in db_files if f != st.session_state.selected_db])
        if st.button("Delete Selected DB"):
            os.remove(os.path.join(user_dir, db_to_delete))
            st.success(f"Deleted {db_to_delete}")
            st.rerun()

        rename_db = st.text_input("Rename current database", value=st.session_state.selected_db.replace(".db", ""))
        if st.button("Rename DB") and rename_db:
            new_path = os.path.join(user_dir, rename_db + ".db")
            old_path = os.path.join(user_dir, st.session_state.selected_db)
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                st.session_state.selected_db = rename_db + ".db"
                st.success("Renamed database.")
                st.rerun()
            else:
                st.warning("A database with that name already exists.")

# --- Active DB Path ---
st.session_state.db_path = os.path.join(user_dir, st.session_state.selected_db)
st.markdown(f"**Current DB:** `{st.session_state.selected_db}`")
st.title("Equipment & Inventory Tracking System")

# --- Upload Inventory File ---
st.subheader("Upload Inventory File")
uploaded_file = st.file_uploader("Upload inventory data", type=["csv", "xlsx", "xls", "tsv", "json"])
if uploaded_file:
    file_type = uploaded_file.name.split(".")[-1].lower()
    try:
        if file_type == "csv":
            df = pd.read_csv(uploaded_file)
        elif file_type == "tsv":
            df = pd.read_csv(uploaded_file, sep="\t")
        elif file_type in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file)
        elif file_type == "json":
            df = pd.read_json(uploaded_file)
        else:
            st.error("Unsupported file type.")
            st.stop()

        conn = sqlite3.connect(st.session_state.db_path)
        df.to_sql("equipment", conn, if_exists="replace", index=False)
        conn.commit()
        conn.close()

        st.success(f"Uploaded and saved {len(df)} rows to the database.")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Inventory as CSV", csv, "inventory_export.csv", mime="text/csv")

        if st.button("Save to DB"):
            conn = sqlite3.connect(st.session_state.db_path)
            df.to_sql("equipment", conn, if_exists="replace", index=False)
            conn.commit()
            conn.close()
            st.success("Data manually saved.")

    except Exception as e:
        st.error(f"Upload failed: {e}")

else:
    try:
        conn = sqlite3.connect(st.session_state.db_path)
        df = pd.read_sql("SELECT * FROM equipment", conn)
        if not df.empty:
            st.subheader("Existing Inventory Data")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Inventory", csv, "inventory_export.csv", mime="text/csv")
        conn.close()
    except:
        st.info("No inventory found in this database.")

# --- Dashboard Summary ---
st.subheader("📊 Quick Dashboard")
with sqlite3.connect(st.session_state.db_path) as conn:
    try:
        items_df = pd.read_sql("SELECT * FROM equipment", conn)
        st.metric("Inventory Items", len(items_df))
    except:
        st.info("No inventory data.")

    try:
        logs_df = pd.read_sql("SELECT * FROM maintenance_log", conn)
        st.metric("Maintenance Logs", len(logs_df))
    except:
        st.info("No maintenance logs.")

    try:
        scans_df = pd.read_sql("SELECT * FROM scanned_items", conn)
        st.metric("Barcode Scans", len(scans_df))
    except:
        st.info("No scan data.")
