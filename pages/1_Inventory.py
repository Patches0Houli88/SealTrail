import streamlit as st
import sqlite3
import pandas as pd
import os

st.title("Inventory Management")

if "db_path" not in st.session_state:
    st.warning("Please log in from the homepage.")
    st.stop()

st.caption(f"Current Database: {os.path.basename(st.session_state.db_path)}")

conn = sqlite3.connect(st.session_state.db_path)
conn.execute("""
CREATE TABLE IF NOT EXISTS equipment (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number TEXT,
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

st.subheader("Filter Inventory")
search = st.text_input("Search serial number, model, or notes")

col1, col2 = st.columns(2)
with col1:
    selected_type = st.selectbox("Equipment Type", ["All"] + sorted(df["type"].dropna().unique().tolist())) if "type" in df.columns else None
with col2:
    selected_status = st.selectbox("Status", ["All"] + sorted(df["status"].dropna().unique().tolist())) if "status" in df.columns else None

filtered_df = df.copy()
if selected_type and selected_type != "All":
    filtered_df = filtered_df[filtered_df["type"] == selected_type]
if selected_status and selected_status != "All":
    filtered_df = filtered_df[filtered_df["status"] == selected_status]
if search:
    filtered_df = filtered_df[
        filtered_df["serial_number"].str.contains(search, case=False, na=False) |
        filtered_df.get("model", pd.Series(dtype=str)).astype(str).str.contains(search, case=False, na=False) |
        filtered_df.get("notes", pd.Series(dtype=str)).astype(str).str.contains(search, case=False, na=False)
    ]

st.subheader("Filtered Inventory Table")
st.data_editor(filtered_df, use_container_width=True)

csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button("Download Filtered Inventory", csv, file_name="filtered_inventory.csv", mime="text/csv")

if st.button("Save Changes to Database"):
    filtered_df.to_sql("equipment", conn, if_exists="replace", index=False)
    st.success("Changes saved to database.")

conn.close()
