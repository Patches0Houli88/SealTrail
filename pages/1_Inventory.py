import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="Inventory", layout="wide")
st.title("📦 Inventory Management")

# --- Ensure DB is selected ---
if "db_path" not in st.session_state:
    st.error("No database selected.")
    st.stop()

conn = sqlite3.connect(st.session_state.db_path)

# --- Load inventory table ---
try:
    df = pd.read_sql("SELECT rowid AS id, * FROM equipment", conn)
    df.set_index("id", inplace=True)
except:
    st.warning("No inventory data found.")
    conn.close()
    st.stop()

# --- Editable Table with Filters ---
st.subheader("Edit Inventory")
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    key="edit_table",
    column_config={
        col: st.column_config.Column(label=col, width="medium") for col in df.columns
    },
    hide_index=False,
)

# --- Save Changes ---
if st.button("💾 Save Changes"):
    try:
        edited_df.reset_index(drop=True, inplace=True)
        edited_df.to_sql("equipment", conn, if_exists="replace", index=False)
        st.success("Changes saved successfully.")
    except Exception as e:
        st.error(f"Failed to save: {e}")

# --- Deletion Logic ---
selected_rows = st.multiselect("Select rows to delete by ID", options=df.index.tolist())

if st.button("🗑️ Delete Selected"):
    if not selected_rows:
        st.warning("No rows selected.")
    else:
        updated_df = df.drop(index=selected_rows)
        updated_df.reset_index(drop=True, inplace=True)
        updated_df.to_sql("equipment", conn, if_exists="replace", index=False)
        st.success(f"Deleted {len(selected_rows)} row(s).")
        st.rerun()

# --- Manual Add Section ---
st.subheader("➕ Add New Inventory Item")
with st.form("add_form", clear_on_submit=True):
    new_row = {}
    for col in df.columns:
        unique_vals = sorted(df[col].dropna().astype(str).unique())
        if len(unique_vals) <= 20:
            new_row[col] = st.selectbox(col, options=unique_vals + ["Other"], key=col)
        else:
            new_row[col] = st.text_input(col, key=col)

    submitted = st.form_submit_button("Add")
    if submitted:
        new_df = pd.DataFrame([new_row])
        combined = pd.concat([df.reset_index(drop=True), new_df], ignore_index=True)
        combined.to_sql("equipment", conn, if_exists="replace", index=False)
        st.success("New item added.")
        st.rerun()

conn.close()
