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

user_email = st.session_state.get("user_email", "unknown@example.com")
user_role = st.session_state.get("user_role", "guest")

def load_data():
    try:
        df = pd.read_sql("SELECT rowid, * FROM equipment", conn)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# --- Column Management (Admin only) ---
if user_role == "admin":
    st.subheader("🛠 Column Management (Admin Only)")

    with st.expander("➕ Add Column"):
        new_col = st.text_input("New column name")
        col_type = st.selectbox("Data type", ["TEXT", "INTEGER", "REAL", "DATE"])
        if st.button("Add Column"):
            if new_col:
                try:
                    cursor.execute(f"ALTER TABLE equipment ADD COLUMN {new_col} {col_type}")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS column_audit_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_email TEXT,
                            action TEXT,
                            column_name TEXT,
                            data_type TEXT,
                            timestamp TEXT
                        )
                    """)
                    cursor.execute("""
                        INSERT INTO column_audit_log (user_email, action, column_name, data_type, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_email, "ADD", new_col, col_type, datetime.now().isoformat()))
                    conn.commit()
                    st.success(f"Column '{new_col}' added.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    with st.expander("✏️ Rename/Delete Column"):
        existing_cols = [col for col in df.columns if col != "rowid"]
        selected_col = st.selectbox("Select column to modify", existing_cols)

        new_name = st.text_input("Rename to (leave blank to skip)")
        if st.button("Rename Column") and new_name:
            try:
                st.warning("Renaming requires table recreation. Proceed with caution.")
                temp_df = df.copy()
                temp_df = temp_df.rename(columns={selected_col: new_name})
                cursor.execute("DROP TABLE IF EXISTS equipment")
                temp_df.drop(columns="rowid").to_sql("equipment", conn, index=False)
                cursor.execute("""
                    INSERT INTO column_audit_log (user_email, action, column_name, data_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_email, "RENAME", f"{selected_col} → {new_name}", "N/A", datetime.now().isoformat()))
                conn.commit()
                st.success(f"Renamed '{selected_col}' to '{new_name}'")
                st.rerun()
            except Exception as e:
                st.error(f"Rename failed: {e}")

        if st.button("Delete Column"):
            try:
                st.warning("Deleting a column requires table recreation. Proceed with caution.")
                temp_df = df.drop(columns=[selected_col, "rowid"])
                cursor.execute("DROP TABLE IF EXISTS equipment")
                temp_df.to_sql("equipment", conn, index=False)
                cursor.execute("""
                    INSERT INTO column_audit_log (user_email, action, column_name, data_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_email, "DELETE", selected_col, "N/A", datetime.now().isoformat()))
                conn.commit()
                st.success(f"Deleted column '{selected_col}'")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")

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
        if 1 < len(unique_vals) < 20:
            new_values[col] = col_layout[i].selectbox(col, unique_vals + ["<Other>"])
            if new_values[col] == "<Other>":
                new_values[col] = col_layout[i].text_input(f"Enter custom {col}")
        else:
            new_values[col] = col_layout[i].text_input(col)

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
if not df.empty:
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
    delete_ids = st.multiselect("Select items to delete:", df["rowid"].tolist())
    if st.button("Delete Selected") and delete_ids:
        cursor.executemany("DELETE FROM equipment WHERE rowid = ?", [(i,) for i in delete_ids])
        conn.commit()
        st.success("Selected items deleted.")
        st.rerun()

conn.close()
