import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="🔎 Global Search", layout="wide")
st.title("🔎 Equipment Global Search")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = st.session_state.get("db_path", None)
active_table = st.session_state.get("active_table", "equipment")

st.sidebar.markdown(f"🔐 Role: {user_role} | 📧 Email: {user_email}")
st.sidebar.info(f"📦 Active Table: `{active_table}`")

if not db_path or not os.path.exists(db_path):
    st.error("No active database found.")
    st.stop()

# --- Load Data
conn = sqlite3.connect(db_path)

# Equipment Table
try:
    equipment_df = pd.read_sql_query(f"SELECT * FROM {active_table}", conn)
    id_col = next((col for col in equipment_df.columns if col.lower() in ["equipment_id", "asset_id"]), None)
    if id_col:
        equipment_df[id_col] = equipment_df[id_col].astype(str).str.strip()
except:
    equipment_df = pd.DataFrame()

# Maintenance Table
try:
    maintenance_df = pd.read_sql_query("SELECT * FROM maintenance_log", conn)
except:
    maintenance_df = pd.DataFrame()

# Scanned Table
try:
    scans_df = pd.read_sql_query("SELECT * FROM scanned_items", conn)
except:
    scans_df = pd.DataFrame()

conn.close()

# --- Search Input
st.subheader("🔎 Search Across All Data")
search_term = st.text_input("Enter search term (equipment ID, type, description, etc):")

# --- Equipment Search
if not equipment_df.empty:
    st.markdown("### 📦 Inventory Matches")
    mask = equipment_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False)).any(axis=1)
    st.dataframe(equipment_df[mask], use_container_width=True)

# --- Maintenance Search
if not maintenance_df.empty:
    st.markdown("### 🛠 Maintenance Matches")
    mask = maintenance_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False)).any(axis=1)
    st.dataframe(maintenance_df[mask], use_container_width=True)

# --- Scans Search
if not scans_df.empty:
    st.markdown("### 📷 Scans Matches")
    mask = scans_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False)).any(axis=1)
    st.dataframe(scans_df[mask], use_container_width=True)
