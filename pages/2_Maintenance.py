import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Maintenance Log", layout="wide")
st.title("🛠 Maintenance Log")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")

if "db_path" not in st.session_state:
    st.error("No active database found. Please select or upload one in the main page.")
    st.stop()

db_path = st.session_state.db_path
active_table = st.session_state.get("active_table", "equipment")

# Whenever you load equipment_df
equipment_df = pd.read_sql_query(f"SELECT * FROM {active_table}", conn)
if "equipment_id" in equipment_df.columns:
    equipment_df["equipment_id"] = equipment_df["equipment_id"].astype(str).str.strip()

# Same for maintenance_df if relevant:
maintenance_df = pd.read_sql_query("SELECT * FROM maintenance_log", conn)
if "equipment_id" in maintenance_df.columns:
    maintenance_df["equipment_id"] = maintenance_df["equipment_id"].astype(str).str.strip()
# --- Load and Display Maintenance Log ---
conn = sqlite3.connect(db_path)
try:
    df = pd.read_sql("SELECT * FROM maintenance_log", conn)
    if not df.empty:
        st.subheader("🧾 Maintenance History")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Maintenance Log", csv, "maintenance_log.csv", mime="text/csv")
    else:
        st.info("No maintenance records yet.")
except:
    st.info("Maintenance log not found. Add a record below to start it.")
finally:
    conn.close()

# --- Load Equipment Options ---
item_options = []
match_col, name_col = None, None
try:
    with sqlite3.connect(db_path) as conn:
        df_equipment = pd.read_sql(f"SELECT * FROM {active_table}", conn)
        match_col = next((col for col in df_equipment.columns if col.lower() in ["asset_id", "equipment_id"]), None)
        name_col = next((col for col in df_equipment.columns if col.lower() == "name"), None)
        if match_col:
            if name_col:
                item_options = (df_equipment[match_col].astype(str) + " - " + df_equipment[name_col].astype(str)).tolist()
            else:
                item_options = df_equipment[match_col].astype(str).tolist()
except Exception as e:
    st.warning(f"⚠️ Could not load equipment: {e}")

# --- Add Maintenance Record ---
st.subheader("➕ Add Maintenance Record")

with st.form("maintenance_entry_form"):
    input_mode = st.radio("Select Equipment Input Mode:", ["Dropdown", "Manual Entry"], horizontal=True)

    equipment_id = ""
    manual_id = ""
    if input_mode == "Dropdown" and item_options:
        selected = st.selectbox("Choose Equipment", item_options, key="dropdown_input")
        equipment_id = selected.split(" - ")[0].strip()
    elif input_mode == "Manual Entry":
        manual_id = st.text_input("Enter Equipment ID", key="manual_input")
        equipment_id = manual_id.strip()

    location = st.text_input("Location (Room, Site, or Zone)")
    description = st.text_area("Work Description")
    date_performed = st.date_input("Date Performed", value=datetime.today())
    technician = st.text_input("Technician Name")

    submit_log = st.form_submit_button("💾 Save Record")

if submit_log and equipment_id and description:
    try:
        conn = sqlite3.connect(db_path)

        # --- Ensure Columns Exist ---
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id TEXT,
                description TEXT,
                date TEXT,
                technician TEXT,
                location TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert record
        conn.execute("""
            INSERT INTO maintenance_log (equipment_id, description, date, technician, location)
            VALUES (?, ?, ?, ?, ?)
        """, (equipment_id, description, str(date_performed), technician, location))

        # Optional: Update last_maintenance_date in inventory
        df_equipment = pd.read_sql(f"SELECT * FROM {active_table}", conn)
        id_col = next((col for col in df_equipment.columns if col.lower() in ["asset_id", "equipment_id"]), None)
        if id_col:
            if "last_maintenance_date" not in df_equipment.columns:
                conn.execute(f"ALTER TABLE {active_table} ADD COLUMN last_maintenance_date TEXT")
            conn.execute(f"""
                UPDATE {active_table}
                SET last_maintenance_date = ?
                WHERE LOWER({id_col}) = LOWER(?)
            """, (str(date_performed), equipment_id))

        conn.commit()
        st.success("✅ Maintenance record added.")
    except Exception as e:
        st.error(f"❌ Error saving record: {e}")
    finally:
        conn.close()
