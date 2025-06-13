import streamlit as st
import pandas as pd
import os
import shared_utils as su

st.set_page_config(page_title="Settings", layout="wide")
st.title("⚙Maintenance Interval Settings")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = su.get_db_path()
active_table = su.get_active_table()

st.sidebar.markdown(f"Role: {user_role} | 📧 Email: {user_email}")
st.sidebar.info(f"Active Table: `{active_table}`")

# --- Load Data ---
equipment_df = su.load_equipment()
type_col = su.get_type_column(equipment_df)

if not type_col:
    st.warning("No equipment type column found (equipment_type or type).")
    st.stop()

types = equipment_df[type_col].dropna().astype(str).str.strip().unique().tolist()

# --- Load YAML Settings ---
settings = su.load_settings_yaml()
if active_table not in settings:
    settings[active_table] = {}

# --- Settings Form ---
st.subheader("🔧 Configure Default Maintenance Intervals (in days)")

with st.form("settings_form"):
    for equip_type in types:
        current_val = settings[active_table].get(equip_type, 90)
        settings[active_table][equip_type] = st.number_input(
            f"Interval for '{equip_type}'", min_value=1, max_value=365, value=current_val, key=f"setting_{equip_type}"
        )
    submit = st.form_submit_button("💾 Save Intervals")

if submit:
    su.save_settings_yaml(settings)
    su.log_audit("Update Maintenance Settings", f"Updated intervals for {active_table}")
    st.success("✅ Settings successfully saved.")
