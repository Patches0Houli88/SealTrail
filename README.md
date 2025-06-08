# SealTrail Equipment & Inventory Tracking App

A portable, multi-user, barcode-enabled equipment tracking system. Designed for use in field operations, labs, warehouses, veterinary clinics, or any environment where equipment needs to be tracked, maintained, and audited.

---

## Features

- **User Login** with `streamlit-authenticator`
- **Multiple Dashboards** per user (switch or create new)
- **Dashboard View**: KPIs and status charts with Altair
- **Editable Inventory Table** via `st.data_editor()`
- **Add New Equipment** through form input
- **Maintenance Logs**: Record and view service history
- **Barcode Scanning** with webcam (`streamlit-webrtc` + `pyzbar`)
- **CSV Upload** and future support for data export/backup
- **Deployable to Streamlit Cloud** for public access

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| UI & Logic | [Streamlit](https://streamlit.io) |
| Auth | [streamlit-authenticator](https://github.com/mkhorasani/streamlit-authenticator) |
| DB | SQLite (per-user dashboards) |
| Charts | Altair |
| Barcode Scan | pyzbar + OpenCV + streamlit-webrtc |
| Deployment | Streamlit Cloud (or local run) |

---

## File Structure

inventory_app/
├── main.py                 # Login + dashboard selector
├── dashboard.py            # Main app interface (dashboard + logs + scanner)
├── config.yaml             # User credentials and cookie config
├── requirements.txt
├── data/
│   ├── alice/
│   │   └── warehouse.db
│   └── bob/
│       └── clinic.db
