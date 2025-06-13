import streamlit as st
import pandas as pd
import shared_utils as su
import yaml
import os

st.set_page_config(page_title="⚙️ Maintenance Settings", layout="wide")
st.title("Maintenance Interval Settings")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = su.get_db_path()
active_table = su.get_active_table()

st.sidebar.markdown(f"Role: {user_role}  \n📧 Email: {user_email}")
st.sidebar.info(f"Active Table: `{active_table}`")

# --- Load Equipment Data
equipment_df = su.load_equipment()
type_col = su.get_type_column(equipment_df)

if not type_col:
    st.warning("No 'equipment_type' or 'type' column found in your active table.")
    st.stop()

types = equipment_df[type_col].dropna().astype(str).str.strip().unique().tolist()

# --- Load YAML Settings ---
settings = su.load_settings_yaml()
if active_table not in settings:
    settings[active_table] = {}

# --- Settings Form ---
st.subheader("Configure Maintenance Intervals (days)")

with st.form("settings_form"):
    for t in types:
        current = settings[active_table].get(t, 90)
        settings[active_table][t] = st.number_input(
            f"Interval for '{t}' (days):", min_value=1, max_value=365, value=current, key=f"setting_{t}"
        )
    submitted = st.form_submit_button("💾 Save Settings")

if submitted:
    su.save_settings_yaml(settings)
    st.success("✅ Settings saved successfully.")
