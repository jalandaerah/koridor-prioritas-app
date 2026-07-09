from __future__ import annotations
import pandas as pd
import streamlit as st
from scoring.io import has_scored_data, load_parquet, load_formula_params
from scoring.schema import COL, PRODUCTION_TYPE_COLS, PRODUCTION_AMOUNT_COLS, LAND_AREA_COLS
from scoring.scoring_engine import get_score_component_columns, build_formula_summary, export_columns
from scoring.formatting import format_dataframe_for_display, format_metric_value, format_series_for_display

st.title("👤 Detail Koridor")
st.info("Pilih satu koridor untuk melihat skor akhir, ranking, komponen skor, rumus yang dipakai, dan data lengkap. Menu ini berguna untuk audit kenapa skor koridor naik/turun.")

if not has_scored_data():
    st.warning("Belum ada data. Upload dan proses Excel dulu.")
    st.stop()

df = load_parquet().sort_values("final_score", ascending=False)
label_col = "nama_koridor_display" if "nama_koridor_display" in df.columns else COL["nama_koridor"]
choices = (df[COL["id_koridor"]].astype(str) + " | " + df[COL["provinsi"]].astype(str) + " | " + df[label_col].astype(str)).tolist()
selected = st.selectbox("Pilih koridor", choices)
id_selected = selected.split(" | ")[0]
row = df[df[COL["id_koridor"]].astype(str) == id_selected].iloc[0]

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Final Score", format_metric_value(row["final_score"], decimals=2))
m2.metric("Rank Nasional", format_metric_value(row["rank_nasional"], kind="int"))
m3.metric("Kategori", row["kategori_prioritas"])
m4.metric("Panjang KM", format_metric_value(row[COL["panjang"]], decimals=2) if row[COL["panjang"]] == row[COL["panjang"]] else "0")
m5.metric("Biaya Aktif Rp M", format_metric_value(row.get("biaya_aktif_miliar", row.get(COL["biaya"], 0)), decimals=2) if row.get("biaya_aktif_miliar", row.get(COL["biaya"], 0)) == row.get("biaya_aktif_miliar", row.get(COL["biaya"], 0)) else "0")

st.subheader(row.get("nama_koridor_display", row[COL["nama_koridor"]]))
st.write(f"**Provinsi:** {row[COL['provinsi']]}  ")
st.write(f"**Kabupaten/Kota:** {row[COL['kabupaten']]}  ")
st.write(f"**No. Koridor:** {row[COL['no_koridor']]}  ")
st.write(f"**Tematik:** {row.get(COL['tematik'], '-')}")
st.write(f"**Panjang KML Used:** {format_metric_value(row.get('panjang_kml_used_km'), decimals=2)} km  ")

st.subheader("Ringkasan Ekonomi Komoditas")
prod_items = []
for i, (tcol, pcol, lcol) in enumerate(zip(PRODUCTION_TYPE_COLS, PRODUCTION_AMOUNT_COLS, LAND_AREA_COLS), start=1):
    jenis = str(row.get(tcol, "") or "").strip()
    if jenis and jenis.lower() not in {"nan", "none", "-"}:
        prod_items.append({
            "Slot": i,
            "Jenis Produksi": jenis,
            "Jumlah Produksi": row.get(pcol),
            "Satuan Produksi": "Ton/Tahun",
            "Luas Lahan": row.get(lcol),
            "Satuan Lahan": "Ha",
        })
if prod_items:
    st.dataframe(format_dataframe_for_display(pd.DataFrame(prod_items)), use_container_width=True, hide_index=True)
else:
    st.info("Jenis produksi 1-4 belum terisi untuk koridor ini.")
prod_summary = pd.DataFrame([
    {"Item": "Produksi total", "Nilai": format_metric_value(row.get("produksi_total_ton_tahun"), decimals=2), "Satuan": "Ton/Tahun"},
    {"Item": "Luas lahan total", "Nilai": format_metric_value(row.get("luas_lahan_total_ha"), decimals=2), "Satuan": "Ha"},
    {"Item": "Produksi tertimbang komoditas", "Nilai": format_metric_value(row.get("produksi_tertimbang_ton_tahun"), decimals=2), "Satuan": "Ton/Tahun x bobot"},
    {"Item": "Luas lahan tertimbang komoditas", "Nilai": format_metric_value(row.get("luas_lahan_tertimbang_ha"), decimals=2), "Satuan": "Ha x bobot"},
    {"Item": "Bobot jenis produksi maksimum", "Nilai": format_metric_value(row.get("jenis_produksi_bobot_maks"), decimals=4), "Satuan": "bobot"},
    {"Item": "Detail bobot komoditas", "Nilai": str(row.get("jenis_produksi_bobot_detail", "-")), "Satuan": ""},
])
st.dataframe(prod_summary, use_container_width=True, hide_index=True)

st.subheader("Ringkasan Biaya yang Dipakai Scoring")
biaya_summary = pd.DataFrame([
    {"Item": "Biaya dipakai scoring", "Nilai": format_metric_value(row.get("biaya_aktif_miliar"), decimals=2), "Satuan": "Rp miliar"},
    {"Item": "Biaya per km dipakai scoring", "Nilai": format_metric_value(row.get("biaya_per_km_miliar"), decimals=3), "Satuan": "Rp miliar/km"},
    {"Item": "Mode biaya", "Nilai": str(row.get("cost_mode", "-")), "Satuan": ""},
])
st.dataframe(biaya_summary, use_container_width=True, hide_index=True)
with st.expander("Audit biaya: Excel asli vs hitung kondisi", expanded=False):
    audit_items = [
        ("Biaya Excel asli", row.get(COL["biaya"]), "Rp miliar"),
        ("Biaya kondisi awal", row.get("biaya_estimasi_kondisi_awal_miliar"), "Rp miliar"),
        ("Biaya kondisi setelah fallback/minimum", row.get("biaya_estimasi_kondisi_miliar"), "Rp miliar"),
        ("Biaya aktif", row.get("biaya_aktif_miliar"), "Rp miliar"),
        ("Sumber biaya", row.get("biaya_sumber", "-"), ""),
        ("Alasan biaya 0", row.get("biaya_nol_reason", ""), ""),
    ]
    audit_df = pd.DataFrame([{"Item": k, "Nilai": format_metric_value(v, decimals=2) if isinstance(v, (int, float)) and pd.notna(v) else str(v), "Satuan": s} for k, v, s in audit_items])
    st.dataframe(audit_df, use_container_width=True, hide_index=True)

st.subheader("Komponen Score Dinamis")
score_cols = get_score_component_columns(df)
score_table = row[[c for c in score_cols if c in row.index]].to_frame("Nilai")
st.dataframe(format_dataframe_for_display(score_table), use_container_width=True, height=520)

with st.expander("Rumus yang dipakai", expanded=False):
    params = load_formula_params()
    st.dataframe(format_dataframe_for_display(build_formula_summary(params)), use_container_width=True, height=360)

st.subheader("Data Utama")
user_cols_df = export_columns(pd.DataFrame([row]), include_audit=False)
st.dataframe(format_series_for_display(user_cols_df.iloc[0]).to_frame("Nilai"), use_container_width=True, height=520)

with st.expander("Data audit lengkap / semua kolom teknis", expanded=False):
    st.caption("Bagian ini menampilkan seluruh kolom mentah dan kolom audit. Kolom resmi untuk scoring biaya adalah `biaya_aktif_miliar`.")
    st.dataframe(format_series_for_display(row).to_frame("Nilai"), use_container_width=True, height=600)
