import streamlit as st
import sqlite3
import pandas as pd

st.title("Maintenance Log")

# Ensure DB
if "db_path" not in st.session_state:
    st.warning("No active database. Please upload a file in the main page.")
    st.stop()

db_path = st.session_state.db_path

# View existing log
conn = sqlite3.connect(db_path)
try:
    df = pd.read_sql("SELECT * FROM maintenance_log", conn)
    if not df.empty:
        st.subheader("Maintenance History")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Maintenance Log", csv, "maintenance_log.csv", mime="text/csv")
    else:
        st.info("No maintenance records yet.")
except:
    st.info("Maintenance log not found. Add an entry below to create it.")
finally:
    conn.close()

# Add maintenance entry
st.subheader("Add New Maintenance Record")
with st.form("maintenance_form"):
    equipment_id = st.text_input("Equipment ID")
    description = st.text_area("Work Done / Notes")
    date = st.date_input("Date Performed")
    technician = st.text_input("Technician")
    submitted = st.form_submit_button("Add Record")

if submitted and equipment_id and description:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS maintenance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT,
            description TEXT,
            date TEXT,
            technician TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute("INSERT INTO maintenance_log (equipment_id, description, date, technician) VALUES (?, ?, ?, ?)",
                     (equipment_id, description, str(date), technician))
        conn.commit()
        st.success("Maintenance record added.")
    except Exception as e:
        st.error(f"Error saving record: {e}")
    finally:
        conn.close()
