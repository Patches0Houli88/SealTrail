import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Maintenance", layout="wide")
st.title("🛠 Maintenance Log")

# --- User Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")

if "user_email" not in st.session_state or "user_role" not in st.session_state:
    st.error("User not recognized. Please return to the main page.")
    st.stop()

# --- Validate DB ---
if "db_path" not in st.session_state:
    st.warning("No database selected. Please choose one on the main page.")
    st.stop()

db_path = st.session_state.db_path
conn = sqlite3.connect(db_path)

# --- Load Existing Maintenance Log ---
st.subheader("🔍 Maintenance History")
try:
    df = pd.read_sql("SELECT * FROM maintenance_log", conn)
    if not df.empty:
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download CSV", csv, "maintenance_log.csv", mime="text/csv")
    else:
        st.info("No maintenance logs found.")
except:
    st.info("Maintenance log not yet created.")

# --- Load Equipment IDs for Linking ---
try:
    equipment_df = pd.read_sql("SELECT * FROM equipment", conn)
except:
    equipment_df = pd.DataFrame()

if not equipment_df.empty and "equipment_id" in equipment_df.columns:
    equipment_df["equipment_id"] = equipment_df["equipment_id"].astype(str)
    equipment_df["label"] = equipment_df["equipment_id"]
    if "name" in equipment_df.columns:
        equipment_df["label"] = equipment_df["equipment_id"] + " - " + equipment_df["name"].astype(str)
    item_options = equipment_df["label"].tolist()
else:
    item_options = ["No equipment available"]

# --- Add New Maintenance Record ---
st.subheader("➕ Add Maintenance Record")
with st.form("add_maintenance"):
    selected_equipment = st.selectbox("Link to Equipment", item_options)
    description = st.text_area("Description of Work")
    date_performed = st.date_input("Date Performed", value=datetime.today())
    technician = st.text_input("Technician Name")
    submit_log = st.form_submit_button("Save Record")

if submit_log and selected_equipment != "No equipment available" and description:
    # Extract actual equipment_id
    equipment_id = selected_equipment.split(" - ")[0].strip()
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS maintenance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT,
            description TEXT,
            date TEXT,
            technician TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute("INSERT INTO maintenance_log (equipment_id, description, date, technician) VALUES (?, ?, ?, ?)",
                     (equipment_id, description, str(date_performed), technician))
        conn.commit()
        st.success("✅ Maintenance record added.")
        st.experimental_rerun()
    except Exception as e:
        st.error(f"❌ Error saving record: {e}")

conn.close()
