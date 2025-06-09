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

# Database Selection
selected_db = st.sidebar.selectbox("Choose database", db_files + ["➕ Create new"])
if selected_db == "➕ Create new":
    new_db_name = st.text_input("New database name (e.g., inventory.db)")
    if st.button("Create"):
        if not new_db_name.endswith(".db"):
            new_db_name += ".db"
        new_db_path = os.path.join(user_dir, new_db_name)
        if not os.path.exists(new_db_path):
            open(new_db_path, "w").close()
            st.session_state.selected_db = new_db_name
            st.success(f"Created and switched to: {new_db_name}")
        else:
            st.warning("That DB already exists.")
else:
    st.session_state.selected_db = selected_db

# Set db_path
if "selected_db" not in st.session_state:
    st.warning("No database selected or available.")
    st.stop()
st.session_state.db_path = os.path.join(user_dir, st.session_state.selected_db)
st.markdown(f"📁 **Current DB**: `{st.session_state.selected_db}`")

# --- Optional DB Management (Admin) ---
if user_role == "admin":
    with st.expander("🛠️ Manage Databases"):
        db_to_delete = st.selectbox("Delete a DB", [f for f in db_files if f != selected_db])
        if st.button("Delete Selected DB"):
            os.remove(os.path.join(user_dir, db_to_delete))
            st.success(f"Deleted {db_to_delete}")

        rename_db = st.text_input("Rename current DB", value=selected_db.replace(".db", ""))
        if st.button("Rename"):
            new_path = os.path.join(user_dir, rename_db + ".db")
            old_path = os.path.join(user_dir, selected_db)
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                st.session_state.selected_db = rename_db + ".db"
                st.success(f"Renamed to {rename_db}.db")
            else:
                st.warning("DB with that name exists.")

# --- Upload & Save File ---
st.title("Equipment & Inventory Tracking System")
st.subheader("Upload Inventory File")
uploaded_file = st.file_uploader("Upload inventory data", type=["csv", "xlsx", "xls", "tsv", "json"])
df = None

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

        st.dataframe(df)

        # Auto-save
        conn = sqlite3.connect(st.session_state.db_path)
        df.to_sql("equipment", conn, if_exists="replace", index=False)
        conn.commit()
        conn.close()

        st.success("Auto-saved to database.")

        # Manual save option
        if st.button("Save to DB"):
            conn = sqlite3.connect(st.session_state.db_path)
            df.to_sql("equipment", conn, if_exists="replace", index=False)
            conn.commit()
            conn.close()
            st.success("Manually saved to database.")

        # CSV Download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Inventory as CSV", csv, "inventory_export.csv", mime="text/csv")

    except Exception as e:
        st.error(f"Failed to process file: {e}")

else:
    # Load existing if nothing uploaded
    try:
        conn = sqlite3.connect(st.session_state.db_path)
        existing_df = pd.read_sql("SELECT * FROM equipment", conn)
        if not existing_df.empty:
            st.subheader("Existing Inventory Data")
            st.dataframe(existing_df)
    except:
        st.info("No inventory data found.")

# --- Quick Dashboard ---
st.subheader("📊 Quick Dashboard")
try:
    conn = sqlite3.connect(st.session_state.db_path)
    st.metric("Inventory Items", pd.read_sql("SELECT COUNT(*) FROM equipment", conn).iloc[0, 0])
    st.metric("Maintenance Logs", pd.read_sql("SELECT COUNT(*) FROM maintenance_log", conn).iloc[0, 0])
    st.metric("Barcode Scans", pd.read_sql("SELECT COUNT(*) FROM scanned_items", conn).iloc[0, 0])
    conn.close()
except:
    st.info("Unable to fetch some metrics.")
