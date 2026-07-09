from __future__ import annotations
import streamlit as st
from scoring.io import (
    read_excel_file, save_uploaded_excel, save_parquet,
    RAW_PARQUET, SCORED_PARQUET, load_formula_params, load_scoring_settings, load_data_quality_rules
)
from scoring.validation import validate_schema
from scoring.scoring_engine import compute_scores_dynamic
from scoring.formatting import format_dataframe_for_display, format_metric_value

st.title("🔐 Admin - Upload Data Koridor")
st.info("Upload file Excel agregasi koridor. Aplikasi menyimpan raw data ke Parquet dan langsung menghitung skor berdasarkan menu **Rumus Perhitungan**. Pastikan file sudah level agregasi koridor, bukan ruas mentah.")

uploaded = st.file_uploader("Pilih Excel agregasi koridor", type=["xlsx"])

if uploaded:
    with st.spinner("Membaca Excel..."):
        df = read_excel_file(uploaded)
    st.success(f"Terbaca: {format_metric_value(len(df), kind='int')} baris dan {format_metric_value(len(df.columns), kind='int')} kolom.")
    st.dataframe(format_dataframe_for_display(df.head(50)), use_container_width=True)

    missing = validate_schema(df)
    if missing:
        st.error("Kolom wajib hilang. File belum bisa diproses.")
        st.write(missing)
        st.stop()

    if st.button("Proses dan Simpan ke Database Parquet", type="primary"):
        save_uploaded_excel(uploaded, uploaded.name)
        save_parquet(df, RAW_PARQUET)
        params = load_formula_params()
        rules = load_data_quality_rules()
        settings = load_scoring_settings()
        scored = compute_scores_dynamic(df, params, penalty_factor=float(settings.get("penalty_factor", 0.30)), data_quality_rules=rules, scoring_settings=settings)
        save_parquet(scored, SCORED_PARQUET)
        st.cache_data.clear()
        st.success("Data berhasil diproses dengan rumus dinamis, biaya aktif, dan threshold kategori yang sedang tersimpan.")
        st.write(f"Raw Parquet: `{RAW_PARQUET}`")
        st.write(f"Scored Parquet: `{SCORED_PARQUET}`")
        st.dataframe(format_dataframe_for_display(scored.head(20)), use_container_width=True)
