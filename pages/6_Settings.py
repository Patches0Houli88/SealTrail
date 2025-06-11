import streamlit as st
import sqlite3
import pandas as pd
import yaml
import os

st.set_page_config(page_title="Settings - Maintenance Intervals", layout="wide")
st.title("⚙️ Maintenance Settings")

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

# --- Load Active Equipment Types ---
try:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM {active_table}", conn)
    conn.close()

    if df.empty:
        st.warning("No equipment data found.")
        st.stop()

    # Normalize type column
    cols_lower = {c.lower(): c for c in df.columns}
    type_col = cols_lower.get("equipment_type") or cols_lower.get("type")
    if not type_col:
        st.warning("No 'Equipment Type' column found.")
        st.stop()

    types = df[type_col].dropna().astype(str).str.strip().unique().tolist()

except Exception as e:
    st.error(f"Error loading table: {e}")
    st.stop()

# --- Load YAML Settings ---
settings_file = "maintenance_settings.yaml"
if os.path.exists(settings_file):
    with open(settings_file, "r") as f:
        settings = yaml.safe_load(f) or {}
else:
    settings = {}

settings.setdefault(active_table, {})

# --- Settings Form ---
st.subheader("🔧 Configure Maintenance Intervals")
with st.form("settings_form"):
    for t in types:
        current = settings[active_table].get(t, 90)
        settings[active_table][t] = st.number_input(
            f"Maintenance Interval for {t} (days)",
            min_value=1, max_value=365, value=current, key=f"setting_{t}"
        )
    submitted = st.form_submit_button("💾 Save Settings")

if submitted:
    with open(settings_file, "w") as f:
        yaml.safe_dump(settings, f)
    st.success("✅ Settings saved.")
