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

# Load data
def load_data():
    try:
        return pd.read_sql("SELECT rowid, * FROM equipment", conn)
    except:
        return pd.DataFrame()

df = load_data()

# --- Admin-only: Add Column ---
user_email = st.session_state.get("user_email", "")
user_role = st.session_state.get("user_role", "guest")

if user_role == "admin":
    st.subheader("🔧 Admin: Modify Columns")
    with st.expander("➕ Add New Column"):
        new_col_name = st.text_input("New column name", key="new_col_name_input")
        col_type = st.selectbox("Data type", ["TEXT", "INTEGER", "REAL"], key="col_type_input")
        if st.button("Add Column", key="add_column_btn") and new_col_name:
            try:
                cursor.execute(f"ALTER TABLE equipment ADD COLUMN {new_col_name} {col_type}")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        timestamp TEXT, action TEXT, user TEXT, detail TEXT
                    )
                """)
                timestamp = datetime.utcnow().isoformat()
                cursor.execute("INSERT INTO audit_log VALUES (?, ?, ?, ?)",
                               (timestamp, "Add Column", user_email, f"{new_col_name} ({col_type})"))
                conn.commit()
                st.success(f"Column `{new_col_name}` added.")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding column: {e}")

# --- Add New Item ---
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
        if 1 < len(unique_vals) < 20:
            new_values[col] = col_layout[i].selectbox(col, unique_vals + ["<Other>"], key=f"add_{col}")
            if new_values[col] == "<Other>":
                new_values[col] = col_layout[i].text_input(f"Enter custom {col}", key=f"custom_{col}")
        else:
            new_values[col] = col_layout[i].text_input(col, key=f"text_{col}")

    if st.form_submit_button("Add to Inventory"):
        values = tuple(new_values[col] for col in col_names)
        placeholders = ', '.join('?' for _ in values)
        sql = f"INSERT INTO equipment ({', '.join(col_names)}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        st.success("Item added!")
        st.rerun()

# --- Edit Items ---
st.subheader("Edit Items")
if not df.empty:
    st.markdown("### Filter Inventory")
    filter_col = st.selectbox("Select column to filter by", df.columns.drop("rowid"), key="filter_col")
    filter_value = st.text_input("Filter value contains:", key="filter_val")

    if filter_value:
        filtered_df = df[df[filter_col].astype(str).str.contains(filter_value, na=False)]
    else:
        filtered_df = df.copy()

    # Assign compatible widgets
    column_config = {}
    for col in filtered_df.columns:
        if col == "rowid":
            continue
        if pd.api.types.is_integer_dtype(filtered_df[col]):
            column_config[col] = st.column_config.NumberColumn(col)
        elif pd.api.types.is_float_dtype(filtered_df[col]):
            column_config[col] = st.column_config.NumberColumn(col, format="%.2f")
        else:
            column_config[col] = st.column_config.TextColumn(col)

    editable_df = st.data_editor(
        filtered_df.drop(columns="rowid"),
        column_config=column_config,
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
    delete_ids = st.multiselect("Select items to delete:", df["rowid"].tolist(), key="delete_ids")
    if st.button("Delete Selected") and delete_ids:
        cursor.executemany("DELETE FROM equipment WHERE rowid = ?", [(i,) for i in delete_ids])
        conn.commit()
        st.success("Selected items deleted.")
        st.rerun()

conn.close()
