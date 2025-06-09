import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner
import sqlite3
import pandas as pd

st.title("Barcode Scanner")
st.write("Scan equipment codes using your camera. If unsupported, manually enter a code.")

# Ensure active database
if "db_path" not in st.session_state:
    st.warning("No database selected. Please upload data first in the main page.")
    st.stop()

db_path = st.session_state.db_path
user_email = st.session_state.get("user_email", "unknown")

# Start scan button
scan_mode = st.button("Start Scan")
scanned = qrcode_scanner(key="scanner") if scan_mode else None
scanner_active = scanned is not None

if scan_mode:
    st.info("Scanner active... waiting for input")

if scanner_active:
    st.success("Scanner is active and working.")

# Manual fallback input
manual_code = st.text_input("Or manually enter a code")

code_to_save = scanned or manual_code

# Table and key selection
table_options = ["scanned_items", "equipment", "maintenance_log"]
selected_table = st.selectbox("Select table to save scan to", table_options)
key_column = st.text_input("Key column to match in table (optional, e.g., asset_id or serial_number)")

if code_to_save and selected_table:
    st.success(f"Code Captured: {code_to_save}")

    conn = sqlite3.connect(db_path)
    try:
        if selected_table == "scanned_items":
            conn.execute('''CREATE TABLE IF NOT EXISTS scanned_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scanned_by TEXT
            )''')
            conn.execute("INSERT INTO scanned_items (code, scanned_by) VALUES (?, ?)", (code_to_save, user_email))

        elif selected_table in ["equipment", "maintenance_log"]:
            if key_column:
                cursor = conn.execute(f"SELECT rowid FROM {selected_table} WHERE {key_column} = ? LIMIT 1", (code_to_save,))
                match = cursor.fetchone()
                if match:
                    rowid = match[0]
                    try:
                        conn.execute(f"ALTER TABLE {selected_table} ADD COLUMN scanned_code TEXT")
                    except:
                        pass  # Column may already exist
                    conn.execute(f"UPDATE {selected_table} SET scanned_code = ? WHERE rowid = ?", (code_to_save, rowid))
                    st.success(f"Updated {selected_table}.{key_column} = {code_to_save}")
                else:
                    st.warning("No matching row found for key.")
            else:
                try:
                    conn.execute(f"ALTER TABLE {selected_table} ADD COLUMN scanned_code TEXT")
                except:
                    pass
                conn.execute(f"UPDATE {selected_table} SET scanned_code = ? WHERE rowid = (SELECT rowid FROM {selected_table} WHERE scanned_code IS NULL LIMIT 1)", (code_to_save,))
                st.info("Saved code to first available row.")

        conn.commit()
    except Exception as e:
        st.error(f"Failed to save scan: {e}")
    finally:
        conn.close()

# Show recent scans + filter/export
with sqlite3.connect(db_path) as conn:
    st.subheader("View & Export Scan History")
    try:
        scans_df = pd.read_sql("SELECT * FROM scanned_items ORDER BY scanned_at DESC", conn)

        # Filter options
        with st.expander("Filter Scan Logs"):
            unique_users = scans_df["scanned_by"].dropna().unique().tolist()
            user_filter = st.multiselect("Filter by user", unique_users)
            date_range = st.date_input("Date range", [])

            if user_filter:
                scans_df = scans_df[scans_df["scanned_by"].isin(user_filter)]
            if len(date_range) == 2:
                scans_df = scans_df[(pd.to_datetime(scans_df["scanned_at"]).dt.date >= date_range[0]) &
                                    (pd.to_datetime(scans_df["scanned_at"]).dt.date <= date_range[1])]

        st.dataframe(scans_df)

        if not scans_df.empty:
            csv = scans_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Filtered Scan History", csv, "scan_history.csv", mime="text/csv")
        else:
            st.info("No scan records found with current filters.")

    except:
        st.info("No scan log table found yet.")

    # Attempt to match scanned codes with equipment table
    st.subheader("Matching Equipment Records")
    try:
        equipment_df = pd.read_sql("SELECT * FROM equipment", conn)
        if not scans_df.empty:
            matched_df = scans_df.merge(equipment_df, left_on="code", right_on=key_column if key_column else "code", how="left")
            st.dataframe(matched_df)

            csv_matches = matched_df.to_csv(index=False).encode("utf-8")
            st.download_button("Export Matched Equipment Data", csv_matches, "matched_equipment.csv", mime="text/csv")
    except:
        st.info("Equipment table not found or key mismatch.")

# Scan summary stats
    st.subheader("Scan Summary")
    try:
        if not scans_df.empty:
            summary = scans_df.groupby("scanned_by")["code"].count().reset_index(name="total_scans")
            st.dataframe(summary)
    except:
        pass
