import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import shared_utils as su

st.set_page_config(page_title="Predictive Maintenance", layout="wide")
st.title("Predictive Maintenance Engine")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = su.get_db_path()
active_table = su.get_active_table()

st.sidebar.markdown(f"Role: {user_role}  \n📧 Email: {user_email}")
st.sidebar.info(f"Active Table: `{active_table}`")

# --- Load Data using centralized shared_utils ---
equipment_df = su.load_equipment()
maintenance_df = su.load_maintenance()

# --- Load YAML settings ---
settings = su.load_settings_yaml()
table_settings = settings.get(active_table, {})

# --- Normalize columns ---
id_col = su.get_id_column(equipment_df)
type_col = su.get_type_column(equipment_df)

if id_col is None:
    st.error("No equipment ID column found.")
    st.stop()

# --- Predictive Logic ---
results = []

for _, row in equipment_df.iterrows():
    equip_id = row[id_col]
    equip_type = str(row.get(type_col, "")).strip()

    # Historical maintenance lookup
    history = maintenance_df[maintenance_df["equipment_id"] == equip_id].sort_values("date").dropna(subset=["date"])

    # Calculate average interval from history
    avg_interval = int(history["date"].diff().dt.days[1:].mean()) if len(history) >= 2 else None

    # Use user-defined interval or default to 90
    interval_setting = table_settings.get(equip_type, 90)
    last_maint = history["date"].max() if not history.empty else None

    # Predictive next due calculation
    if pd.notna(last_maint):
        predicted_next = last_maint + timedelta(days=interval_setting)
        days_remaining = (predicted_next - datetime.today()).days

        if days_remaining < 0:
            status = "🔴 Overdue"
        elif days_remaining <= 30:
            status = "🟠 Due Soon"
        else:
            status = "🟢 On Schedule"
    else:
        predicted_next, days_remaining, status = None, None, "⚪ Never Serviced"

    results.append({
        "Equipment ID": equip_id,
        "Equipment Type": equip_type,
        "Last Maintenance": last_maint.date() if pd.notna(last_maint) else None,
        "Interval (days)": interval_setting,
        "Avg Historical Interval": avg_interval,
        "Next Due": predicted_next.date() if predicted_next else None,
        "Days Remaining": days_remaining,
        "Predicted Status": status
    })

# --- Display ---
result_df = pd.DataFrame(results)
st.subheader("Predictive Maintenance Table")
st.dataframe(result_df, use_container_width=True)

# --- Filters ---
st.sidebar.subheader("Filter by Status")
status_filter = st.sidebar.selectbox("Status", ["All", "Overdue", "Due Soon", "On Schedule", "Never Serviced"])

if status_filter != "All":
    emoji = {"Overdue": "🔴", "Due Soon": "🟠", "On Schedule": "🟢", "Never Serviced": "⚪"}[status_filter]
    filtered_df = result_df[result_df["Predicted Status"].str.startswith(emoji)]
    st.dataframe(filtered_df, use_container_width=True)

# ✅ Log audit entry
su.log_audit("View Predictive Maintenance")
