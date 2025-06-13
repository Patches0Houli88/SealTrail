import streamlit as st
import pandas as pd
import os
from datetime import datetime
import shared_utils as su

st.set_page_config(page_title="Maintenance Log", layout="wide")
st.title("🛠 Maintenance Log")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")

db_path = su.get_db_path()
active_table = su.get_active_table()

# --- Load Maintenance Log ---
df = su.load_table("maintenance_log")
if not df.empty:
    st.subheader("🧾 Maintenance History")
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Maintenance Log", csv, "maintenance_log.csv", mime="text/csv")
else:
    st.info("No maintenance records yet.")

# --- Load Equipment Options ---
item_options = []
try:
    df_equipment = su.load_equipment()
    if not df_equipment.empty:
        df_equipment["equipment_id"] = df_equipment.get("equipment_id", df_equipment.get("Asset_ID", "")).astype(str).str.strip()
        df_equipment["display"] = df_equipment["equipment_id"]
        if "name" in df_equipment.columns:
            df_equipment["display"] += " - " + df_equipment["name"].astype(str)
        item_options = df_equipment["display"].tolist()
except Exception as e:
    st.warning(f"⚠️ Could not load equipment: {e}")

# --- Add Maintenance Record ---
st.subheader("➕ Add Maintenance Record")

with st.form("maintenance_entry_form"):
    input_mode = st.radio("Select Equipment Input Mode:", ["Dropdown", "Manual Entry"], horizontal=True)

    equipment_id = ""
    if input_mode == "Dropdown" and item_options:
        selected_equipment = st.selectbox("Choose Equipment", item_options)
        equipment_id = selected_equipment.split(" - ")[0].strip()
    elif input_mode == "Manual Entry":
        equipment_id = st.text_input("Enter Equipment ID Manually").strip()

    description = st.text_area("Work Description")
    date_performed = st.date_input("Date Performed", value=datetime.today())
    technician = st.text_input("Technician Name")

    submit_log = st.form_submit_button("💾 Save Record")

if submit_log and equipment_id and description:
    try:
        with su.load_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipment_id TEXT,
                    description TEXT,
                    date TEXT,
                    technician TEXT,
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT INTO maintenance_log (equipment_id, description, date, technician) 
                VALUES (?, ?, ?, ?)
            """, (equipment_id, description, str(date_performed), technician))

            # Auto update last_maintenance_date
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

            su.log_audit(db_path, user_email, "Add Maintenance", f"Added maintenance for {equipment_id}")
            conn.commit()

        st.success("✅ Maintenance record added.")
    except Exception as e:
        st.error(f"❌ Error saving record: {e}")
