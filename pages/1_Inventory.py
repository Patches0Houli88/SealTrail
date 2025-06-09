import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Inventory", layout="wide")
st.title("Inventory Management")

if "db_path" not in st.session_state:
    st.warning("No database selected. Please choose one from the main page.")
    st.stop()

conn = sqlite3.connect(st.session_state.db_path)
cursor = conn.cursor()

# Load current user info
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")

# Load existing data
def load_data():
    try:
        return pd.read_sql("SELECT rowid, * FROM equipment", conn)
    except:
        return pd.DataFrame()

df = load_data()

# --- Add New Inventory Item ---
st.subheader("Add New Item")
with st.form("add_form"):
    if df.empty:
        st.info("No data found in inventory table to infer columns.")
        st.stop()

    col_names = df.columns.drop("rowid")
    new_values = {}
    col_layout = st.columns(len(col_names))

    for i, col in enumerate(col_names):
        unique_vals = df[col].dropna().unique().tolist()
        key_prefix = f"new_{col}_{i}"
        if 1 < len(unique_vals) < 20:
            new_values[col] = col_layout[i].selectbox(
                col, unique_vals + ["<Other>"], key=f"{key_prefix}_select"
            )
            if new_values[col] == "<Other>":
                new_values[col] = col_layout[i].text_input(
                    f"Enter custom {col}", key=f"{key_prefix}_input"
                )
        else:
            new_values[col] = col_layout[i].text_input(col, key=f"{key_prefix}_text")

    submitted = st.form_submit_button("Add to Inventory")
    if submitted:
        values = tuple(new_values[col] for col in col_names)
        placeholders = ', '.join('?' for _ in values)
        sql = f"INSERT INTO equipment ({', '.join(col_names)}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        st.success("Item added!")
        st.rerun()

# --- Edit Inventory ---
st.subheader("Edit Items")
if df.empty:
    st.info("No data available to edit.")
else:
    st.markdown("### Filter Inventory")
    filter_col = st.selectbox("Select column to filter by", df.columns.drop("rowid"))
    filter_value = st.text_input("Filter value contains:")

    if filter_value:
        filtered_df = df[df[filter_col].astype(str).str.contains(filter_value, na=False)]
    else:
        filtered_df = df.copy()

    editable_df = st.data_editor(
        filtered_df.drop(columns="rowid"),
        num_rows="dynamic",
        use_container_width=True,
        key="editor"
    )

    if st.button("Save Changes"):
        cursor.execute("DELETE FROM equipment")
        editable_df.to_sql("equipment", conn, if_exists="append", index=False)
        conn.commit()
        st.success("Changes saved.")
        st.rerun()

# --- Delete Items ---
st.subheader("Delete Items")
if not df.empty:
    selected_rows = st.multiselect("Select rows to delete", df["rowid"].tolist())
    if st.button("Delete Selected") and selected_rows:
        cursor.executemany("DELETE FROM equipment WHERE rowid = ?", [(i,) for i in selected_rows])
        conn.commit()
        st.success("Selected items deleted.")
        st.rerun()

# --- Add Column (Admin Only) ---
if user_role == "admin":
    st.subheader("Add Column to Inventory Table")
    with st.form("add_column_form"):
        new_col_name = st.text_input("New Column Name")
        new_col_type = st.selectbox("Data Type", ["TEXT", "INTEGER", "REAL", "BLOB"])
        add_col_submit = st.form_submit_button("Add Column")

    if add_col_submit and new_col_name:
        try:
            cursor.execute(f"ALTER TABLE equipment ADD COLUMN {new_col_name} {new_col_type}")
            conn.commit()
            st.success(f"Added column: {new_col_name} ({new_col_type})")

            # Log to audit
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    timestamp TEXT,
                    user TEXT,
                    action TEXT,
                    details TEXT
                )
            """)
            cursor.execute(
                "INSERT INTO audit_log (timestamp, user, action, details) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), user_email, "ADD_COLUMN", f"{new_col_name} ({new_col_type})")
            )
            conn.commit()
            st.rerun()
        except Exception as e:
            st.error(f"Failed to add column: {e}")

conn.close()
