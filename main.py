import streamlit as st
import streamlit_authenticator as stauth
import yaml
import sqlite3
import os
from yaml.loader import SafeLoader

# Load config
def load_config():
    with open('config.yaml') as file:
        return yaml.load(file, Loader=SafeLoader)

config = load_config()
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, auth_status, username = authenticator.login('Login', location='main')

if auth_status:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.title(f"Welcome, {name}")

    user_dir = f"data/{username}"
    os.makedirs(user_dir, exist_ok=True)

    # List dashboards
    dashboards = [f.replace(".db", "") for f in os.listdir(user_dir) if f.endswith(".db")]
    dashboard_choice = st.selectbox("Select Dashboard", dashboards + ["➕ Create New"])

    if dashboard_choice == "➕ Create New":
        new_name = st.text_input("New dashboard name")
        if st.button("Create"):
            open(f"{user_dir}/{new_name}.db", "w").close()
            st.success("Dashboard created. Reload to see it.")
    elif dashboard_choice:
        st.session_state.db_path = f"{user_dir}/{dashboard_choice}.db"
        st.success(f"Loaded dashboard: {dashboard_choice}")
        # You can redirect to dashboard.py logic here or use multipage setup

elif auth_status is False:
    st.error("Incorrect username or password.")
elif auth_status is None:
    st.warning("Please enter your credentials.")
