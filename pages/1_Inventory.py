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

# --- Edit Inventory ---
st.subheader("Edit Items")
if df.empty:
    st.info("No data available to edit.")
else:
    sort_col = st.selectbox("Sort by column:", df.columns.drop("rowid"))
    sort_order = st.radio("Order:", ["A-Z / 0-9", "Z-A / 9-0"])
    df_sorted = df.sort_values(by=sort_col, ascending=(sort_order == "A-Z / 0-9"))

    editable_df = st.data_editor(df_sorted.drop(columns="rowid"), num_rows="dynamic", use_container_width=True, key="editor")
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
