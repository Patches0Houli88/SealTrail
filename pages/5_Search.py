import streamlit as st
import pandas as pd
import os
from datetime import datetime
import shared_utils as su

st.set_page_config(page_title="Global Search & Filters", layout="wide")
st.title("🔎 Global Search & Filters")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = su.get_db_path()
active_table = su.get_active_table()

st.sidebar.markdown(f"Role: {user_role}  \n📧 Email: {user_email}")
st.sidebar.info(f"Active Table: `{active_table}`")

# --- Load Data Centrally ---
equipment_df = su.load_equipment()
maintenance_df = su.load_maintenance()
scans_df = su.load_scans()

# --- Global Search ---
st.subheader("🔍 Global Search")
search_term = st.text_input("Enter keyword to search across all tables:")

if search_term:
    st.markdown("### Search Results:")
    found_any = False

    # Equipment Search
    if not equipment_df.empty:
        results = equipment_df[equipment_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
        if not results.empty:
            st.write("#### Equipment Matches")
            st.dataframe(results, use_container_width=True)
            found_any = True

    # Maintenance Search
    if not maintenance_df.empty:
        results = maintenance_df[maintenance_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
        if not results.empty:
            st.write("#### Maintenance Matches")
            st.dataframe(results, use_container_width=True)
            found_any = True

    # Scans Search
    if not scans_df.empty:
        results = scans_df[scans_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
        if not results.empty:
            st.write("#### Scan Matches")
            st.dataframe(results, use_container_width=True)
            found_any = True

    if not found_any:
        st.warning("No matches found across any tables.")

# --- Divider ---
st.divider()
st.subheader("Advanced Filters")

# --- Equipment Filters ---
if not equipment_df.empty:
    with st.expander("Equipment Filters"):
        cols_lower = {col.lower(): col for col in equipment_df.columns}
        type_col = cols_lower.get("equipment_type") or cols_lower.get("type")
        status_col = cols_lower.get("status")
        location_col = cols_lower.get("location")

        f1, f2, f3 = st.columns(3)
        type_choice = f1.selectbox("Type", ["All"] + sorted(equipment_df[type_col].dropna().unique().tolist()) if type_col else ["All"])
        status_choice = f2.selectbox("Status", ["All"] + sorted(equipment_df[status_col].dropna().unique().tolist()) if status_col else ["All"])
        location_choice = f3.selectbox("Location", ["All"] + sorted(equipment_df[location_col].dropna().unique().tolist()) if location_col else ["All"])

        filtered = equipment_df.copy()
        if type_choice != "All" and type_col:
            filtered = filtered[filtered[type_col] == type_choice]
        if status_choice != "All" and status_col:
            filtered = filtered[filtered[status_col] == status_choice]
        if location_choice != "All" and location_col:
            filtered = filtered[filtered[location_col] == location_choice]

        st.dataframe(filtered, use_container_width=True)
        st.download_button("Export Equipment Results", filtered.to_csv(index=False), "equipment_results.csv")

# --- Maintenance Filters ---
if not maintenance_df.empty:
    with st.expander("Maintenance Filters"):
        techs = ["All"] + sorted(maintenance_df["technician"].dropna().unique().tolist())
        tech_choice = st.selectbox("Technician", techs)
        date_range = st.date_input("Maintenance Date Range", [datetime.today().replace(day=1), datetime.today()])

        filtered = maintenance_df.copy()
        filtered["date"] = pd.to_datetime(filtered["date"], errors="coerce")
        if tech_choice != "All":
            filtered = filtered[filtered["technician"] == tech_choice]
        filtered = filtered[
            (filtered["date"] >= pd.to_datetime(date_range[0])) &
            (filtered["date"] <= pd.to_datetime(date_range[1]))
        ]

        st.dataframe(filtered, use_container_width=True)
        st.download_button("Export Maintenance Results", filtered.to_csv(index=False), "maintenance_results.csv")

# --- Scan Filters ---
if not scans_df.empty:
    with st.expander("Scan Filters"):
        users = ["All"] + sorted(scans_df["scanned_by"].dropna().unique().tolist())
        locations = ["All"] + sorted(scans_df["location"].dropna().unique().tolist())

        c1, c2 = st.columns(2)
        user_choice = c1.selectbox("User", users)
        loc_choice = c2.selectbox("Location", locations)
        scan_range = st.date_input("Scan Date Range", [datetime.today().replace(day=1), datetime.today()])

        filtered = scans_df.copy()
        if user_choice != "All":
            filtered = filtered[filtered["scanned_by"] == user_choice]
        if loc_choice != "All":
            filtered = filtered[filtered["location"] == loc_choice]
        filtered = filtered[
            (filtered["timestamp"].dt.date >= scan_range[0]) &
            (filtered["timestamp"].dt.date <= scan_range[1])
        ]

        st.dataframe(filtered, use_container_width=True)
        st.download_button("Export Scan Results", filtered.to_csv(index=False), "scans_results.csv")
