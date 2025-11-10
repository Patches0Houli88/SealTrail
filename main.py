# main.py
import streamlit as st
import os
import pandas as pd
import sqlite3
import yaml

st.set_page_config(page_title="SealTrail", layout="wide")

# -----------------------------
# Auth shim + helpers
# -----------------------------
def _attach_user():
    """Provide a minimal st.user object that reads from session_state and
    supports the attributes and .get() calls your previous code used."""
    class _User:
        @property
        def is_logged_in(self):
            return bool(st.session_state.get("authentication_status", False))

        @property
        def name(self):
            return st.session_state.get("name") or st.session_state.get("username")

        @property
        def role(self):
            return st.session_state.get("role", "admin")

        @property
        def email(self):
            return st.session_state.get("email")

        def get(self, key, default=None):
            # allow st.user.get("email", "...") style reads
            mapping = {
                "is_logged_in": self.is_logged_in,
                "name": self.name,
                "role": self.role,
                "email": self.email,
                "username": st.session_state.get("username"),
            }
            val = mapping.get(key)
            return val if val is not None else st.session_state.get(key, default)

        def as_dict(self):
            return {
                "is_logged_in": self.is_logged_in,
                "name": self.name,
                "role": self.role,
                "email": self.email,
                "username": st.session_state.get("username"),
            }

    st.user = _User()

def _do_logout():
    for k in [
        "authentication_status", "name", "username", "email", "role",
        "selected_db", "active_table", "db_path"
    ]:
        if k in st.session_state:
            del st.session_state[k]
    st.success("Logged out.")
    st.rerun()

def _login_ui():
    st.title("SealTrail")
    st.subheader("Sign in to continue")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", key="login_email", placeholder="you@example.com")
        name = st.text_input("Name (optional)", key="login_name", placeholder="Your name")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if not email or "@" not in email:
                st.error("Please enter a valid email.")
            else:
                st.session_state["authentication_status"] = True
                st.session_state["email"] = email.strip()
                st.session_state["name"] = name.strip() or email.split("@")[0]
                st.session_state["username"] = st.session_state["name"]
                # Default role on first login until roles.yaml says otherwise
                st.session_state.setdefault("role", "admin")
                st.experimental_rerun()

# attach shim
_attach_user()

# -----------------------------
# Login gate (replaces st.login/st.logout)
# -----------------------------
if not st.user.is_logged_in:
    _login_ui()
    st.stop()

# -----------------------------
# User info + logout
# -----------------------------
user_email = st.user.get("email", "unknown@example.com")
user_name = st.user.get("name", "Unknown")
st.sidebar.markdown(f"**Logged in as:** {user_name}")
st.sidebar.caption(user_email)
if st.sidebar.button("Logout"):
    _do_logout()

# -----------------------------
# Per-user data directory
# -----------------------------
user_dir = f"data/{user_email.replace('@', '_at_')}"
os.makedirs(user_dir, exist_ok=True)

# -----------------------------
# Roles & permissions (roles.yaml)
# -----------------------------
roles_config = {}
if os.path.exists("roles.yaml"):
    with open("roles.yaml") as f:
        roles_config = yaml.safe_load(f) or {}

roles_config.setdefault("users", {})

# Auto-add user if not exists
if user_email not in roles_config["users"]:
    roles_config["users"][user_email] = {"role": "user", "allowed_dbs": []}
    with open("roles.yaml", "w") as f:
        yaml.safe_dump(roles_config, f)

user_role = roles_config["users"][user_email]["role"]
allowed_dbs = roles_config["users"][user_email]["allowed_dbs"]

st.session_state["user_email"] = user_email
st.session_state["user_role"] = user_role

# -----------------------------
# Sidebar: role + DB management
# -----------------------------
st.sidebar.write(f"Role: **{user_role.capitalize()}**")

# list existing DBs for this user
db_files = [f for f in os.listdir(user_dir) if f.endswith(".db")]
if allowed_dbs != ["all"]:
    db_files = [db for db in db_files if db in allowed_dbs or user_role == "admin"]

# Create DB
with st.sidebar.expander("Create Database", expanded=not db_files):
    new_db_name = st.text_input("New DB name", placeholder="my_inventory.db", key="new_db_name")
    if st.button("Create DB", key="create_db_btn") and new_db_name:
        name = new_db_name if new_db_name.endswith(".db") else f"{new_db_name}.db"
        full_path = os.path.join(user_dir, name)
        if os.path.exists(full_path):
            st.error("Database already exists.")
        else:
            open(full_path, "w").close()
            st.session_state.selected_db = name
            if user_role != "admin":
                roles_config["users"][user_email]["allowed_dbs"].append(name)
                with open("roles.yaml", "w") as f:
                    yaml.safe_dump(roles_config, f)
            st.success(f"Created: {name}")
            st.rerun()

# Select DB
if db_files:
    selected_db = st.sidebar.selectbox(
        "Choose a database", options=sorted(db_files),
        index=sorted(db_files).index(st.session_state.get("selected_db")) if st.session_state.get("selected_db") in db_files else 0,
        key="selected_db_select"
    )
    st.session_state.selected_db = selected_db
else:
    st.sidebar.warning("No databases found. Create one above.")

# Delete DB
if db_files:
    with st.sidebar.expander("Delete Database"):
        deletable = sorted(db_files) if user_role == "admin" else [db for db in sorted(db_files) if db in allowed_dbs]
        if deletable:
            db_to_delete = st.selectbox("Delete which?", deletable, key="delete_db_select")
            if st.button("Delete DB", key="delete_db_btn"):
                os.remove(os.path.join(user_dir, db_to_delete))
                # prune from roles if present
                if db_to_delete in roles_config["users"][user_email]["allowed_dbs"]:
                    roles_config["users"][user_email]["allowed_dbs"].remove(db_to_delete)
                    with open("roles.yaml", "w") as f:
                        yaml.safe_dump(roles_config, f)
                if st.session_state.get("selected_db") == db_to_delete:
                    st.session_state.pop("selected_db", None)
                st.success(f"{db_to_delete} deleted.")
                st.rerun()

# -----------------------------
# Main content
# -----------------------------
st.title("Equipment & Inventory Tracking System")

if "selected_db" not in st.session_state:
    st.warning("No database selected.")
    st.stop()

db_path = os.path.join(user_dir, st.session_state.selected_db)
st.session_state.db_path = db_path
st.markdown(f"**Current DB**: `{st.session_state.selected_db}`")

# Upload to working table
st.subheader("Upload File to Working Table")
uploaded_file = st.file_uploader(
    "Upload CSV, Excel, JSON or TSV",
    type=["csv", "xlsx", "xls", "tsv", "json"],
    key="uploader"
)

if uploaded_file:
    try:
        ext = uploaded_file.name.split(".")[-1].lower()
        if ext == "csv":
            df = pd.read_csv(uploaded_file)
        elif ext == "tsv":
            df = pd.read_csv(uploaded_file, sep="\t")
        elif ext in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file)
        elif ext == "json":
            df = pd.read_json(uploaded_file)
        else:
            st.error("Unsupported file type.")
            st.stop()

        # Normalize column names
        df.columns = df.columns.str.strip()
        if "Asset_ID" in df.columns and "equipment_id" not in df.columns:
            df.rename(columns={"Asset_ID": "equipment_id"}, inplace=True)

        st.dataframe(df, use_container_width=True, height=380)

        table_name = st.text_input("Save to which table?", value=st.session_state.get("active_table", "equipment"))
        if st.button("Save to DB", key="save_to_db_btn") and table_name:
            with sqlite3.connect(db_path) as conn:
                df.to_sql(table_name, conn, if_exists="replace", index=False)
            st.session_state.active_table = table_name
            st.success(f"Saved to '{table_name}' table.")

    except Exception as e:
        st.error(f"Error processing file: {e}")

# Active table selection
try:
    with sqlite3.connect(db_path) as conn:
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
    if tables:
        active_table = st.selectbox(
            "Select active working table",
            tables,
            index=tables.index(st.session_state.get("active_table")) if st.session_state.get("active_table") in tables else 0,
            key="table_selector"
        )
        st.session_state.active_table = active_table
        st.markdown(f"**Active Table**: `{active_table}`")
    else:
        st.info("No tables found. Upload a file to create one.")
except Exception as e:
    st.warning(f"Error fetching tables: {e}")

# Show current active table
if st.session_state.get("active_table"):
    try:
        with sqlite3.connect(db_path) as conn:
            current_df = pd.read_sql(f"SELECT * FROM {st.session_state.active_table}", conn)
        if not current_df.empty:
            st.subheader("📋 Current Active Table")
            st.dataframe(current_df, use_container_width=True, height=420)
        else:
            st.info(f"'{st.session_state.active_table}' is empty.")
    except Exception as e:
        st.warning(f"Could not read active table: {e}")
else:
    st.info("Select an active table to view its contents.")
