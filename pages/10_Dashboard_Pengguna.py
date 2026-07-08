from __future__ import annotations
from io import BytesIO

import pandas as pd
import streamlit as st

from scoring.io import has_scored_data, load_parquet
from scoring.schema import COL
from scoring.scoring_engine import export_columns, get_score_component_columns
from scoring.formatting import format_dataframe_for_display, format_metric_value

st.title("👤 Dashboard Pengguna - Penilaian Koridor Prioritas")
st.info("Dashboard ini memakai **Biaya Aktif** sebagai biaya resmi untuk scoring. Jika mode biaya di Admin diset ke `Hitung semua biaya dari kondisi jalan`, maka Biaya Aktif berasal dari hitungan kondisi jalan. Kolom audit seperti biaya Excel asli dan biaya sumber disembunyikan dari tabel pengguna agar tidak membingungkan.")

if not has_scored_data():
    st.warning("Belum ada data scoring. Buka halaman Upload Data lalu proses Excel agregasi koridor.")
    st.stop()

@st.cache_data(show_spinner=False)
def load_data_cached() -> pd.DataFrame:
    return load_parquet()


def safe_unique(df: pd.DataFrame, col: str) -> list:
    if col not in df.columns:
        return []
    return sorted([x for x in df[col].dropna().unique().tolist() if str(x).strip()])


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "ranking") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
        wb = writer.book
        ws = writer.sheets[sheet_name[:31]]
        header_fmt = wb.add_format({"bold": True, "text_wrap": True, "valign": "top", "border": 1})
        num_fmt = wb.add_format({"num_format": "#,##0.00"})
        int_fmt = wb.add_format({"num_format": "#,##0"})
        pct_fmt = wb.add_format({"num_format": "0.00%"})
        from scoring.formatting import column_format_kind
        for col_num, value in enumerate(df.columns.values):
            ws.write(0, col_num, value, header_fmt)
            width = min(max(len(str(value)) + 2, 12), 42)
            kind, decimals, _, suffix = column_format_kind(str(value))
            if kind == "int":
                ws.set_column(col_num, col_num, width, int_fmt)
            elif suffix == "%":
                ws.set_column(col_num, col_num, width, num_fmt)
            elif kind == "number":
                ws.set_column(col_num, col_num, width, num_fmt)
            else:
                ws.set_column(col_num, col_num, width)
        ws.freeze_panes(1, 0)
    return output.getvalue()


df = load_data_cached()

# Ensure expected score cols exist.
for c in ["final_score", "raw_score", "data_quality_penalty"]:
    if c not in df.columns:
        st.error(f"Kolom `{c}` belum ada. Hitung ulang scoring dulu.")
        st.stop()

with st.sidebar:
    st.header("🔎 Filter Dashboard")
    st.caption("Filter di sini langsung memengaruhi grafik, tabel, dan file download.")

    search = st.text_input("Cari teks", help="Cari di ID Koridor, Nama Koridor, Provinsi, Kabupaten/Kota, Tematik, atau Jenis Produksi.")

    provs = safe_unique(df, COL["provinsi"])
    selected_prov = st.multiselect("Provinsi", provs, help="Kosongkan untuk semua provinsi.")

    if selected_prov and COL["kabupaten"] in df.columns:
        kab_options = safe_unique(df.loc[df[COL["provinsi"]].isin(selected_prov)], COL["kabupaten"])
    else:
        kab_options = safe_unique(df, COL["kabupaten"])
    selected_kab = st.multiselect("Kabupaten/Kota", kab_options)

    kategori = st.multiselect("Kategori Prioritas", safe_unique(df, "kategori_prioritas"))
    tematik = st.multiselect("Tematik", safe_unique(df, COL["tematik"]), help="Filter tematik jika kolom tersedia.")
    jenis_produksi = st.multiselect("Jenis Produksi", safe_unique(df, COL["jenis_produksi"]), help="Filter jenis produksi jika kolom tersedia.")

    min_score = float(df["final_score"].min()) if len(df) else 0.0
    max_score = float(df["final_score"].max()) if len(df) else 100.0
    score_range = st.slider("Rentang Final Score", 0.0, 100.0, (max(0.0, min_score), min(100.0, max_score)), step=1.0)

    top_n = st.number_input("Jumlah baris Top/Bottom", min_value=5, max_value=500, value=50, step=5)
    sort_col_options = [c for c in ["final_score", "raw_score", "data_quality_penalty", "rank_nasional", "biaya_per_km_miliar", COL["panjang"], COL["biaya"], "persen_rusak_total"] if c in df.columns]
    sort_col = st.selectbox("Urut berdasarkan", sort_col_options, index=sort_col_options.index("final_score") if "final_score" in sort_col_options else 0)
    ascending = st.checkbox("Urut kecil ke besar", value=False, help="Centang untuk melihat skor/biaya/rank terkecil dulu.")

f = df.copy()
if selected_prov:
    f = f[f[COL["provinsi"]].isin(selected_prov)]
if selected_kab:
    f = f[f[COL["kabupaten"]].isin(selected_kab)]
if kategori:
    f = f[f["kategori_prioritas"].isin(kategori)]
if tematik and COL["tematik"] in f.columns:
    f = f[f[COL["tematik"]].isin(tematik)]
if jenis_produksi and COL["jenis_produksi"] in f.columns:
    f = f[f[COL["jenis_produksi"]].isin(jenis_produksi)]
f = f[(f["final_score"] >= score_range[0]) & (f["final_score"] <= score_range[1])]

if search.strip():
    search_cols = [c for c in [COL["id_koridor"], COL["nama_koridor"], COL["provinsi"], COL["kabupaten"], COL["tematik"], COL["jenis_produksi"], COL["status_pengajuan"]] if c in f.columns]
    mask = pd.Series(False, index=f.index)
    q = search.strip().lower()
    for c in search_cols:
        mask = mask | f[c].fillna("").astype(str).str.lower().str.contains(q, regex=False)
    f = f[mask]

m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("Koridor", format_metric_value(f.shape[0], kind="int"))
m2.metric("Panjang KM", format_metric_value(f[COL['panjang']].sum(), decimals=2) if COL["panjang"] in f.columns else "0")
m3.metric("Biaya Aktif Rp M", format_metric_value(f['biaya_aktif_miliar'].sum(), decimals=2) if "biaya_aktif_miliar" in f.columns else (format_metric_value(f[COL['biaya']].sum(), decimals=2) if COL["biaya"] in f.columns else "0"))
m4.metric("Final Score Rata-rata", format_metric_value(f['final_score'].mean(), decimals=2) if len(f) else "0")
m5.metric("Prioritas Tinggi+", format_metric_value(int(f["kategori_prioritas"].isin(["Tinggi", "Sangat Tinggi"]).sum()), kind="int") if "kategori_prioritas" in f.columns else "0")
m6.metric("Rata-rata Penalti", format_metric_value(f['data_quality_penalty'].mean(), decimals=2) if len(f) else "0")
m7.metric("Biaya 0", format_metric_value(int((pd.to_numeric(f.get("biaya_aktif_miliar"), errors="coerce").fillna(0) <= 0).sum()), kind="int") if "biaya_aktif_miliar" in f.columns else "0")

st.divider()

tab_overview, tab_ranking, tab_komponen, tab_rekap, tab_query, tab_export = st.tabs([
    "📊 Overview", "🏆 Ranking", "🧮 Komponen Skor", "🗺️ Rekap Wilayah", "🔍 Query Builder", "⬇️ Export"
])

with tab_overview:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Top Ranking Berdasarkan Filter")
        top = f.sort_values(sort_col, ascending=ascending).head(int(top_n))
        if len(top):
            chart_name_col = "nama_koridor_display" if "nama_koridor_display" in top.columns else (COL["nama_koridor"] if COL["nama_koridor"] in top.columns else COL["id_koridor"])
            st.bar_chart(top.set_index(chart_name_col)["final_score"])
        else:
            st.warning("Tidak ada data setelah filter.")
    with right:
        st.subheader("Komposisi Kategori")
        if "kategori_prioritas" in f.columns and len(f):
            st.dataframe(format_dataframe_for_display(f["kategori_prioritas"].value_counts().rename_axis("Kategori").reset_index(name="Jumlah")), use_container_width=True)
        st.subheader("Distribusi Score")
        if len(f):
            st.line_chart(f["final_score"].sort_values(ascending=False).reset_index(drop=True))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top Provinsi by Rata-rata Score")
        if COL["provinsi"] in f.columns and len(f):
            prov_summary = f.groupby(COL["provinsi"], dropna=False).agg(
                jumlah_koridor=("final_score", "size"),
                avg_score=("final_score", "mean"),
                max_score=("final_score", "max"),
                total_panjang=(COL["panjang"], "sum") if COL["panjang"] in f.columns else ("final_score", "size"),
                total_biaya=("biaya_aktif_miliar", "sum") if "biaya_aktif_miliar" in f.columns else ((COL["biaya"], "sum") if COL["biaya"] in f.columns else ("final_score", "size")),
            ).reset_index().sort_values("avg_score", ascending=False)
            st.dataframe(format_dataframe_for_display(prov_summary.head(20)), use_container_width=True, height=360)
    with c2:
        st.subheader("Koridor Penalti Tertinggi")
        penalty_cols = [c for c in [COL["provinsi"], COL["kabupaten"], "nama_koridor_display", "data_quality_penalty", "final_score", COL["panjang"], "biaya_aktif_miliar", "panjang_kml_used_km"] if c in f.columns]
        st.dataframe(format_dataframe_for_display(f.sort_values("data_quality_penalty", ascending=False)[penalty_cols].head(20)), use_container_width=True, height=300)

        with st.expander("Diagnostik biaya aktif 0 / audit biaya", expanded=False):
            st.caption("Bagian ini hanya audit. Untuk ranking, aplikasi memakai kolom `biaya_aktif_miliar`, bukan biaya Excel asli jika mode biaya berbasis kondisi jalan.")
            if "biaya_aktif_miliar" in f.columns:
                zero = f[pd.to_numeric(f["biaya_aktif_miliar"], errors="coerce").fillna(0) <= 0]
                zero_cols = [c for c in [COL["provinsi"], COL["kabupaten"], "nama_koridor_display", COL["panjang"], "Baik", "Sedang", "Rusak Ringan", "Rusak Berat", "biaya_estimasi_kondisi_miliar", "biaya_aktif_miliar", "biaya_sumber", "biaya_nol_reason"] if c in zero.columns]
                st.dataframe(format_dataframe_for_display(zero[zero_cols].head(50)), use_container_width=True, height=260)

with tab_ranking:
    st.subheader("Daftar Urutan dan Nilai Koridor")
    st.caption("Gunakan filter sidebar, pencarian, sort, dan pilihan kolom. Semua tampilan bisa diexport di tab Export.")
    default_show = export_columns(f).sort_values(sort_col if sort_col in f.columns else "final_score", ascending=ascending)
    all_cols = list(default_show.columns)
    selected_cols = st.multiselect("Pilih kolom tabel", all_cols, default=all_cols[:min(len(all_cols), 28)])
    if selected_cols:
        st.dataframe(format_dataframe_for_display(default_show[selected_cols].head(5000)), use_container_width=True, height=620)
    else:
        st.warning("Pilih minimal satu kolom.")

with tab_komponen:
    st.subheader("Analisis Komponen Skor")
    score_cols = [c for c in f.columns if c.startswith("score__")]
    weighted_cols = [c for c in f.columns if c.startswith("weighted__")]
    if not score_cols:
        st.warning("Belum ada kolom score dinamis. Hitung ulang scoring dulu.")
    else:
        component_view = st.radio("Tampilan", ["Rata-rata komponen", "Top koridor per komponen", "Tabel semua komponen"], horizontal=True)
        if component_view == "Rata-rata komponen":
            comp = f[score_cols].mean().sort_values(ascending=False).reset_index()
            comp.columns = ["komponen", "rata_rata_score"]
            st.bar_chart(comp.set_index("komponen")["rata_rata_score"])
            st.dataframe(format_dataframe_for_display(comp), use_container_width=True)
        elif component_view == "Top koridor per komponen":
            chosen_score = st.selectbox("Pilih komponen", score_cols)
            cols = [c for c in [COL["provinsi"], COL["kabupaten"], COL["nama_koridor"], chosen_score, "final_score", "rank_nasional"] if c in f.columns]
            st.dataframe(format_dataframe_for_display(f.sort_values(chosen_score, ascending=False)[cols].head(int(top_n))), use_container_width=True, height=600)
        else:
            base_cols = [c for c in ["rank_nasional", COL["provinsi"], COL["kabupaten"], "nama_koridor_display", COL["nama_koridor"], "final_score", "raw_score", "data_quality_penalty", "biaya_aktif_miliar"] if c in f.columns]
            st.dataframe(format_dataframe_for_display(f[base_cols + score_cols + weighted_cols].sort_values("final_score", ascending=False).head(3000)), use_container_width=True, height=620)

with tab_rekap:
    st.subheader("Rekap Wilayah")
    group_level = st.radio("Level rekap", ["Provinsi", "Kabupaten/Kota", "Provinsi + Kabupaten/Kota"], horizontal=True)
    if group_level == "Provinsi":
        groups = [COL["provinsi"]]
    elif group_level == "Kabupaten/Kota":
        groups = [COL["kabupaten"]]
    else:
        groups = [COL["provinsi"], COL["kabupaten"]]
    groups = [g for g in groups if g in f.columns]
    if groups and len(f):
        agg = f.groupby(groups, dropna=False).agg(
            jumlah_koridor=("final_score", "size"),
            avg_score=("final_score", "mean"),
            max_score=("final_score", "max"),
            min_score=("final_score", "min"),
            total_panjang=(COL["panjang"], "sum") if COL["panjang"] in f.columns else ("final_score", "size"),
            total_biaya=("biaya_aktif_miliar", "sum") if "biaya_aktif_miliar" in f.columns else ((COL["biaya"], "sum") if COL["biaya"] in f.columns else ("final_score", "size")),
            avg_penalty=("data_quality_penalty", "mean"),
        ).reset_index().sort_values("avg_score", ascending=False)
        st.dataframe(format_dataframe_for_display(agg), use_container_width=True, height=620)
    else:
        st.warning("Kolom wilayah tidak tersedia atau data kosong.")

with tab_query:
    st.subheader("Query Builder Tanpa SQL")
    st.caption("Ini untuk menyaring hasil lebih spesifik tanpa menulis SQL. Untuk SQL bebas, gunakan menu Query DuckDB.")
    qdf = f.copy()
    numeric_cols = [c for c in qdf.columns if pd.api.types.is_numeric_dtype(qdf[c])]
    text_cols = [c for c in qdf.columns if not pd.api.types.is_numeric_dtype(qdf[c])]

    c1, c2, c3 = st.columns(3)
    with c1:
        num_col = st.selectbox("Kolom angka", numeric_cols, index=numeric_cols.index("final_score") if "final_score" in numeric_cols else 0)
    with c2:
        op = st.selectbox("Operator", [">=", "<=", ">", "<", "=", "!="])
    with c3:
        val = st.number_input("Nilai pembanding", value=float(qdf[num_col].median()) if len(qdf) else 0.0)

    if op == ">=":
        qdf = qdf[qdf[num_col] >= val]
    elif op == "<=":
        qdf = qdf[qdf[num_col] <= val]
    elif op == ">":
        qdf = qdf[qdf[num_col] > val]
    elif op == "<":
        qdf = qdf[qdf[num_col] < val]
    elif op == "=":
        qdf = qdf[qdf[num_col] == val]
    elif op == "!=":
        qdf = qdf[qdf[num_col] != val]

    if text_cols:
        t1, t2 = st.columns(2)
        with t1:
            txt_col = st.selectbox("Kolom teks", text_cols, index=text_cols.index(COL["nama_koridor"]) if COL["nama_koridor"] in text_cols else 0)
        with t2:
            txt_contains = st.text_input("Mengandung teks")
        if txt_contains.strip():
            qdf = qdf[qdf[txt_col].fillna("").astype(str).str.contains(txt_contains.strip(), case=False, regex=False)]

    st.metric("Hasil Query", f"{format_metric_value(len(qdf), kind='int')} baris")
    st.dataframe(format_dataframe_for_display(export_columns(qdf).sort_values("final_score", ascending=False).head(5000)), use_container_width=True, height=520)

with tab_export:
    st.subheader("Export Hasil")
    include_audit_export = st.checkbox("Sertakan kolom audit biaya & setting internal", value=False, help="Centang ini hanya jika perlu mengecek biaya Excel asli, biaya hasil kondisi, sumber biaya, dan alasan biaya 0.")
    export_df = export_columns(f, include_audit=include_audit_export).sort_values(sort_col if sort_col in f.columns else "final_score", ascending=ascending)
    st.write(f"Jumlah baris yang akan diexport: **{format_metric_value(len(export_df), kind='int')}**")
    st.download_button(
        "Download ranking CSV",
        data=export_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="ranking_koridor_prioritas.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download ranking Excel",
        data=to_excel_bytes(export_df, "ranking"),
        file_name="ranking_koridor_prioritas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    with st.expander("Preview export", expanded=False):
        st.dataframe(format_dataframe_for_display(export_df.head(200)), use_container_width=True, height=420)
