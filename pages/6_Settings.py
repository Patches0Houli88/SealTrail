import streamlit as st
import sqlite3
import pandas as pd  
import yaml
import os

st.set_page_config(page_title="Settings & Lifecycle Rules", layout="wide")
st.title("⚙️ Equipment Settings")

# --- User Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = st.session_state.get("db_path", None)
active_table = st.session_state.get("active_table", "equipment")

st.sidebar.markdown(f"🔐 Role: {user_role} | 📧 {user_email}")
st.sidebar.info(f"Active Table: `{active_table}`")

if not db_path or not os.path.exists(db_path):
    st.error("No active database found.")
    st.stop()

# --- Settings file path (per DB file, fully isolated) ---
settings_file = f"settings_{os.path.basename(db_path)}.yaml"

# --- Load existing settings or defaults ---
if os.path.exists(settings_file):
    with open(settings_file, "r") as f:
        settings = yaml.safe_load(f) or {}
else:
    settings = {
        "default_lifecycle_days": 90,
        "type_rules": {},
        "warning_days": 10
    }

# --- Global Defaults ---
st.header("🔧 Global Maintenance Defaults")

settings["default_lifecycle_days"] = st.number_input(
    "Default lifecycle (days between maintenance)", 
    min_value=1, max_value=1000, 
    value=settings.get("default_lifecycle_days", 90)
)

settings["warning_days"] = st.number_input(
    "Warning period before due (days)", 
    min_value=1, max_value=60, 
    value=settings.get("warning_days", 10)
)

# --- Equipment Type Overrides ---
st.header("🔬 Type-Specific Lifecycles")

# Load equipment types from current data
try:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM {active_table}", conn)
    conn.close()

    cols_lower = {col.lower(): col for col in df.columns}
    type_col = cols_lower.get("equipment_type") or cols_lower.get("type")

    if type_col:
        equipment_types = sorted(df[type_col].dropna().unique())
    else:
        equipment_types = []

except Exception as e:
    st.warning(f"Error reading types: {e}")
    equipment_types = []

if equipment_types:
    for eq_type in equipment_types:
        key = str(eq_type)
        settings["type_rules"][key] = st.number_input(
            f"Lifecycle for '{eq_type}' (days)", 
            min_value=1, max_value=1000, 
            value=settings.get("type_rules", {}).get(key, settings["default_lifecycle_days"]),
            key=f"type_{key}"
        )
else:
    st.info("No equipment types detected. Upload data first.")

# --- Save Button ---
if st.button("💾 Save Settings"):
    with open(settings_file, "w") as f:
        yaml.dump(settings, f)
    st.success("✅ Settings saved successfully!")
