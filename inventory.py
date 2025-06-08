import streamlit as st
import sqlite3
import pandas as pd

st.title("📋 Inventory Management")

if "db_path" not in st.session_state:
    st.warning("🔐 Please log in first from the homepage.")
    st.stop()

conn = sqlite3.connect(st.session_state.db_path)
conn.execute("""
CREATE TABLE IF NOT EXISTS equipment (
    equipment_id INTEGER PRIMARY KEY,
    serial_number TEXT UNIQUE,
    type TEXT,
    model TEXT,
    status TEXT,
    purchase_date TEXT,
    warranty_expiry TEXT,
    notes TEXT
)
""")
conn.commit()

df = pd.read_sql("SELECT * FROM equipment", conn)
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

if st.button("💾 Save Changes"):
    edited_df.to_sql("equipment", conn, if_exists="replace", index=False)
    st.success("Changes saved to database.")
