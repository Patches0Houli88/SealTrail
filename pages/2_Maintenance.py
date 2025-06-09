import streamlit as st
import sqlite3
import pandas as pd
import os

st.title("Maintenance Log")

db_path = st.session_state.get("db_path")
if not db_path or not os.path.exists(db_path):
    st.warning("No database selected. Please select one on the main page.")
    st.stop()

st.subheader(f"Current Database: {os.path.basename(db_path)}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS maintenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER,
    date TEXT,
    performed_by TEXT,
    notes TEXT
)
""")
conn.commit()

df = pd.read_sql("SELECT * FROM maintenance", conn)
if not df.empty:
    st.dataframe(df)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Maintenance Log", csv, "maintenance_log.csv", mime="text/csv")
else:
    st.info("No maintenance records yet.")

with st.form("Add Maintenance Entry"):
    equipment_id = st.text_input("Equipment ID")
    date = st.date_input("Date")
    performed_by = st.text_input("Performed By")
    notes = st.text_area("Notes")
    submitted = st.form_submit_button("Add Entry")
    if submitted:
        cursor.execute("INSERT INTO maintenance (equipment_id, date, performed_by, notes) VALUES (?, ?, ?, ?)",
                       (equipment_id, date.strftime("%Y-%m-%d"), performed_by, notes))
        conn.commit()
        st.success("Entry added.")

conn.close()
