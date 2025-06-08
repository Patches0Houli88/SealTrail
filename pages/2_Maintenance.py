import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

st.title("Maintenance Log")

if "db_path" not in st.session_state:
    st.warning("Please log in from the homepage.")
    st.stop()

st.caption(f"Current Database: {os.path.basename(st.session_state.db_path)}")

conn = sqlite3.connect(st.session_state.db_path)
conn.execute("""
CREATE TABLE IF NOT EXISTS maintenance (
    maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER,
    maintenance_type TEXT,
    maintenance_date TEXT,
    performed_by TEXT,
    description TEXT,
    next_scheduled TEXT
)
""")
conn.commit()

conn.execute("""
CREATE TABLE IF NOT EXISTS access_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT,
    action TEXT,
    timestamp TEXT
)
""")
conn.commit()

user_email = st.session_state.get("user_email", "unknown")
conn.execute(
    "INSERT INTO access_log (user_email, action, timestamp) VALUES (?, ?, ?)",
    (user_email, "Viewed Maintenance Log", datetime.now().isoformat())
)
conn.commit()

# View Maintenance Records
df = pd.read_sql("SELECT * FROM maintenance", conn)
st.subheader("View Maintenance Records")
st.dataframe(df, use_container_width=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Maintenance Records", csv, file_name="maintenance_log.csv", mime="text/csv")

# Log New Maintenance
st.subheader("Log New Maintenance")
with st.form("maintenance_form"):
    equipment_id = st.number_input("Equipment ID", step=1)
    maint_type = st.selectbox("Maintenance Type", ["Preventive", "Corrective"])
    maint_date = st.date_input("Maintenance Date")
    performed_by = st.text_input("Performed By")
    description = st.text_area("Description")
    next_sched = st.date_input("Next Scheduled")
    submit = st.form_submit_button("Add Maintenance Log")

    if submit:
        conn.execute(
            "INSERT INTO maintenance (equipment_id, maintenance_type, maintenance_date, performed_by, description, next_scheduled) VALUES (?, ?, ?, ?, ?, ?)",
            (equipment_id, maint_type, maint_date.isoformat(), performed_by, description, next_sched.isoformat())
        )
        conn.commit()
        st.success("Maintenance log added.")

        conn.execute(
            "INSERT INTO access_log (user_email, action, timestamp) VALUES (?, ?, ?)",
            (user_email, "Added Maintenance Log", datetime.now().isoformat())
        )
        conn.commit()

# Admin view: Access Log
roles_config = {}
if os.path.exists("roles.yaml"):
    with open("roles.yaml") as f:
        import yaml
        roles_config = yaml.safe_load(f)

admin_email = st.session_state.get("user_email")
role = roles_config.get("users", {}).get(admin_email, {}).get("role")

if role == "admin":
    st.subheader("Access Log")
    log_df = pd.read_sql("SELECT * FROM access_log ORDER BY timestamp DESC", conn)
    st.dataframe(log_df, use_container_width=True)
    csv_log = log_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Access Log", csv_log, file_name="access_log.csv", mime="text/csv")

    if st.button("Clear Access Log"):
        conn.execute("DELETE FROM access_log")
        conn.commit()
        st.success("Access log cleared.")

conn.close()
