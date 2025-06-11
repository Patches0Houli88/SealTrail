import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Global Search & Filters", layout="wide")
st.title("🔎 Global Search & Filters")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = st.session_state.get("db_path")
active_table = st.session_state.get("active_table", "equipment")

st.sidebar.markdown(f"🔐 Role: {user_role}  \n📧 Email: {user_email}")

if not db_path or not os.path.exists(db_path):
    st.error("No database loaded. Please return to the main page.")
    st.stop()

# --- Load Tables Safely ---
conn = sqlite3.connect(db_path)
def load_table(name):
    try:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except:
        return pd.DataFrame()

equipment_df = load_table(active_table)
maintenance_df = load_table("maintenance_log")
scans_df = load_table("scanned_items")
conn.close()

# --- Search Section ---
st.subheader("🔍 Global Search")
search_term = st.text_input("Enter keyword to search across all tables:")

if search_term:
    st.markdown("### Search Results:")
    found_any = False

    # Search Equipment
    if not equipment_df.empty:
        equipment_results = equipment_df[equipment_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
        if not equipment_results.empty:
            st.write("#### Equipment Matches")
            st.dataframe(equipment_results, use_container_width=True)
            found_any = True

    # Search Maintenance
    if not maintenance_df.empty:
        maintenance_results = maintenance_df[maintenance_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
        if not maintenance_results.empty:
            st.write("#### Maintenance Matches")
            st.dataframe(maintenance_results, use_container_width=True)
            found_any = True

    # Search Scans
    if not scans_df.empty:
        scans_results = scans_df[scans_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
        if not scans_results.empty:
            st.write("#### Scan Matches")
            st.dataframe(scans_results, use_container_width=True)
            found_any = True

    if not found_any:
        st.warning("No matches found across any tables.")

# --- Advanced Filters ---
st.divider()
st.subheader("🧮 Advanced Filters")

# Equipment Filters
if not equipment_df.empty:
    with st.expander("🔧 Equipment Filters"):
        cols_lower = {col.lower(): col for col in equipment_df.columns}
        type_col = cols_lower.get("equipment_type") or cols_lower.get("type")
        status_col = cols_lower.get("status")
        location_col = cols_lower.get("location")

        f1, f2, f3 = st.columns(3)
        
        if type_col:
            type_choice = f1.selectbox("Type", ["All"] + sorted(equipment_df[type_col].dropna().unique().tolist()))
        else:
            type_choice = "All"

        if status_col:
            status_choice = f2.selectbox("Status", ["All"] + sorted(equipment_df[status_col].dropna().unique().tolist()))
        else:
            status_choice = "All"

        if location_col:
            location_choice = f3.selectbox("Location", ["All"] + sorted(equipment_df[location_col].dropna().unique().tolist()))
        else:
            location_choice = "All"

        filtered_equipment = equipment_df.copy()
        if type_choice != "All":
            filtered_equipment = filtered_equipment[filtered_equipment[type_col] == type_choice]
        if status_choice != "All":
            filtered_equipment = filtered_equipment[filtered_equipment[status_col] == status_choice]
        if location_choice != "All":
            filtered_equipment = filtered_equipment[filtered_equipment[location_col] == location_choice]

        st.dataframe(filtered_equipment, use_container_width=True)
        st.download_button("Export Equipment Results", filtered_equipment.to_csv(index=False), "equipment_results.csv")

# Maintenance Filters
if not maintenance_df.empty:
    with st.expander("🛠 Maintenance Filters"):
        techs = ["All"] + sorted(maintenance_df["technician"].dropna().unique().tolist())
        tech_choice = st.selectbox("Technician", techs)
        date_range = st.date_input("Maintenance Date Range", [datetime.today().replace(day=1), datetime.today()])

        filtered_maint = maintenance_df.copy()
        filtered_maint["date"] = pd.to_datetime(filtered_maint["date"], errors="coerce")
        if tech_choice != "All":
            filtered_maint = filtered_maint[filtered_maint["technician"] == tech_choice]
        filtered_maint = filtered_maint[(filtered_maint["date"] >= pd.to_datetime(date_range[0])) & (filtered_maint["date"] <= pd.to_datetime(date_range[1]))]

        st.dataframe(filtered_maint, use_container_width=True)
        st.download_button("Export Maintenance Results", filtered_maint.to_csv(index=False), "maintenance_results.csv")

# Scan Filters
if not scans_df.empty:
    with st.expander("📷 Scan Filters"):
        users = ["All"] + sorted(scans_df["scanned_by"].dropna().unique().tolist())
        locations = ["All"] + sorted(scans_df["location"].dropna().unique().tolist())

        c1, c2 = st.columns(2)
        user_choice = c1.selectbox("User", users)
        loc_choice = c2.selectbox("Location", locations)

        scan_range = st.date_input("Scan Date Range", [datetime.today().replace(day=1), datetime.today()])
        scans_df["timestamp"] = pd.to_datetime(scans_df["timestamp"], errors="coerce")

        filtered_scans = scans_df.copy()
        if user_choice != "All":
            filtered_scans = filtered_scans[filtered_scans["scanned_by"] == user_choice]
        if loc_choice != "All":
            filtered_scans = filtered_scans[filtered_scans["location"] == loc_choice]
        filtered_scans = filtered_scans[(filtered_scans["timestamp"] >= pd.to_datetime(scan_range[0])) & (filtered_scans["timestamp"] <= pd.to_datetime(scan_range[1]))]

        st.dataframe(filtered_scans, use_container_width=True)
        st.download_button("Export Scan Results", filtered_scans.to_csv(index=False), "scans_results.csv")
