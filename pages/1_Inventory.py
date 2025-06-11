import streamlit as st
import sqlite3
import pandas as pd
import yaml
import os
from datetime import datetime

st.set_page_config(page_title="Inventory", layout="wide")
st.title("📦 Inventory Management")

# --- Session Info ---
user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")
db_path = st.session_state.get("db_path", None)
active_table = st.session_state.get("active_table", "equipment")

st.sidebar.markdown(f"🔐 Role: {user_role} | 📧 Email: {user_email}")
st.sidebar.info(f"📦 Active Table: `{active_table}`")

if not db_path or not os.path.exists(db_path):
    st.error("No active database. Please return to the main page.")
    st.stop()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --- Load Data ---
def load_data():
    try:
        df = pd.read_sql(f"SELECT rowid, * FROM {active_table}", conn)
        if "equipment_id" in df.columns:
            df["equipment_id"] = df["equipment_id"].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- Template File ---
template_file = "templates.yaml"
if os.path.exists(template_file):
    with open(template_file) as f:
        templates = yaml.safe_load(f) or {}
else:
    templates = {}

table_key = f"{user_email}_{os.path.basename(db_path)}_{active_table}"
template = templates.get(table_key, {})

# --- Admin: Add Column ---
if user_role == "admin":
    st.subheader("🔧 Admin Tools")
    with st.expander("➕ Add New Column"):
        new_col = st.text_input("Column Name")
        col_type = st.selectbox("Column Type", ["TEXT", "INTEGER", "REAL"])
        if st.button("Add Column") and new_col:
            try:
                cursor.execute(f"ALTER TABLE {active_table} ADD COLUMN {new_col} {col_type}")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        timestamp TEXT, action TEXT, user TEXT, detail TEXT
                    )
                """)
                cursor.execute("INSERT INTO audit_log VALUES (?, ?, ?, ?)",
                    (datetime.utcnow().isoformat(), "Add Column", user_email, f"{new_col} ({col_type})"))
                conn.commit()
                st.success(f"Column `{new_col}` added.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add column: {e}")

# --- Add New Item Using Template ---
if not df.empty:
    st.subheader("➕ Add New Item")
    col_names = df.columns.drop(["rowid", "selected"], errors="ignore")
    new_data = {}

    cols = st.columns(len(col_names))
    for i, col in enumerate(col_names):
        unique_vals = df[col].dropna().unique().tolist()
        default = template.get(col, "")
        if 1 < len(unique_vals) < 20:
            new_data[col] = cols[i].selectbox(
                col, unique_vals + ["<Other>"],
                index=unique_vals.index(default) if default in unique_vals else 0,
                key=f"new_{col}"
            )
            if new_data[col] == "<Other>":
                new_data[col] = cols[i].text_input(f"Enter {col}", value=default, key=f"custom_{col}")
        else:
            new_data[col] = cols[i].text_input(col, value=default, key=f"input_{col}")

    if st.button("Add to Inventory"):
        values = tuple(new_data[col] for col in col_names)
        placeholders = ', '.join('?' for _ in values)
        cursor.execute(f"INSERT INTO {active_table} ({', '.join(col_names)}) VALUES ({placeholders})", values)
        conn.commit()
        st.success("✅ Item added!")
        st.rerun()

# --- Edit/Delete Table ---
st.subheader("📝 Edit & Delete Items")
if df.empty:
    st.info("No inventory yet.")
else:
    filter_col = st.selectbox("Filter by column", df.columns.drop("rowid"))
    filter_val = st.text_input("Contains")
    if filter_val:
        df = df[df[filter_col].astype(str).str.contains(filter_val, na=False)]

    df["selected"] = False
    editable_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="editor_table", disabled=["rowid"])

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💾 Save Changes"):
            cursor.execute(f"DELETE FROM {active_table}")
            editable_df.drop(columns=["rowid", "selected"]).to_sql(active_table, conn, if_exists="append", index=False)
            conn.commit()
            st.success("Saved successfully.")
            st.rerun()

    with col2:
        if st.button("🗑 Delete Selected"):
            to_delete = editable_df[editable_df["selected"] == True]["rowid"].tolist()
            if to_delete:
                cursor.executemany(f"DELETE FROM {active_table} WHERE rowid = ?", [(rid,) for rid in to_delete])
                conn.commit()
                st.success(f"Deleted {len(to_delete)} item(s).")
                st.rerun()

    with col3:
        if st.button("📌 Set as Template"):
            selected = editable_df[editable_df["selected"] == True]
            if len(selected) == 1:
                row = selected.drop(columns=["rowid", "selected"]).iloc[0].to_dict()
                templates[table_key] = row
                with open(template_file, "w") as f:
                    yaml.safe_dump(templates, f)
                st.success("✅ Template saved for future entries.")
            elif len(selected) == 0:
                st.warning("⚠️ Please select one row to set as a template.")
            else:
                st.warning("⚠️ Please select only one row.")
conn.close()
