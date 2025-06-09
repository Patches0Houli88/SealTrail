import streamlit as st
import sqlite3
import pandas as pd
import os

st.title("Inventory Management")

# Validate DB
db_path = st.session_state.get("db_path")
if not db_path or not os.path.exists(db_path):
    st.warning("No database selected. Please select one on the main page.")
    st.stop()

st.subheader(f"Current Database: {os.path.basename(db_path)}")

conn = sqlite3.connect(db_path)
df = pd.read_sql("SELECT * FROM equipment", conn)

# Filter UI
if not df.empty:
    st.subheader("Filter Inventory")
    col1, col2 = st.columns(2)

    with col1:
        selected_type = st.selectbox("Equipment Type", ["All"] + sorted(df["type"].dropna().unique()))
    with col2:
        selected_status = st.selectbox("Status", ["All"] + sorted(df["status"].dropna().unique()))

    filtered_df = df.copy()
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["type"] == selected_type]
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df["status"] == selected_status]

    st.dataframe(filtered_df)

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Filtered Data", csv, "filtered_inventory.csv", mime="text/csv")
else:
    st.info("No equipment data found.")

conn.close()
