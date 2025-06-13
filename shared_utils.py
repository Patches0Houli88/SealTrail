# shared_utils.py
import sqlite3
import pandas as pd
import os

# --- Core DB Connection ---
def get_conn(db_path):
    """Safely open SQLite connection"""
    if not db_path or not os.path.exists(db_path):
        raise FileNotFoundError("Database path invalid")
    return sqlite3.connect(db_path)


# --- Universal Table Loader ---
def load_table(db_path, table_name):
    """Load any table, safely"""
    try:
        with get_conn(db_path) as conn:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            df = normalize_table(df, table_name)
            return df
    except Exception:
        return pd.DataFrame()


# --- Normalize dataframe columns automatically ---
def normalize_table(df, table_name):
    """Apply standard normalization depending on table type"""

    # Normalize equipment_id for ALL tables that have it
    for col in df.columns:
        if col.lower() in ["equipment_id", "asset_id"]:
            df[col] = df[col].astype(str).str.strip()

    # Normalize maintenance dates
    if table_name == "maintenance_log" and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Normalize scanned_items timestamps
    if table_name == "scanned_items" and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    return df


# --- Save back to DB ---
def save_table(db_path, table_name, dataframe):
    """Overwrite table contents"""
    with get_conn(db_path) as conn:
        dataframe.to_sql(table_name, conn, if_exists="replace", index=False)


# --- Append (optional helper for inserts) ---
def insert_row(db_path, table_name, row_dict):
    """Insert one row (dict of values)"""
    with get_conn(db_path) as conn:
        cols = ', '.join(row_dict.keys())
        placeholders = ', '.join(['?'] * len(row_dict))
        values = list(row_dict.values())
        conn.execute(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", values)
        conn.commit()


# --- Utility: get all tables ---
def list_tables(db_path):
    """List available tables"""
    with get_conn(db_path) as conn:
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return [r[0] for r in result]
