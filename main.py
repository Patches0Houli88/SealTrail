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
user_role = roles_config.get("users", {}).get(user_email, {}).get("role", "guest")
allowed_dbs = roles_config.get("users", {}).get(user_email, {}).get("allowed_dbs", [])

st.session_state.user_email = user_email
user_dir = f"data/{user_email.replace('@', '_at_')}"
os.makedirs(user_dir, exist_ok=True)

# --- List DB Files ---
db_files = [f for f in os.listdir(user_dir) if f.endswith(".db")]
if allowed_dbs != ["all"]:
    db_files = [f for f in db_files if f in allowed_dbs]

st.sidebar.write(f"Role: {user_role.capitalize()}")

# --- Create New Database ---
st.subheader("Select or Create a Database")
new_db_name = st.text_input("New Database Name", placeholder="example: laptops.db")

if st.button("Create Database"):
    if new_db_name:
        if not new_db_name.endswith(".db"):
            new_db_name += ".db"
        new_path = os.path.join(user_dir, new_db_name)
        if not os.path.exists(new_path):
            open(new_path, "w").close()
            st.session_state.selected_db = new_db_name
            st.success(f"Created and selected: {new_db_name}")
            st.rerun()
        else:
            st.warning("A database with that name already exists.")

# --- Select Existing Database ---
if db_files:
    selected_db = st.sidebar.selectbox("Choose a database", db_files, index=0)
    if selected_db:
        st.session_state.selected_db = selected_db

# --- No Database Selected ---
if "selected_db" not in st.session_state:
    st.warning("Please create or select a database to continue.")
    st.stop()

st.session_state.db_path = os.path.join(user_dir, st.session_state.selected_db)
st.markdown(f"**Current DB: `{st.session_state.selected_db}`**")

# --- Admin DB Management ---
if user_role == "admin":
    with st.expander("Manage Databases"):
        db_to_delete = st.selectbox("Delete database", [f for f in db_files if f != st.session_state.selected_db])
        if st.button("Delete Selected DB"):
            os.remove(os.path.join(user_dir, db_to_delete))
            st.success(f"Deleted {db_to_delete}")
            st.rerun()

        rename_db = st.text_input("Rename current DB", value=st.session_state.selected_db.replace(".db", ""))
        if st.button("Rename DB"):
            new_path = os.path.join(user_dir, rename_db + ".db")
            old_path = os.path.join(user_dir, st.session_state.selected_db)
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                st.success(f"Renamed to {rename_db}.db")
                st.session_state.selected_db = rename_db + ".db"
                st.rerun()
            else:
                st.warning("A DB with that name already exists.")

# --- File Upload ---
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

        st.success(f"Uploaded and auto-saved {len(df)} rows.")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Inventory as CSV", csv, "inventory_export.csv", mime="text/csv")

        if st.button("Save to DB"):
            conn = sqlite3.connect(st.session_state.db_path)
            df.to_sql("equipment", conn, if_exists="replace", index=False)
            conn.commit()
            conn.close()
            st.success("Manually saved to DB.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    try:
        conn = sqlite3.connect(st.session_state.db_path)
        df = pd.read_sql("SELECT * FROM equipment", conn)
        if not df.empty:
            st.subheader("Current Inventory")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Inventory as CSV", csv, "inventory_export.csv", mime="text/csv")
        conn.close()
    except:
        st.info("No inventory found.")

# --- Quick Dashboard ---
st.subheader("📊 Quick Stats")
with sqlite3.connect(st.session_state.db_path) as conn:
    try:
        items_df = pd.read_sql("SELECT * FROM equipment", conn)
        st.metric("Inventory Items", len(items_df))
    except:
        st.info("No inventory yet.")

    try:
        logs_df = pd.read_sql("SELECT * FROM maintenance_log", conn)
        st.metric("Maintenance Logs", len(logs_df))
    except:
        st.info("No maintenance logs.")

    try:
        scans_df = pd.read_sql("SELECT * FROM scanned_items", conn)
        st.metric("Barcode Scans", len(scans_df))
    except:
        st.info("No scans recorded.")
