
from __future__ import annotations
import streamlit as st

st.set_page_config(page_title="Koridor Prioritas", page_icon="🛣️", layout="wide")

try:
    pages = {
        "👤 Pengguna": [
            st.Page("pages/10_Dashboard_Pengguna.py", title="Dashboard", icon="🛣️", default=True),
            st.Page("pages/11_Detail_Koridor.py", title="Detail Koridor", icon="🔎"),
            st.Page("pages/12_Panduan_Aplikasi.py", title="Panduan Aplikasi", icon="📘"),
        ],
        "🔐 Admin": [
            st.Page("pages/90_Upload_Data.py", title="Upload Data", icon="📤"),
            st.Page("pages/91_Validasi_Data.py", title="Validasi Data", icon="🧪"),
            st.Page("pages/92_Rumus_Perhitungan.py", title="Rumus Perhitungan", icon="🧮"),
            st.Page("pages/93_Scoring.py", title="Scoring", icon="⚖️"),
            st.Page("pages/94_Query_DuckDB.py", title="Query DuckDB", icon="🦆"),
        ],
    }
    pg = st.navigation(pages, position="sidebar")
    pg.run()
except AttributeError:
    st.error("Versi Streamlit terlalu lama untuk menu berkelompok. Jalankan: pip install --upgrade streamlit")
    st.stop()
