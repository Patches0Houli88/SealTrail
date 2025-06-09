import streamlit as st
import sqlite3
import pandas as pd
import yaml
import os
from datetime import datetime

st.set_page_config(page_title="Inventory", layout="wide")
st.title("Inventory Management")

# --- Check for active DB ---
if "db_path" not in st.session_state:
    st.warning("No database selected. Please choose one from the main page.")
    st.stop()

conn = sqlite3.connect(st.session_state.db_path)
cursor = conn.cursor()

# Fallback to load role if not already in session
if "user_role" not in st.session_state:
    user_email = st.session_state.get("user_email", "unknown@example.com")
    st.session_state.user_email = user_email  # ensure set
    if os.path.exists("roles.yaml"):
        with open("roles.yaml") as f:
            roles = yaml.safe_load(f)
        st.session_state.user_role = roles.get("users", {}).get(user_email, {}).get("role", "guest")

user_email = st.session_state.get("user_email", "")
user_role = st.session_state.user_role
st.caption(f"🔍 Role: {user_role} | Email: {user_email}")
# --- Load Data ---
def load_data():
    try:
        return pd.read_sql("SELECT rowid, * FROM equipment", conn)
    except:
        return pd.DataFrame()

df = load_data()

# --- Admin-only Column Add ---
if user_role == "admin":
    st.subheader("🔧 Admin Tools")
    with st.expander("➕ Add New Column"):
        new_col_name = st.text_input("Column name", key="admin_add_column")
        new_col_type = st.selectbox("Column type", ["TEXT", "INTEGER", "REAL"], key="admin_col_type")
        if st.button("Add Column") and new_col_name:
            try:
                cursor.execute(f"ALTER TABLE equipment ADD COLUMN {new_col_name} {new_col_type}")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        timestamp TEXT, action TEXT, user TEXT, detail TEXT
                    )
                """)
                cursor.execute("INSERT INTO audit_log VALUES (?, ?, ?, ?)",
                               (datetime.utcnow().isoformat(), "Add Column", user_email, f"{new_col_name} ({new_col_type})"))
                conn.commit()
                st.success(f"Column `{new_col_name}` added.")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding column: {e}")

# --- Add New Inventory Item ---
if not df.empty:
    st.subheader("Add New Item")
    col_names = df.columns.drop(["rowid", "selected"], errors="ignore")
    new_data = {}
    cols = st.columns(len(col_names))
    for i, col in enumerate(col_names):
        unique = df[col].dropna().unique().tolist()
        if 1 < len(unique) < 20:
            new_data[col] = cols[i].selectbox(col, unique + ["<Other>"], key=f"new_{col}")
            if new_data[col] == "<Other>":
                new_data[col] = cols[i].text_input(f"Enter {col}", key=f"custom_{col}")
        else:
            new_data[col] = cols[i].text_input(col, key=f"input_{col}")

    if st.button("Add to Inventory"):
        values = tuple(new_data[col] for col in col_names)
        placeholders = ', '.join('?' for _ in values)
        cursor.execute(f"INSERT INTO equipment ({', '.join(col_names)}) VALUES ({placeholders})", values)
        conn.commit()
        st.success("Item added!")
        st.rerun()

# --- Edit Table with Checkbox-based Delete ---
st.subheader("Edit & Delete Items")
if df.empty:
    st.info("No data available.")
else:
    filter_col = st.selectbox("Filter by column", df.columns.drop("rowid"))
    filter_val = st.text_input("Contains:")
    if filter_val:
        df = df[df[filter_col].astype(str).str.contains(filter_val, na=False)]

    # Add checkbox column
    df["selected"] = False

    editable_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_table",
        disabled=["rowid"]
    )

    if st.button("Save Changes"):
        cursor.execute("DELETE FROM equipment")
        editable_df.drop(columns=["rowid", "selected"]).to_sql("equipment", conn, if_exists="append", index=False)
        conn.commit()
        st.success("Changes saved.")
        st.rerun()

    if st.button("Delete Checked Rows"):
        to_delete = editable_df[editable_df["selected"] == True]["rowid"].tolist()
        if to_delete:
            cursor.executemany("DELETE FROM equipment WHERE rowid = ?", [(rid,) for rid in to_delete])
            conn.commit()
            st.success(f"Deleted {len(to_delete)} rows.")
            st.rerun()

conn.close()
