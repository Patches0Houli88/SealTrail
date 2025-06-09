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

# --- Select or Create Database ---
db_files = [f for f in os.listdir(user_dir) if f.endswith('.db')]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

st.sidebar.write(f"Role: {user_role.capitalize()}")

selected_db = None
if db_files:
    selected_db = st.selectbox("Choose a database to work with", db_files, index=0)
    if selected_db:
        st.session_state.selected_db = selected_db

new_db_name = st.text_input("Or create a new database", placeholder="example: laptops.db")

if new_db_name:
    if not new_db_name.endswith(".db"):
        new_db_name += ".db"
    full_new_path = os.path.join(user_dir, new_db_name)
    if not os.path.exists(full_new_path):
        open(full_new_path, "w").close()
        st.success(f"Created new database: {new_db_name}")
        db_files.append(new_db_name)
        selected_db = new_db_name
        st.session_state.selected_db = selected_db

# Optional: delete and rename functionality for admins only
if user_role == "admin" and selected_db:
    with st.expander("Manage Databases"):
        db_to_delete = st.selectbox("Delete database", [f for f in db_files if f != selected_db])
        if st.button("Delete Selected DB"):
            os.remove(os.path.join(user_dir, db_to_delete))
            st.success(f"Deleted {db_to_delete}. Refresh to update list.")

        rename_db = st.text_input("Rename current database", value=selected_db.replace(".db", ""))
        if st.button("Rename DB") and rename_db:
            new_path = os.path.join(user_dir, rename_db + ".db")
            old_path = os.path.join(user_dir, selected_db)
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                st.success(f"Renamed to {rename_db}.db. Refresh to use new name.")
                selected_db = rename_db + ".db"
                st.session_state.selected_db = selected_db
            else:
                st.warning("A database with that name already exists.")

# Ensure a valid database is selected
if "selected_db" not in st.session_state:
    st.warning("No database selected or available.")
    st.stop()

st.session_state.db_path = os.path.join(user_dir, st.session_state.selected_db)
st.markdown(f"Current DB: `{st.session_state.selected_db}`")

# --- App Body ---
st.title("Equipment & Inventory Tracking System")

# --- Upload File ---
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

        # Save to SQLite
        conn = sqlite3.connect(st.session_state.db_path)
        df.to_sql("equipment", conn, if_exists="replace", index=False)
        conn.commit()

        st.success(f"Uploaded and saved {len(df)} rows to the database.")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Inventory as CSV", csv, "inventory_export.csv", mime="text/csv")

        conn.close()
    except Exception as e:
        st.error(f"Failed to process file: {e}")
else:
    # Show existing data if available
    conn = sqlite3.connect(st.session_state.db_path)
    try:
        existing_df = pd.read_sql("SELECT * FROM equipment", conn)
        if not existing_df.empty:
            st.subheader("Existing Inventory Data")
            st.dataframe(existing_df)

            csv = existing_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Inventory as CSV", csv, file_name="inventory_export.csv", mime="text/csv")
    except Exception:
        st.info("No inventory data found. Upload a file to get started.")
    finally:
        conn.close()
