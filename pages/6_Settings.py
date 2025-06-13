import streamlit as st
import sqlite3
import pandas as pd
import yaml
import os
import shared_utils as su

st.set_page_config(page_title="Equipment Settings", layout="wide")
st.title("⚙️ Predictive Maintenance Settings")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")

db_path = st.session_state.get("db_path")
active_table = st.session_state.get("active_table", "equipment")

if not db_path or not os.path.exists(db_path):
    st.error("No database loaded. Please return to the main page.")
    st.stop()

st.sidebar.markdown(f"📦 Active Table: `{active_table}`")

# --- Load Equipment Types Dynamically ---
df = su.load_table(db_path, active_table)
if "equipment_type" in df.columns:
    df["equipment_type"] = df["equipment_type"].astype(str).str.strip()
    unique_types = sorted(df["equipment_type"].dropna().unique().tolist())
else:
    unique_types = []

# --- Load Existing Settings ---
settings_file = f"settings_{os.path.basename(db_path)}_{active_table}.yaml"
if os.path.exists(settings_file):
    with open(settings_file) as f:
        lifecycle_settings = yaml.safe_load(f) or {}
else:
    lifecycle_settings = {}

st.subheader("🛠 Define Lifecycle Intervals (days)")

if not unique_types:
    st.warning("No equipment types detected. Upload data first.")
else:
    for eq_type in unique_types:
        default_days = lifecycle_settings.get(eq_type, 30)
        lifecycle_settings[eq_type] = st.number_input(
            f"Lifecycle for '{eq_type}'", min_value=1, max_value=1000, value=default_days
        )

    if st.button("💾 Save Settings"):
        with open(settings_file, "w") as f:
            yaml.safe_dump(lifecycle_settings, f)
        st.success("Settings saved successfully!")
