
from __future__ import annotations
import json
import pandas as pd
import streamlit as st

from scoring.io import (
    has_raw_data, has_scored_data, load_parquet, RAW_PARQUET, SCORED_PARQUET,
    load_formula_params, load_scoring_settings, load_data_quality_rules,
)
from scoring.scoring_engine import FORMULA_TYPES, build_formula_summary, compute_scores_dynamic
from scoring.formatting import format_dataframe_for_display, format_metric_value

st.title("📑 Penjelasan Rumus Aktif")
st.info(
    "Halaman ini menjelaskan rumus scoring yang sedang dipakai saat ini. "
    "Halaman ini hanya untuk membaca dan audit, bukan untuk mengubah rumus. Perubahan rumus dilakukan di menu Admin → Rumus Perhitungan."
)

params = load_formula_params()
settings = load_scoring_settings()
rules = load_data_quality_rules()
active_params = [p for p in params if bool(p.get("active", True)) and float(p.get("weight", 0) or 0) > 0]
inactive_params = [p for p in params if not (bool(p.get("active", True)) and float(p.get("weight", 0) or 0) > 0)]
total_weight = sum(float(p.get("weight", 0) or 0) for p in active_params)
penalty_active = bool(settings.get("use_data_quality_penalty", True))
penalty_factor = float(settings.get("penalty_factor", 0.0) or 0.0) if penalty_active else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rumus aktif", format_metric_value(len(active_params), kind="int"))
c2.metric("Rumus nonaktif", format_metric_value(len(inactive_params), kind="int"))
c3.metric("Total bobot aktif", format_metric_value(total_weight, kind="number", decimals=2))
c4.metric("Faktor penalti", format_metric_value(penalty_factor, kind="number", decimals=2))

st.markdown("""
### Cara membaca skor akhir

```text
final_score = raw_score - (data_quality_penalty × penalty_factor)
```

`raw_score` berasal dari gabungan seluruh parameter aktif. Bobot asli boleh berjumlah berapa pun; aplikasi akan menormalkan bobot aktif menjadi 100%. Jika penalti kualitas data dimatikan, `final_score = raw_score`.
""")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧮 Rumus Aktif",
    "📚 Jenis Tipe Skor",
    "🌾 Ekonomi Komoditas",
    "⚠️ Penalti Data",
    "🔎 Audit Hasil"
])

with tab1:
    st.subheader("Rumus yang sedang dipakai")
    rows = []
    for p in active_params:
        ft = str(p.get("formula_type", ""))
        catalog = FORMULA_TYPES.get(ft, {})
        weight = float(p.get("weight", 0) or 0)
        norm = (weight / total_weight * 100) if total_weight > 0 else 0
        settings_json = p.get("settings_json", {}) or {}
        rows.append({
            "grup": p.get("group", ""),
            "id": p.get("id", ""),
            "nama_parameter": p.get("name", ""),
            "tipe_skor": ft,
            "arti_tipe_skor": catalog.get("label", ft),
            "rumus_ringkas": catalog.get("formula", "-"),
            "kolom_sumber": ", ".join(p.get("source_columns", []) or []),
            "bobot_asli": weight,
            "bobot_normal_%": norm,
            "settings_json": json.dumps(settings_json, ensure_ascii=False),
            "catatan": p.get("description", ""),
        })
    active_df = pd.DataFrame(rows)
    if active_df.empty:
        st.warning("Belum ada rumus aktif. Buka Admin → Rumus Perhitungan dan aktifkan minimal satu parameter.")
    else:
        group_filter = st.multiselect("Filter grup", sorted(active_df["grup"].dropna().unique().tolist()), default=[])
        show_df = active_df.copy()
        if group_filter:
            show_df = show_df[show_df["grup"].isin(group_filter)]
        st.dataframe(format_dataframe_for_display(show_df), use_container_width=True, height=500)

        st.markdown("#### Komposisi bobot aktif")
        bobot_grup = active_df.groupby("grup", dropna=False)["bobot_normal_%"].sum().reset_index().sort_values("bobot_normal_%", ascending=False)
        st.dataframe(format_dataframe_for_display(bobot_grup), use_container_width=True, height=240)
        try:
            st.bar_chart(bobot_grup.set_index("grup")["bobot_normal_%"])
        except Exception:
            pass

with tab2:
    st.subheader("Katalog jenis tipe skor")
    st.caption("Ini daftar tipe rumus yang bisa dipilih pada kolom formula_type di Admin → Rumus Perhitungan.")
    catalog_rows = []
    used_types = {str(p.get("formula_type", "")) for p in active_params}
    for key, meta in FORMULA_TYPES.items():
        catalog_rows.append({
            "formula_type": key,
            "sedang_dipakai": "YA" if key in used_types else "TIDAK",
            "nama_tipe": meta.get("label", key),
            "rumus": meta.get("formula", ""),
            "kapan_dipakai": meta.get("notes", ""),
            "contoh_settings_json": meta.get("settings_example", "{}"),
        })
    st.dataframe(pd.DataFrame(catalog_rows), use_container_width=True, height=540)

    with st.expander("Contoh memilih tipe skor", expanded=True):
        st.markdown("""
        - Kolom berisi **YA/TIDAK** → pakai `yes_no`.
        - Kolom angka dan **semakin besar semakin baik** → pakai `numeric_higher`.
        - Kolom angka dan **semakin kecil semakin baik** → pakai `numeric_lower`.
        - Kolom biaya yang 0 tidak boleh dianggap baik → pakai `numeric_lower_positive`.
        - Kolom prioritas/ranking, angka kecil lebih penting → pakai `rank_lower`.
        - Beberapa kolom dijumlahkan dengan bobot → pakai `weighted_sum_higher`.
        - Kondisi jalan berbasis RB/RR/Sedang → pakai `weighted_percent_sum`.
        - Produksi/lahan yang harus dikaitkan dengan jenis komoditas → pakai `production_amount_by_type`, `land_area_by_type`, atau `production_land_by_type`.
        """)

with tab3:
    st.subheader("Penjelasan rumus ekonomi komoditas")
    commodity_params = [p for p in params if str(p.get("formula_type", "")) in {"production_type_priority", "production_amount_by_type", "land_area_by_type", "production_land_by_type"}]
    st.markdown("""
    Rumus ekonomi komoditas mengaitkan **jenis produksi**, **jumlah produksi**, dan **luas lahan**. Tujuannya agar komoditas strategis bisa diberi prioritas lebih tinggi.

    Contoh: jika Padi diberi bobot `1,50` dan Jagung `1,20`, maka produksi padi 1.000 ton dihitung sebagai `1.000 × 1,50 = 1.500 nilai tertimbang`, sedangkan jagung 1.000 ton dihitung sebagai `1.000 × 1,20 = 1.200 nilai tertimbang`.
    """)
    if not commodity_params:
        st.warning("Belum ada parameter ekonomi komoditas di konfigurasi rumus.")
    else:
        comm_rows = []
        for p in commodity_params:
            sj = p.get("settings_json", {}) or {}
            cw = sj.get("commodity_weights", {}) or {}
            if isinstance(cw, str):
                try:
                    cw = json.loads(cw)
                except Exception:
                    cw = {}
            top_weights = sorted(cw.items(), key=lambda kv: float(kv[1] or 0), reverse=True)[:15]
            comm_rows.append({
                "aktif": "YA" if bool(p.get("active", True)) else "TIDAK",
                "id": p.get("id", ""),
                "nama": p.get("name", ""),
                "formula_type": p.get("formula_type", ""),
                "bobot_parameter": p.get("weight", 0),
                "default_weight": sj.get("default_weight", 1.0),
                "production_weight": sj.get("production_weight", "-"),
                "land_weight": sj.get("land_weight", "-"),
                "contoh_bobot_komoditas_tertinggi": "; ".join([f"{k}: {v}" for k, v in top_weights]),
            })
        st.dataframe(format_dataframe_for_display(pd.DataFrame(comm_rows)), use_container_width=True, height=360)

        first = commodity_params[0]
        cw = first.get("settings_json", {}).get("commodity_weights", {}) if isinstance(first.get("settings_json", {}), dict) else {}
        if cw:
            st.markdown("#### Daftar bobot komoditas dari konfigurasi")
            cw_df = pd.DataFrame([{"jenis_produksi": k, "bobot": v} for k, v in cw.items()]).sort_values("bobot", ascending=False)
            st.dataframe(format_dataframe_for_display(cw_df), use_container_width=True, height=360)

    st.markdown("""
    #### Rumus yang dipakai

    ```text
    produksi_tertimbang = Σ(jumlah_produksi_i × bobot_jenis_produksi_i)
    luas_lahan_tertimbang = Σ(luas_lahan_i × bobot_jenis_produksi_i)
    score_produksi = normalisasi(produksi_tertimbang) ke 0–100
    score_lahan = normalisasi(luas_lahan_tertimbang) ke 0–100
    ```

    Untuk parameter gabungan:

    ```text
    score_ekonomi_komoditas = score_produksi × production_weight + score_lahan × land_weight
    ```
    """)

with tab4:
    st.subheader("Penalti kualitas data")
    st.markdown("""
    Penalti berbeda dari skor parameter. Skor parameter menambah nilai, sedangkan penalti mengurangi nilai akhir bila data belum lengkap atau tidak konsisten.
    """)
    rule_rows = []
    for r in rules:
        rule_rows.append({
            "aktif": "YA" if bool(r.get("active", True)) else "TIDAK",
            "id": r.get("id", ""),
            "nama_penalti": r.get("name", ""),
            "tipe_penalti": r.get("rule_type", ""),
            "kolom_sumber": ", ".join(r.get("source_columns", []) or []),
            "nilai_penalti": r.get("penalty", 0),
            "settings_json": json.dumps(r.get("settings_json", {}) or {}, ensure_ascii=False),
        })
    if rule_rows:
        st.dataframe(format_dataframe_for_display(pd.DataFrame(rule_rows)), use_container_width=True, height=360)
    else:
        st.info("Tidak ada aturan penalti yang tersimpan.")

    st.markdown("#### Kebijakan awal yang sedang berlaku")
    settings_rows = [{"setting": k, "nilai": json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v} for k, v in settings.items()]
    st.dataframe(pd.DataFrame(settings_rows), use_container_width=True, height=360)

with tab5:
    st.subheader("Audit hasil scoring saat ini")
    if not has_scored_data():
        st.warning("Belum ada hasil scoring. Jalankan Admin → Upload Data, lalu Admin → Scoring atau Admin → Rumus Perhitungan → Simpan + Hitung Ulang.")
    else:
        df = load_parquet(SCORED_PARQUET)
        score_cols = [c for c in df.columns if c.startswith("score__")]
        weighted_cols = [c for c in df.columns if c.startswith("weighted__")]
        audit_cols = [c for c in ["rank_nasional", "nama_koridor_display", "No. Koridor", "Provinsi", "Kabupaten/Kota", "raw_score", "data_quality_penalty", "final_score", "biaya_aktif_miliar", "biaya_sumber"] if c in df.columns]
        st.markdown("#### Top 20 hasil akhir")
        st.dataframe(format_dataframe_for_display(df.sort_values("final_score", ascending=False)[audit_cols].head(20)), use_container_width=True, height=360)

        st.markdown("#### Statistik komponen skor")
        if score_cols:
            stat = df[score_cols].apply(pd.to_numeric, errors="coerce").describe().T.reset_index().rename(columns={"index": "komponen"})
            st.dataframe(format_dataframe_for_display(stat), use_container_width=True, height=360)
        else:
            st.info("Kolom komponen skor belum ditemukan.")

        with st.expander("Kolom weighted kontribusi", expanded=False):
            if weighted_cols:
                statw = df[weighted_cols].apply(pd.to_numeric, errors="coerce").describe().T.reset_index().rename(columns={"index": "komponen_weighted"})
                st.dataframe(format_dataframe_for_display(statw), use_container_width=True, height=360)
            else:
                st.info("Kolom weighted belum ditemukan.")
