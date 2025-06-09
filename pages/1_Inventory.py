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

# Load existing data
def load_data():
    try:
        df = pd.read_sql("SELECT rowid, * FROM equipment", conn)
        return df
    except Exception:
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

# --- Edit Inventory with Filters ---
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

    st.markdown("### Inline Edit Table")
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

# --- Delete Inventory Items ---
st.subheader("Delete Items")
if not df.empty:
    st.markdown("### Select Rows to Delete")
    delete_df = df.copy()
    delete_df["select"] = False
    selection = st.data_editor(delete_df, column_order=["select"] + list(df.columns), use_container_width=True, key="delete_selector")

    selected_ids = selection[selection["select"] == True]["rowid"].tolist()

    if st.button("Delete Selected"):
        if selected_ids:
            cursor.executemany("DELETE FROM equipment WHERE rowid = ?", [(i,) for i in selected_ids])
            conn.commit()
            st.success(f"Deleted {len(selected_ids)} items.")
            st.rerun()
        else:
            st.warning("No items selected.")

conn.close()
