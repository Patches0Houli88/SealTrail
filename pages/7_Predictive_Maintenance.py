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

# --- Load data centrally ---
equipment_df = su.load_equipment()
maintenance_df = su.load_maintenance()

# --- Load YAML settings ---
settings = su.load_settings_yaml()
table_settings = settings.get(active_table, {})

# --- Normalize ID columns ---
id_col = su.get_id_column(equipment_df)
type_col = su.get_type_column(equipment_df)

if id_col is None:
    st.error("No equipment_id column found.")
    st.stop()

# --- Predictive Logic ---
results = []

for _, row in equipment_df.iterrows():
    equip_id = row[id_col]
    equip_type = str(row.get(type_col, "")).strip()

    # Maintenance history for this equipment
    history = maintenance_df.loc[maintenance_df["equipment_id"] == equip_id].sort_values("date")
    history = history.dropna(subset=["date"])

    # Historical learning (optional - avg interval from actual history)
    if len(history) >= 2:
        intervals = history["date"].diff().dt.days[1:]
        avg_interval = int(intervals.mean())
    else:
        avg_interval = None

    # Use YAML setting if exists
    interval_setting = table_settings.get(equip_type, 90)

    last_maint = history["date"].max() if not history.empty else None

    # Predictive next due:
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
        predicted_next = None
        days_remaining = None
        status = "⚪ Never Serviced"

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

# --- Display Results ---
result_df = pd.DataFrame(results)
st.subheader("Predictive Maintenance Table")
st.dataframe(result_df, use_container_width=True)

# --- Filters ---
st.sidebar.subheader("Filter by Status")
status_filter = st.sidebar.selectbox("Status", ["All", "Overdue", "Due Soon", "On Schedule", "Never Serviced"])

if status_filter != "All":
    emoji_map = {
        "Overdue": "🔴",
        "Due Soon": "🟠",
        "On Schedule": "🟢",
        "Never Serviced": "⚪"
    }
    filtered_df = result_df[result_df["Predicted Status"].str.startswith(emoji_map[status_filter])]
    st.dataframe(filtered_df, use_container_width=True)
