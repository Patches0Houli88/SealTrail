import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Maintenance Log", layout="wide")
st.title("Maintenance Log")

# --- Session & Access Checks ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"🔐 Role: {user_role} | 📧 Email: {user_email}")

if "user_email" not in st.session_state or "user_role" not in st.session_state:
    st.error("User not recognized. Please go to the main page and log in again.")
    st.stop()

if "db_path" not in st.session_state:
    st.warning("No active database. Please upload a file in the main page.")
    st.stop()

db_path = st.session_state.db_path

# --- Load Maintenance Log ---
conn = sqlite3.connect(db_path)
try:
    df = pd.read_sql("SELECT * FROM maintenance_log", conn)
    if not df.empty:
        st.subheader("🧾 Maintenance History")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Maintenance Log", csv, "maintenance_log.csv", mime="text/csv")
    else:
        st.info("No maintenance records yet.")
except:
    st.info("Maintenance log not found. Add an entry below to create it.")
finally:
    conn.close()

# --- Add New Record ---
with st.form("add_maintenance"):
    st.markdown("### 🛠 Add Maintenance Record")

    input_mode = st.radio("Select equipment input method:", ["Dropdown", "Manual Entry"], horizontal=True)

    if item_options and input_mode == "Dropdown":
        selected_equipment = st.selectbox("Choose Equipment", item_options)
        equipment_id = selected_equipment.split(" - ")[0].strip()
    else:
        equipment_id = st.text_input("Enter Asset_ID manually")

    description = st.text_area("Description of Work")
    date_performed = st.date_input("Date Performed", value=datetime.today())
    technician = st.text_input("Technician Name")
    submit_log = st.form_submit_button("Save Record")

# Load equipment options using Asset_ID or fallback
try:
    equipment_df = pd.read_sql("SELECT rowid, * FROM equipment", conn)
except:
    equipment_df = pd.DataFrame()

if not equipment_df.empty:
    if "Asset_ID" in equipment_df.columns:
        equipment_df["ref_id"] = equipment_df["Asset_ID"].astype(str)
    elif "id" in equipment_df.columns:
        equipment_df["ref_id"] = equipment_df["id"].astype(str)
    else:
        equipment_df["ref_id"] = equipment_df["rowid"].astype(str)

    if "name" in equipment_df.columns:
        equipment_df["label"] = equipment_df["ref_id"] + " - " + equipment_df["name"].astype(str)
    else:
        equipment_df["label"] = equipment_df["ref_id"]

    item_options = equipment_df["label"].tolist()
else:
    item_options = []

with st.form("add_maintenance"):
    if item_options:
        selected_equipment = st.selectbox("Link to Equipment", item_options)
        description = st.text_area("Description of Work")
        date_performed = st.date_input("Date Performed", value=datetime.today())
        technician = st.text_input("Technician Name")
        submit_log = st.form_submit_button("Save Record")
    else:
        st.warning("⚠️ No equipment available. Please add inventory first.")
        submit_log = False

if submit_log and selected_equipment and description:
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id TEXT,
                description TEXT,
                date TEXT,
                technician TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        equipment_id = selected_equipment.split(" - ")[0].strip()
        cursor.execute("INSERT INTO maintenance_log (equipment_id, description, date, technician) VALUES (?, ?, ?, ?)",
                       (equipment_id, description, str(date_performed), technician))
        conn.commit()
        st.success("✅ Maintenance record added.")
    except Exception as e:
        st.error(f"❌ Error saving record: {e}")
conn.close()
