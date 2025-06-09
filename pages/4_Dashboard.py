import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from io import BytesIO
from fpdf import FPDF
import os

st.set_page_config(page_title="Full Dashboard", layout="wide")
st.title("Equipment Dashboard")

# --- Get user role and email ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")

st.sidebar.markdown(f" Role: {user_role} | Email: {user_email}")

if "user_email" not in st.session_state or "user_role" not in st.session_state:
    st.error("User not recognized. Please go to the main page and log in again.")
    st.stop()

# --- Connect to DB ---
DB_PATH = st.session_state.get("db_path", None)
if not DB_PATH or not os.path.exists(DB_PATH):
    st.error("No dashboard loaded. Please log in and select a dashboard.")
    st.stop()

conn = sqlite3.connect(DB_PATH)

# --- Load Data ---
try:
    equipment_df = pd.read_sql_query("SELECT * FROM equipment", conn)
except:
    equipment_df = pd.DataFrame()

st.title("📊 Inventory Dashboard")

# --- KPI Cards ---
st.subheader("Overview")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Items", len(equipment_df))

if "status" in equipment_df.columns:
    with col2:
        st.metric("Active", equipment_df[equipment_df["status"].str.lower() == "active"].shape[0])
    with col3:
        st.metric("In Repair", equipment_df[equipment_df["status"].str.lower() == "in repair"].shape[0])
else:
    with col2:
        st.metric("Active", 0)
    with col3:
        st.metric("In Repair", 0)

# --- Chart: Equipment by Status ---
st.subheader("Equipment Status Distribution")
if "status" in equipment_df.columns:
    try:
        status_counts = equipment_df["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]

        status_chart = (
            alt.Chart(status_counts)
            .mark_bar()
            .encode(
                x=alt.X("status:N", title="Status"),
                y=alt.Y("count:Q", title="Count"),
                color="status:N",
                tooltip=["status:N", "count:Q"]
            )
            .properties(height=300)
        )
        st.altair_chart(status_chart, use_container_width=True)
    except Exception as e:
        st.error(f"Could not generate chart: {e}")
else:
    st.info("No 'status' column found for visualization.")

conn.close()
