from __future__ import annotations
import streamlit as st
from scoring.io import has_scored_data, has_raw_data, load_parquet, load_scoring_settings, RAW_PARQUET, SCORED_PARQUET
from scoring.validation import build_validation_table
from scoring.formatting import format_dataframe_for_display, format_metric_value

st.title("🔐 Admin - Validasi Data")
st.info("Menu ini membaca kualitas data berdasarkan pengaturan di menu Rumus Perhitungan. Jika KML diatur memakai fallback panjang koridor atau penalti dimatikan, hasil validasi ikut menyesuaikan.")

if not has_scored_data():
    st.warning("Belum ada data. Upload dan proses Excel dulu.")
    st.stop()

settings = load_scoring_settings()
df = load_parquet(RAW_PARQUET if has_raw_data() else SCORED_PARQUET)
issues = build_validation_table(df, scoring_settings=settings)

with st.expander("⚙️ Pengaturan validasi yang sedang dipakai", expanded=False):
    st.json(settings)

c1, c2, c3 = st.columns(3)
c1.metric("Total Koridor", format_metric_value(len(df), kind="int"))
c2.metric("Koridor dengan Catatan", format_metric_value(len(issues), kind="int"))
c3.metric("Persentase dengan Catatan", format_metric_value((len(issues)/len(df)*100), kind="percent", decimals=1) if len(df) else "0%")

st.subheader("Daftar Catatan/Masalah Data")
st.caption("Catatan seperti 'dinormalisasi' atau 'fallback' tidak selalu berarti salah; itu menunjukkan aplikasi melakukan perlakuan khusus sesuai setting.")
st.dataframe(format_dataframe_for_display(issues), use_container_width=True, height=600)

csv = issues.to_csv(index=False).encode("utf-8-sig")
st.download_button("Download validasi CSV", data=csv, file_name="validasi_data_koridor.csv", mime="text/csv")
