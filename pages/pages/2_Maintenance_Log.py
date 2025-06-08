import streamlit as st
import sqlite3
import pandas as pd

st.title("🛠️ Maintenance Log")

if "db_path" not in st.session_state:
    st.warning("🔐 Please log in first from the homepage.")
    st.stop()

conn = sqlite3.connect(st.session_state.db_path)
conn.execute("""
CREATE TABLE IF NOT EXISTS maintenance (
    maintenance_id INTEGER PRIMARY KEY,
    equipment_id INTEGER,
    maintenance_type TEXT,
    maintenance_date TEXT,
    performed_by TEXT,
    description TEXT,
    next_scheduled TEXT
)
""")
conn.commit()

df = pd.read_sql("SELECT * FROM maintenance", conn)
st.dataframe(df)

st.subheader("➕ Log New Maintenance")
with st.form("maintenance_form"):
    equipment_id = st.number_input("Equipment ID", step=1)
    maint_type = st.selectbox("Maintenance Type", ["Preventive", "Corrective"])
    maint_date = st.date_input("Maintenance Date")
    performed_by = st.text_input("Performed By")
    description = st.text_area("Description")
    next_scheduled = st.date_input("Next Scheduled")
    submit = st.form_submit_button("Add")

    if submit:
        conn.execute(
            "INSERT INTO maintenance (equipment_id, maintenance_type, maintenance_date, performed_by, description, next_scheduled) VALUES (?, ?, ?, ?, ?, ?)",
            (equipment_id, maint_type, maint_date.isoformat(), performed_by, description, next_scheduled.isoformat())
        )
        conn.commit()
        st.success("Maintenance log added.")
