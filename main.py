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
st.sidebar.markdown(f"Logged in as: {st.user.name}")
st.sidebar.markdown(f"Email: {st.user.email}")
if st.sidebar.button("Logout"):
    st.logout()

# --- Load Roles ---
roles_config = {}
if os.path.exists("roles.yaml"):
    with open("roles.yaml") as f:
        roles_config = yaml.safe_load(f)

user_email = st.user.email
user_role = roles_config.get("users", {}).get(user_email, {}).get("role", "guest")
allowed_dbs = roles_config.get("users", {}).get(user_email, {}).get("allowed_dbs", [])

# --- User Directory ---
user_dir = f"data/{st.user.email.replace('@', '_at_')}"
os.makedirs(user_dir, exist_ok=True)

# --- Select or Create Database ---
db_files = [f for f in os.listdir(user_dir) if f.endswith('.db')]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs]

st.sidebar.write(f"Role: {user_role.capitalize()}")
st.subheader("Select or Create Equipment Database")
selected_db = st.selectbox("Choose a database to work with", db_files)

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

# Optional: delete and rename functionality for admins only
if user_role == "admin":
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
            else:
                st.warning("A database with that name already exists.")

# Set session DB path
st.session_state.db_path = os.path.join(user_dir, selected_db)
st.markdown(f"Current DB: `{selected_db}`")

# --- App Body ---
st.title("Equipment & Inventory Tracking System")

# --- Upload CSV ---
st.subheader("Upload Inventory CSV")
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Save to SQLite immediately
    conn = sqlite3.connect(st.session_state.db_path)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_number TEXT,
        type TEXT,
        model TEXT,
        status TEXT,
        purchase_date TEXT,
        warranty_expiry TEXT,
        notes TEXT
    )
    """)
    conn.commit()

    df.to_sql("equipment", conn, if_exists="replace", index=False)
    conn.commit()

    st.success(f"Uploaded and saved {len(df)} rows to the database.")

    # Reload and show from DB
    df_reload = pd.read_sql("SELECT * FROM equipment", conn)
    st.dataframe(df_reload)

    # Download button
    csv = df_reload.to_csv(index=False).encode("utf-8")
    st.download_button("Download Inventory as CSV", csv, file_name="inventory_export.csv", mime="text/csv")

    conn.close()
else:
    # Show existing data if available
    conn = sqlite3.connect(st.session_state.db_path)
    try:
        existing_df = pd.read_sql("SELECT * FROM equipment", conn)
        if not existing_df.empty:
            st.subheader("Existing Inventory Data")
            st.dataframe(existing_df)

            # Download existing data
            csv = existing_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Inventory as CSV", csv, file_name="inventory_export.csv", mime="text/csv")
    except Exception:
        st.info("No inventory data found. Upload a CSV to get started.")
    finally:
        conn.close()
