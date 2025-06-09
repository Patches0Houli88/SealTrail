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

# --- Load user info ---
user_email = st.session_state.get("user_email", "")
user_role = st.session_state.get("user_role", "guest")

# --- Load Data ---
def load_data():
    try:
        return pd.read_sql("SELECT rowid, * FROM equipment", conn)
    except:
        return pd.DataFrame()

df = load_data()

# --- Admin: Add Column ---
if user_role == "admin":
    st.subheader("🔧 Admin Tools")
    with st.expander("➕ Add New Column"):
        new_col_name = st.text_input("Column name", key="add_column_name")
        new_col_type = st.selectbox("Column type", ["TEXT", "INTEGER", "REAL"], key="add_column_type")
        if st.button("Add Column", key="add_column_btn"):
            try:
                cursor.execute(f"ALTER TABLE equipment ADD COLUMN {new_col_name} {new_col_type}")
                timestamp = datetime.utcnow().isoformat()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        timestamp TEXT, action TEXT, user TEXT, detail TEXT
                    )
                """)
                cursor.execute("INSERT INTO audit_log VALUES (?, ?, ?, ?)",
                               (timestamp, "Add Column", user_email, f"{new_col_name} ({new_col_type})"))
                conn.commit()
                st.success(f"Column `{new_col_name}` added.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add column: {e}")

# --- Add New Item ---
if not df.empty:
    st.subheader("Add New Item")
    col_names = df.columns.drop("rowid")
    new_data = {}
    cols = st.columns(len(col_names))

    for i, col in enumerate(col_names):
        unique = df[col].dropna().unique().tolist()
        if 1 < len(unique) < 20:
            new_data[col] = cols[i].selectbox(col, unique + ["<Other>"], key=f"add_{col}")
            if new_data[col] == "<Other>":
                new_data[col] = cols[i].text_input(f"Enter {col}", key=f"custom_{col}")
        else:
            new_data[col] = cols[i].text_input(col, key=f"input_{col}")

    if st.button("Add to Inventory"):
        values = tuple(new_data[col] for col in col_names)
        placeholders = ', '.join('?' for _ in values)
        sql = f"INSERT INTO equipment ({', '.join(col_names)}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        st.success("Item added!")
        st.rerun()

# --- Edit & Delete ---
st.subheader("Edit & Delete Items")
if df.empty:
    st.info("No data available.")
else:
    filter_col = st.selectbox("Filter by column", df.columns.drop("rowid"))
    filter_val = st.text_input("Contains:")

    view_df = df.copy()
    if filter_val:
        view_df = df[df[filter_col].astype(str).str.contains(filter_val)]

    st.markdown("### Editable Table")
    edited = st.data_editor(
        view_df.drop(columns="rowid"),
        num_rows="dynamic",
        use_container_width=True,
        key="editor",
        disabled=["rowid"]
    )

    if st.button("Save Changes"):
        cursor.execute("DELETE FROM equipment")
        edited.to_sql("equipment", conn, if_exists="append", index=False)
        conn.commit()
        st.success("Changes saved.")
        st.rerun()

    st.markdown("### Delete Rows")
    selected_ids = st.multiselect("Select items by ID to delete", df["rowid"].tolist(), key="delete_rowid")
    if st.button("Delete Selected") and selected_ids:
        cursor.executemany("DELETE FROM equipment WHERE rowid = ?", [(i,) for i in selected_ids])
        conn.commit()
        st.success("Selected rows deleted.")
        st.rerun()

conn.close()
