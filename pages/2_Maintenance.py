import streamlit as st
import pandas as pd
import os
from datetime import datetime
import shared_utils as su

st.set_page_config(page_title="🛠 Maintenance Log", layout="wide")
st.title("🛠 Maintenance Log")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = su.get_db_path()
active_table = su.get_active_table()

st.sidebar.markdown(f"Role: {user_role}  \n📧 Email: {user_email}")
st.sidebar.info(f"Active Table: `{active_table}`")

# --- Load Data ---
equipment_df = su.load_equipment()
maintenance_df = su.load_maintenance()

# --- Maintenance Log Display ---
if not maintenance_df.empty:
    st.subheader("🧾 Maintenance History")
    st.dataframe(maintenance_df, use_container_width=True)
    csv = maintenance_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Maintenance Log", csv, "maintenance_log.csv", mime="text/csv")
else:
    st.info("No maintenance records yet.")

# --- Equipment ID Options ---
id_col = su.get_id_column(equipment_df)
item_options = equipment_df[id_col].dropna().astype(str).tolist()

# --- Add Maintenance Entry ---
st.subheader("➕ Add Maintenance Record")

with st.form("maintenance_entry_form"):
    input_mode = st.radio("Select Equipment Input Mode:", ["Dropdown", "Manual Entry"], horizontal=True)

    equipment_id = ""
    if input_mode == "Dropdown" and item_options:
        equipment_id = st.selectbox("Choose Equipment", item_options)
    elif input_mode == "Manual Entry":
        equipment_id = st.text_input("Enter Equipment ID Manually").strip()

    description = st.text_area("Work Description")
    date_performed = st.date_input("Date Performed", value=datetime.today())
    technician = st.text_input("Technician Name")

    submit_log = st.form_submit_button("💾 Save Record")

if submit_log and equipment_id and description:
    try:
        with su.load_connection() as conn:
            # Ensure table exists
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

            # Update last_maintenance_date in main equipment table
            df_equipment = pd.read_sql_query(f"SELECT * FROM {active_table}", conn)
            id_column = su.get_id_column(df_equipment)
            if id_column:
                if "last_maintenance_date" not in df_equipment.columns:
                    conn.execute(f"ALTER TABLE {active_table} ADD COLUMN last_maintenance_date TEXT")
                conn.execute(f"""
                    UPDATE {active_table}
                    SET last_maintenance_date = ?
                    WHERE LOWER({id_column}) = LOWER(?)
                """, (str(date_performed), equipment_id))

            conn.commit()

        su.log_audit("Add Maintenance", f"Logged maintenance for equipment {equipment_id}")
        st.success("✅ Maintenance record added.")
    except Exception as e:
        st.error(f"❌ Error saving record: {e}")
