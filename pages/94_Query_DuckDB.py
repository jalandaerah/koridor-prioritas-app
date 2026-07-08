from __future__ import annotations
import streamlit as st
from scoring.io import SCORED_PARQUET, has_scored_data
from scoring.formatting import format_dataframe_for_display

st.title("🔐 Admin - Query DuckDB")
st.info("Halaman ini untuk query SQL cepat ke file Parquet. Cocok untuk analisis ad-hoc yang tidak tersedia di dashboard. Jika hanya butuh filter biasa, gunakan tab Query Builder di Dashboard Utama.")

if not has_scored_data():
    st.warning("Belum ada data. Upload dan proses Excel dulu.")
    st.stop()

try:
    import duckdb
except Exception as e:
    st.error("DuckDB belum terinstall. Jalankan: pip install duckdb")
    st.exception(e)
    st.stop()

query = st.text_area("SQL", value=f"""SELECT Provinsi, COUNT(*) AS jumlah_koridor, AVG(final_score) AS avg_score
FROM read_parquet('{SCORED_PARQUET.as_posix()}')
GROUP BY Provinsi
ORDER BY avg_score DESC""", height=180)

if st.button("Run Query"):
    try:
        result = duckdb.query(query).to_df()
        st.dataframe(format_dataframe_for_display(result), use_container_width=True)
    except Exception as e:
        st.exception(e)
