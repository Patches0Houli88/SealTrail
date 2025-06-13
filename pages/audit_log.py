import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
import shared_utils as utils

st.set_page_config(page_title="Audit Log", layout="wide")
st.title("System Audit Log")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = utils.get_db_path()

st.sidebar.markdown(f"Role: {user_role}  \n Email: {user_email}")
st.sidebar.info(f"Database: `{db_path}`")

if user_role != "admin":
    st.warning("You do not have permission to access audit logs.")
    st.stop()

# --- Ensure audit_log table exists ---
conn = utils.load_connection()
conn.execute("""
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    action TEXT,
    user TEXT,
    detail TEXT
)
""")
conn.commit()
conn.close()

# --- Load Audit Log ---
log_df = utils.load_table("audit_log")

if log_df.empty:
    st.info("No audit log entries found.")
else:
    log_df["timestamp"] = pd.to_datetime(log_df["timestamp"], errors="coerce")
    log_df = log_df.sort_values("timestamp", ascending=False)

    st.dataframe(log_df, use_container_width=True)

    # Optional filters
    with st.expander("🔎 Filter Logs"):
        user_filter = st.selectbox("Filter by User", ["All"] + sorted(log_df["user"].dropna().unique().tolist()))
        action_filter = st.selectbox("Filter by Action", ["All"] + sorted(log_df["action"].dropna().unique().tolist()))
        start_date = st.date_input("Start Date", value=datetime.today().replace(day=1))
        end_date = st.date_input("End Date", value=datetime.today())

        filtered = log_df.copy()

        if user_filter != "All":
            filtered = filtered[filtered["user"] == user_filter]
        if action_filter != "All":
            filtered = filtered[filtered["action"] == action_filter]

        filtered = filtered[
            (filtered["timestamp"] >= pd.to_datetime(start_date)) &
            (filtered["timestamp"] <= pd.to_datetime(end_date))
        ]

        st.dataframe(filtered, use_container_width=True)

# --- Export Option ---
with st.expander("📤 Export Audit Log"):
    csv_data = log_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv_data, "audit_log.csv", mime="text/csv")
