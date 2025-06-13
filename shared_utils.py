import sqlite3
import pandas as pd
import os
import yaml
from datetime import datetime

### --- SESSION SAFE GETTERS ---
def get_db_path():
    db_path = st.session_state.get("db_path", None)
    if not db_path or not os.path.exists(db_path):
        st.error("No active database found. Please return to the main page.")
        st.stop()
    return db_path

def get_active_table():
    return st.session_state.get("active_table", "equipment")

### --- DATABASE LOADERS ---
def load_connection():
    db_path = get_db_path()
    return sqlite3.connect(db_path)

def load_table(table):
    conn = load_connection()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    except:
        df = pd.DataFrame()
    finally:
        conn.close()

    if "equipment_id" in df.columns:
        df["equipment_id"] = df["equipment_id"].astype(str).str.strip()
    return df

def load_equipment():
    active_table = get_active_table()
    return load_table(active_table)

def load_maintenance():
    df = load_table("maintenance_log")
    if not df.empty:
        df["equipment_id"] = df["equipment_id"].astype(str).str.strip()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

def load_scans():
    df = load_table("scanned_items")
    if not df.empty:
        df["equipment_id"] = df["equipment_id"].astype(str).str.strip()
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df

### --- IDENTIFIER NORMALIZATION ---
def get_id_column(df):
    return next((col for col in df.columns if col.lower() in ["asset_id", "equipment_id"]), None)

def get_type_column(df):
    return next((col for col in df.columns if col.lower() in ["equipment_type", "type"]), None)

### --- YAML SETTINGS HANDLER ---
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

### --- AUDIT LOGGER (NEW) ---
def log_audit(db_path, user_email, action, detail):
    """
    Logs any user action to audit_log table.
    """
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_email TEXT,
            action TEXT,
            detail TEXT
        )
    """)

    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO audit_log (timestamp, user_email, action, detail)
        VALUES (?, ?, ?, ?)
    """, (timestamp, user_email, action, detail))

    conn.commit()
    conn.close()
