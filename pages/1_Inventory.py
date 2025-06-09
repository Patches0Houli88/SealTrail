import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Inventory", layout="wide")
st.title("Inventory Management")

if "db_path" not in st.session_state:
    st.warning("No database selected. Please choose one from the main page.")
    st.stop()

conn = sqlite3.connect(st.session_state.db_path)
cursor = conn.cursor()

# Ensure audit log exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT,
    column_name TEXT,
    timestamp TEXT,
    user_email TEXT
)
""")

# Load data
def load_data():
    try:
        df = pd.read_sql("SELECT rowid, * FROM equipment", conn)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- Add New Item ---
st.subheader("Add New Inventory Item")
with st.form("add_form"):
    if df.empty:
        st.info("No data found in inventory table to infer columns.")
    else:
        col_names = df.columns.drop("rowid")
        new_values = {}
        col_layout = st.columns(len(col_names))

        for i, col in enumerate(col_names):
            unique_vals = df[col].dropna().unique().tolist()
            if 1 < len(unique_vals) < 20:
                new_values[col] = col_layout[i].selectbox(col, unique_vals + ["<Other>"])
                if new_values[col] == "<Other>":
                    new_values[col] = col_layout[i].text_input(f"Enter custom {col}", key=f"custom_{col}")
            else:
                new_values[col] = col_layout[i].text_input(col, key=f"input_{col}")

        submitted = st.form_submit_button("Add to Inventory")
        if submitted:
            values = tuple(new_values[col] for col in col_names)
            placeholders = ", ".join("?" for _ in values)
            sql = f"INSERT INTO equipment ({', '.join(col_names)}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            conn.commit()
            st.success("Item added.")
            st.rerun()

# --- Edit Items ---
st.subheader("Edit Items")
if df.empty:
    st.info("No data available to edit.")
else:
    st.markdown("### Filter Inventory")
    filter_col = st.selectbox("Filter column", df.columns.drop("rowid"))
    filter_value = st.text_input("Value contains:")

    if filter_value:
        filtered_df = df[df[filter_col].astype(str).str.contains(filter_value, na=False)]
    else:
        filtered_df = df.copy()

    editable_df = st.data_editor(
        filtered_df.drop(columns="rowid"),
        use_container_width=True,
        num_rows="dynamic",
        column_config={col: st.column_config.Column(label=col, filter=True) for col in filtered_df.columns if col != "rowid"}
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
    delete_ids = st.multiselect("Select row IDs to delete", df["rowid"].tolist())
    if st.button("Delete Selected") and delete_ids:
        cursor.executemany("DELETE FROM equipment WHERE rowid = ?", [(i,) for i in delete_ids])
        conn.commit()
        st.success("Selected items deleted.")
        st.rerun()

# --- Admin Only: Add Column ---
if st.session_state.get("user_role") == "admin":
    st.subheader("Add New Column")
    with st.form("add_column_form"):
        new_col_name = st.text_input("Column name")
        new_col_type = st.selectbox("Column type", ["TEXT", "INTEGER", "REAL"])
        if st.form_submit_button("Add Column"):
            if new_col_name:
                try:
                    cursor.execute(f"ALTER TABLE equipment ADD COLUMN {new_col_name} {new_col_type}")
                    conn.commit()
                    cursor.execute("INSERT INTO audit_log (action, column_name, timestamp, user_email) VALUES (?, ?, ?, ?)",
                                   ("add_column", new_col_name, datetime.utcnow().isoformat(), st.session_state.user_email))
                    conn.commit()
                    st.success(f"Column '{new_col_name}' added.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

conn.close()
