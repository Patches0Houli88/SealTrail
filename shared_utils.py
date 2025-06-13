import sqlite3
import pandas as pd
import os
import yaml
from datetime import datetime

# --- SESSION SAFE GETTERS ---
def get_db_path():
    db_path = st.session_state.get("db_path", None)
    if not db_path or not os.path.exists(db_path):
        st.error("No active database found. Please return to the main page.")
        st.stop()
    return db_path

def get_active_table():
    return st.session_state.get("active_table", "equipment")

# --- CONNECTION HANDLER ---
def load_connection():
    db_path = get_db_path()
    return sqlite3.connect(db_path)

def get_conn(db_path=None):
    if db_path is None:
        db_path = get_db_path()
    return sqlite3.connect(db_path)

# --- GENERIC TABLE LOADER ---
def load_table(name):
    conn = load_connection()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except:
        df = pd.DataFrame()
    finally:
        conn.close()

    return df

# --- NORMALIZED LOADERS ---
def load_equipment():
    active_table = get_active_table()
    df = load_table(active_table)
    if not df.empty:
        id_col = get_id_column(df)
        if id_col:
            df[id_col] = df[id_col].astype(str).str.strip()
    return df

def load_maintenance():
    df = load_table("maintenance_log")
    if not df.empty:
        if "equipment_id" in df.columns:
            df["equipment_id"] = df["equipment_id"].astype(str).str.strip()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

def load_scans():
    df = load_table("scanned_items")
    if not df.empty:
        if "equipment_id" in df.columns:
            df["equipment_id"] = df["equipment_id"].astype(str).str.strip()
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df

# --- COLUMN FINDERS ---
def get_id_column(df):
    return next((col for col in df.columns if col.lower() in ["asset_id", "equipment_id"]), None)

def get_type_column(df):
    return next((col for col in df.columns if col.lower() in ["equipment_type", "type"]), None)

# --- SETTINGS YAML HANDLER ---
def load_settings_yaml():
    file = "maintenance_settings.yaml"
    if os.path.exists(file):
        with open(file, "r") as f:
            return yaml.safe_load(f) or {}
    else:
        return {}

def save_settings_yaml(settings):
    file = "maintenance_settings.yaml"
    with open(file, "w") as f:
        yaml.safe_dump(settings, f)

# --- AUDIT LOGGING ---
def init_audit_table():
    db_path = get_db_path()
    with get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_email TEXT,
                action TEXT,
                detail TEXT
            )
        """)
        conn.commit()

def log_audit(action, detail=""):
    db_path = get_db_path()
    user_email = st.session_state.get("user_email", "system")
    timestamp = datetime.utcnow().isoformat()

    try:
        with get_conn(db_path) as conn:
            conn.execute("""
                INSERT INTO audit_log (timestamp, user_email, action, detail)
                VALUES (?, ?, ?, ?)
            """, (timestamp, user_email, action, detail))
            conn.commit()
    except:
        pass  # fail silently if audit table doesn't exist
