import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Maintenance Log", layout="wide")
st.title("🛠 Maintenance Log")

# --- Session & Access Checks ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = st.session_state.get("db_path")
active_table = st.session_state.get("active_table", "equipment")

st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")
st.sidebar.markdown(f"📦 Table: `{active_table}`")

if not db_path or not os.path.exists(db_path):
    st.error("No active database found. Please return to the main page.")
    st.stop()

# --- Load and Display Maintenance Log ---
conn = sqlite3.connect(db_path)
try:
    df = pd.read_sql("SELECT * FROM maintenance_log", conn)
    if not df.empty:
        st.subheader("🧾 Maintenance History")
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        st.dataframe(df)
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
try:
    with sqlite3.connect(db_path) as conn:
        df_equipment = pd.read_sql(f"SELECT * FROM {active_table}", conn)
        id_col = next((c for c in df_equipment.columns if c.lower() in ["asset_id", "equipment_id"]), None)
        name_col = next((c for c in df_equipment.columns if c.lower() == "name"), None)

        if id_col:
            if name_col:
                item_options = (df_equipment[id_col].astype(str) + " - " + df_equipment[name_col].astype(str)).tolist()
            else:
                item_options = df_equipment[id_col].astype(str).tolist()
except Exception as e:
    st.warning(f"⚠️ Could not load equipment from `{active_table}`: {e}")

# --- Add Maintenance Record ---
st.subheader("➕ Add Maintenance Record")

with st.form("maintenance_entry_form"):
    input_mode = st.radio("Select Equipment Input Mode:", ["Dropdown", "Manual Entry"], horizontal=True)

    if input_mode == "Dropdown" and item_options:
        selected_equipment = st.selectbox("Choose Equipment", item_options)
        equipment_id = selected_equipment.split(" - ")[0].strip()
    else:
        equipment_id = st.text_input("Enter Equipment ID Manually").strip()

    description = st.text_area("Work Description")
    date_performed = st.date_input("Date Performed", value=datetime.today())
    technician = st.text_input("Technician Name")

    submit_log = st.form_submit_button("💾 Save Record")

if submit_log and equipment_id and description:
    try:
        conn = sqlite3.connect(db_path)
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
        conn.execute(
            "INSERT INTO maintenance_log (equipment_id, description, date, technician) VALUES (?, ?, ?, ?)",
            (equipment_id, description, str(date_performed), technician)
        )
        conn.commit()
        st.success("✅ Maintenance record added.")
    except Exception as e:
        st.error(f"❌ Error saving record: {e}")
    finally:
        conn.close()
