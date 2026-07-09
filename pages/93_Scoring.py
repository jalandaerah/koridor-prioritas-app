from __future__ import annotations
import streamlit as st
from scoring.io import (
    has_scored_data, has_raw_data, load_parquet, save_parquet,
    RAW_PARQUET, SCORED_PARQUET, load_formula_params, load_scoring_settings, load_data_quality_rules
)
from scoring.scoring_engine import compute_scores_dynamic, export_columns, build_formula_summary
from scoring.formatting import format_dataframe_for_display

st.title("🔐 Admin - Scoring Koridor")
st.info("Halaman ini menjalankan ulang scoring memakai konfigurasi dari menu **Rumus Perhitungan**. Untuk mengubah angka rumus, buka menu Rumus Perhitungan dulu, bukan halaman ini.")

if not has_scored_data():
    st.warning("Belum ada data. Upload dan proses Excel dulu.")
    st.stop()

scored_df = load_parquet(SCORED_PARQUET)
params = load_formula_params()
rules = load_data_quality_rules()
settings = load_scoring_settings()

st.subheader("Rumus Aktif Saat Ini")
summary = build_formula_summary(params)
st.dataframe(format_dataframe_for_display(summary[summary["aktif"] == True]), use_container_width=True, height=300)

with st.expander("⚙️ Setting awal scoring yang sedang dipakai", expanded=False):
    st.json(settings)

if st.button("Hitung Ulang Ranking", type="primary"):
    base_df = load_parquet(RAW_PARQUET if has_raw_data() else SCORED_PARQUET)
    rescored = compute_scores_dynamic(base_df, params, penalty_factor=float(settings.get("penalty_factor", 0.30)), data_quality_rules=rules, scoring_settings=settings)
    save_parquet(rescored, SCORED_PARQUET)
    st.cache_data.clear()
    st.success("Skor berhasil dihitung ulang memakai rumus dinamis, biaya aktif, dan threshold kategori terbaru.")
    scored_df = rescored

st.subheader("Ringkasan Score")
st.dataframe(format_dataframe_for_display(export_columns(scored_df).sort_values("final_score", ascending=False).head(100)), use_container_width=True, height=520)
