import streamlit as st
import sqlite3
import pandas as pd

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
        df = pd.read_sql("SELECT rowid, * FROM equipment", conn)
        return df
    except:
        return pd.DataFrame()

df = load_data()

# ----------------- Column Management -------------------
st.subheader("🛠 Manage Columns")

with st.expander("Add a Column"):
    new_col = st.text_input("New column name")
    new_col_type = st.selectbox("Data type", ["TEXT", "INTEGER", "REAL"])
    if st.button("Add Column"):
        if new_col:
            try:
                cursor.execute(f"ALTER TABLE equipment ADD COLUMN {new_col} {new_col_type}")
                conn.commit()
                st.success(f"Added column `{new_col}` of type {new_col_type}.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

with st.expander("Rename Column"):
    if not df.empty:
        col_to_rename = st.selectbox("Select column", df.columns.drop("rowid"))
        new_name = st.text_input("New column name")
        if st.button("Rename Column"):
            try:
                # SQLite doesn't support native RENAME COLUMN, use workaround
                df_renamed = df.rename(columns={col_to_rename: new_name})
                df_renamed.drop(columns="rowid").to_sql("equipment", conn, if_exists="replace", index=False)
                st.success(f"Renamed column `{col_to_rename}` to `{new_name}`.")
                st.rerun()
            except Exception as e:
                st.error(f"Rename failed: {e}")

with st.expander("Delete Column"):
    if not df.empty:
        col_to_delete = st.selectbox("Select column to delete", df.columns.drop("rowid"))
        if st.button("Delete Column"):
            try:
                df_dropped = df.drop(columns=[col_to_delete])
                df_dropped.drop(columns="rowid").to_sql("equipment", conn, if_exists="replace", index=False)
                st.success(f"Deleted column `{col_to_delete}`.")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting column: {e}")

# ----------------- Add New Inventory -------------------
st.subheader("➕ Add New Item")
if df.empty:
    st.info("No existing data found to determine columns.")
else:
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

    if st.button("Add to Inventory"):
        values = tuple(new_values[col] for col in col_names)
        placeholders = ', '.join('?' for _ in values)
        sql = f"INSERT INTO equipment ({', '.join(col_names)}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        st.success("Item added!")
        st.rerun()

# ----------------- Edit Items -------------------
st.subheader("✏️ Edit Items")
if not df.empty:
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

# ----------------- Delete Items -------------------
st.subheader("❌ Delete Items")
if not df.empty:
    delete_ids = st.multiselect("Select items to delete", df["rowid"].tolist())
    if st.button("Delete Selected") and delete_ids:
        cursor.executemany("DELETE FROM equipment WHERE rowid = ?", [(i,) for i in delete_ids])
        conn.commit()
        st.success("Selected items deleted.")
        st.rerun()

conn.close()
