import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Maintenance Logs", layout="wide")
st.title("🛠 Maintenance Log")

# --- Session Validation ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = st.session_state.get("db_path", None)
active_table = st.session_state.get("active_table", "equipment")

st.sidebar.markdown(f"Role: {user_role} | Email: {user_email}")
st.markdown(f"**Linked to Table:** `{active_table}`")

if not db_path or not os.path.exists(db_path):
    st.error("No database found. Please load one from the main page.")
    st.stop()

# --- Load Equipment Items for Linking ---
conn = sqlite3.connect(db_path)
try:
    items_df = pd.read_sql(f"SELECT rowid, * FROM {active_table}", conn)
    item_options = items_df["rowid"].astype(str) + " | " + items_df[items_df.columns[1]].astype(str)
except Exception as e:
    st.error(f"Could not load items from `{active_table}`: {e}")
    item_options = []

# --- Display Existing Maintenance Log ---
try:
    log_df = pd.read_sql("SELECT * FROM maintenance_log", conn)
    if not log_df.empty:
        st.subheader("📜 Maintenance History")
        st.dataframe(log_df, use_container_width=True)
        csv = log_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Log", csv, "maintenance_log.csv", mime="text/csv")
    else:
        st.info("No maintenance logs yet.")
except:
    st.info("No maintenance_log table yet.")
finally:
    conn.close()

# --- Add New Maintenance Entry ---
st.subheader("➕ Add Maintenance Record")
with st.form("add_maintenance"):
    selected_equipment = st.selectbox("Link to Equipment", item_options, index=0 if item_options else None)
    description = st.text_area("Description of Work")
    date_performed = st.date_input("Date Performed", value=datetime.today())
    technician = st.text_input("Technician Name")
    submit_log = st.form_submit_button("Save Record")

if submit_log and selected_equipment and description:
    equipment_id = selected_equipment.split(" | ")[0]
    try:
        conn = sqlite3.connect(db_path)
        conn.execute('''CREATE TABLE IF NOT EXISTS maintenance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT,
            description TEXT,
            date TEXT,
            technician TEXT,
            table_link TEXT,
            logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('''
            INSERT INTO maintenance_log (equipment_id, description, date, technician, table_link)
            VALUES (?, ?, ?, ?, ?)
        ''', (equipment_id, description, str(date_performed), technician, active_table))
        conn.commit()
        st.success("✅ Maintenance record saved.")
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        conn.close()
        st.rerun()
