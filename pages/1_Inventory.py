import streamlit as st
import pandas as pd
import sqlite3

st.title("Inventory")

# Display active DB
if "db_path" not in st.session_state:
    st.warning("No active database. Please upload a file first.")
    st.stop()

st.markdown(f"Using Database: `{st.session_state.selected_db}`")

# Load inventory
conn = sqlite3.connect(st.session_state.db_path)
try:
    df = pd.read_sql("SELECT * FROM equipment", conn)
except Exception as e:
    st.error(f"Error loading inventory: {e}")
    conn.close()
    st.stop()
conn.close()

# Show filters only for existing columns
st.subheader("Filter Inventory")
if df.empty:
    st.info("No data available.")
    st.stop()

# Dynamically offer filters
col1, col2 = st.columns(2)

if "type" in df.columns:
    with col1:
        selected_type = st.selectbox("Equipment Type", ["All"] + sorted(df["type"].dropna().unique().tolist()))
        if selected_type != "All":
            df = df[df["type"] == selected_type]

if "status" in df.columns:
    with col2:
        selected_status = st.selectbox("Status", ["All"] + sorted(df["status"].dropna().unique().tolist()))
        if selected_status != "All":
            df = df[df["status"] == selected_status]

st.subheader("Inventory Table")
st.dataframe(df)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Filtered Inventory", csv, file_name="filtered_inventory.csv", mime="text/csv")
