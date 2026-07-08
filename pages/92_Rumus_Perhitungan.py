from __future__ import annotations
import json
import pandas as pd
import streamlit as st
from scoring.io import (
    has_scored_data, has_raw_data, load_parquet, save_parquet,
    RAW_PARQUET, SCORED_PARQUET, load_formula_params, save_formula_params,
    load_scoring_settings, save_scoring_settings, FORMULA_PARAMS_JSON,
    load_data_quality_rules, save_data_quality_rules, DATA_QUALITY_RULES_JSON
)
from scoring.scoring_engine import (
    FORMULA_TYPES, compute_indicators, compute_scores_dynamic,
    build_formula_summary, get_formula_catalog
)
from scoring.formatting import format_dataframe_for_display, format_metric_value

st.title("🔐 Admin - Rumus Perhitungan Dinamis")
st.info("Di menu ini Bapak bisa mengubah rumus, bobot, checklist aktif/nonaktif, angka internal seperti RB/RR/Sedang, bobot fasilitas, bobot produksi-lahan, nilai YA/TIDAK, dan penalti kualitas data. Setelah edit, klik **Simpan + Hitung Ulang**.")

if not has_raw_data() and not has_scored_data():
    st.warning("Belum ada data. Upload dan proses Excel dulu.")
    st.stop()

# Use raw data if available so recalculation starts from clean source, not from already-scored data.
df = load_parquet(RAW_PARQUET if has_raw_data() else SCORED_PARQUET)
params = load_formula_params()
rules = load_data_quality_rules()
settings = load_scoring_settings()
indicator_df = compute_indicators(df, scoring_settings=settings)
available_cols = list(indicator_df.columns)

with st.expander("📘 Panduan cepat membaca halaman ini", expanded=False):
    st.markdown("""
    **active** = parameter ikut dihitung atau tidak.  
    **weight** = bobot pengaruh parameter terhadap `raw_score`. Total bobot tidak wajib 100 karena aplikasi menormalisasi otomatis.  
    **formula_type** = jenis rumus. Pilih dari katalog, jangan mengetik formula bebas.  
    **source_columns** = nama kolom yang dibaca. Bisa kolom Excel asli atau kolom turunan seperti `persen_rusak_berat`, `biaya_per_km_miliar`, `produksi_total_ton_tahun`.  
    **settings_json** = isi detail rumus. Di sinilah angka seperti `RB=1.0`, `RR=0.6`, `Sedang=0.25` diubah.

    Contoh mengubah rumus kondisi jalan:
    ```json
    {"weights":{"persen_rusak_berat":1.2,"persen_rusak_ringan":0.7,"persen_sedang":0.15},"clip_min":0,"clip_max":100}
    ```
    """)

with st.expander("📘 Katalog tipe rumus dan contoh settings_json", expanded=False):
    st.dataframe(format_dataframe_for_display(get_formula_catalog()), use_container_width=True, height=420)

st.subheader("⚙️ Pengaturan Kebijakan Awal Perhitungan")
st.caption("Pengaturan ini mengubah cara aplikasi menyiapkan data sebelum rumus scoring dihitung. Setelah diubah, klik Simpan + Hitung Ulang.")

with st.expander("Apa fungsi pengaturan ini?", expanded=False):
    st.markdown("""
    - **Penalti kualitas data**: jika dimatikan, data kosong tidak mengurangi `final_score`; tetapi skor parameter yang kosong tetap bisa 0.
    - **Panjang KML/KMZ kosong**: bisa tetap dipenalti, diabaikan, atau otomatis memakai `Panjang Koridor`.
    - **Normalisasi kondisi**: jika Baik+Sedang+RR+RB tidak sama dengan Panjang Koridor, aplikasi bisa men-scale semua kondisi agar totalnya sama dengan panjang.
    - **Mode biaya**: biaya bisa memakai nilai Excel, dihitung dari kondisi jalan, atau dihitung dari kondisi hanya jika biaya Excel kosong/0.
    - **Nama Koridor kosong**: bisa dipenalti, atau dikesampingkan dengan memakai `No. Koridor` sebagai label.
    - **Tematik kosong**: bisa hanya mengurangi skor Tematik, atau sekaligus menjadi penalti data.
    """)

c1, c2, c3 = st.columns(3)
with c1:
    use_data_quality_penalty = st.checkbox(
        "Aktifkan penalti kualitas data",
        value=bool(settings.get("use_data_quality_penalty", True)),
        help="Jika dimatikan, final_score = raw_score. Parameter kosong tetap bisa bernilai 0 sesuai rumusnya.",
    )
    penalty_factor = st.number_input(
        "Faktor pengali penalti",
        min_value=0.0,
        max_value=1.0,
        value=float(settings.get("penalty_factor", 0.30)),
        step=0.05,
        format="%.2f",
        disabled=not use_data_quality_penalty,
        help="Final Score = Raw Score - Data Quality Penalty x faktor ini.",
    )
    name_policy = st.selectbox(
        "Nama Koridor kosong",
        options=["name_or_no_koridor", "require_name"],
        index=["name_or_no_koridor", "require_name"].index(settings.get("name_policy", "name_or_no_koridor")) if settings.get("name_policy", "name_or_no_koridor") in ["name_or_no_koridor", "require_name"] else 0,
        format_func=lambda x: "Gunakan No. Koridor jika Nama Koridor kosong" if x == "name_or_no_koridor" else "Nama Koridor wajib, kosong kena penalti",
        help="Jika memakai No. Koridor, penalti Nama Koridor kosong otomatis dikesampingkan.",
    )

with c2:
    kml_missing_policy = st.selectbox(
        "Jika Panjang KML/KMZ kosong",
        options=["penalize", "use_corridor_length", "ignore"],
        index=["penalize", "use_corridor_length", "ignore"].index(settings.get("kml_missing_policy", "penalize")) if settings.get("kml_missing_policy", "penalize") in ["penalize", "use_corridor_length", "ignore"] else 0,
        format_func=lambda x: {
            "penalize": "Kosong dianggap masalah dan bisa kena penalti",
            "use_corridor_length": "Pakai Panjang Koridor sebagai pengganti KML/KMZ",
            "ignore": "Abaikan KML/KMZ kosong dari penalti",
        }[x],
        help="Jika memilih pakai Panjang Koridor, score KML tidak turun hanya karena KML kosong.",
    )
    condition_length_mode = st.selectbox(
        "Jika total kondisi ≠ Panjang Koridor",
        options=["normalize_to_corridor_length", "raw"],
        index=["normalize_to_corridor_length", "raw"].index(settings.get("condition_length_mode", "normalize_to_corridor_length")) if settings.get("condition_length_mode", "normalize_to_corridor_length") in ["normalize_to_corridor_length", "raw"] else 0,
        format_func=lambda x: "Normalisasi kondisi terhadap Panjang Koridor" if x == "normalize_to_corridor_length" else "Pakai angka kondisi mentah dari Excel",
        help="Normalisasi membuat Baik+Sedang+RR+RB diproporsikan agar sama dengan Panjang Koridor.",
    )
    tematik_missing_policy = st.selectbox(
        "Jika Tematik kosong",
        options=["score_and_penalty", "score_only"],
        index=["score_and_penalty", "score_only"].index(settings.get("tematik_missing_policy", "score_and_penalty")) if settings.get("tematik_missing_policy", "score_and_penalty") in ["score_and_penalty", "score_only"] else 0,
        format_func=lambda x: "Skor Tematik turun + tetap masuk penalti data" if x == "score_and_penalty" else "Hanya skor Tematik turun, tidak jadi penalti data",
        help="Saran: untuk tematik kosong, minimal skor Tematik harus 0. Penalti tambahan bisa diaktif/nonaktifkan.",
    )

with c3:
    cost_mode = st.selectbox(
        "Sumber biaya untuk biaya/km",
        options=["excel_total", "condition_based", "condition_if_excel_missing"],
        index=["excel_total", "condition_based", "condition_if_excel_missing"].index(settings.get("cost_mode", "excel_total")) if settings.get("cost_mode", "excel_total") in ["excel_total", "condition_based", "condition_if_excel_missing"] else 0,
        format_func=lambda x: {
            "excel_total": "Pakai Biaya Excel",
            "condition_based": "Hitung semua biaya dari kondisi jalan",
            "condition_if_excel_missing": "Pakai Excel; jika kosong, hitung dari kondisi",
        }[x],
        help="Jika biaya dihitung dari kondisi, isi biaya per km untuk Baik/Sedang/Rusak Ringan/Rusak Berat di bawah.",
    )
    st.write("Biaya kondisi, Rp miliar/km")
    unit_cost = settings.get("unit_cost_miliar_per_km", {}) or {}
    biaya_baik = st.number_input("Baik", min_value=0.0, value=float(unit_cost.get("baik", 0.0)), step=0.1, format="%.3f", help="Jika ini 0, koridor yang 100% Baik bisa tetap menghasilkan biaya 0 saat mode biaya berbasis kondisi.")
    biaya_sedang = st.number_input("Sedang", min_value=0.0, value=float(unit_cost.get("sedang", 0.5)), step=0.1, format="%.3f")
    biaya_rr = st.number_input("Rusak Ringan", min_value=0.0, value=float(unit_cost.get("rusak_ringan", 1.5)), step=0.1, format="%.3f")
    biaya_rb = st.number_input("Rusak Berat", min_value=0.0, value=float(unit_cost.get("rusak_berat", 3.0)), step=0.1, format="%.3f")

st.markdown("---")
st.subheader("🩺 Penanganan Biaya 0 Setelah Hitung Kondisi")
st.caption("Dipakai jika biaya dihitung dari kondisi jalan tetapi hasilnya masih 0, misalnya koridor 100% Baik sementara biaya Baik = 0.")
zc1, zc2, zc3 = st.columns(3)
with zc1:
    condition_cost_zero_policy = st.selectbox(
        "Jika estimasi biaya kondisi tetap 0",
        options=["allow_zero", "use_fallback_condition", "minimum_cost"],
        index=["allow_zero", "use_fallback_condition", "minimum_cost"].index(settings.get("condition_cost_zero_policy", "allow_zero")) if settings.get("condition_cost_zero_policy", "allow_zero") in ["allow_zero", "use_fallback_condition", "minimum_cost"] else 0,
        format_func=lambda x: {
            "allow_zero": "Biarkan 0",
            "use_fallback_condition": "Pakai Panjang Koridor × biaya kondisi fallback",
            "minimum_cost": "Pakai minimum biaya per koridor",
        }[x],
        help="Kalau masih ada biaya 0 karena kondisi seluruhnya Baik dan biaya Baik=0, pilih fallback atau minimum cost.",
    )
with zc2:
    condition_cost_zero_fallback_condition = st.selectbox(
        "Kondisi fallback",
        options=["baik", "sedang", "rusak_ringan", "rusak_berat"],
        index=["baik", "sedang", "rusak_ringan", "rusak_berat"].index(settings.get("condition_cost_zero_fallback_condition", "sedang")) if settings.get("condition_cost_zero_fallback_condition", "sedang") in ["baik", "sedang", "rusak_ringan", "rusak_berat"] else 1,
        format_func=lambda x: {"baik":"Baik", "sedang":"Sedang", "rusak_ringan":"Rusak Ringan", "rusak_berat":"Rusak Berat"}[x],
        disabled=condition_cost_zero_policy != "use_fallback_condition",
        help="Contoh: kalau pilih Sedang, biaya fallback = Panjang Koridor × biaya Sedang per km.",
    )
with zc3:
    condition_cost_zero_minimum_miliar = st.number_input(
        "Minimum biaya per koridor, Rp miliar",
        min_value=0.0,
        value=float(settings.get("condition_cost_zero_minimum_miliar", 0.0)),
        step=0.1,
        format="%.3f",
        disabled=condition_cost_zero_policy != "minimum_cost",
        help="Dipakai hanya jika estimasi biaya kondisi masih 0 dan panjang koridor > 0.",
    )

new_settings = {
    "use_data_quality_penalty": bool(use_data_quality_penalty),
    "penalty_factor": float(penalty_factor) if use_data_quality_penalty else 0.0,
    "kml_missing_policy": kml_missing_policy,
    "condition_length_mode": condition_length_mode,
    "cost_mode": cost_mode,
    "unit_cost_miliar_per_km": {
        "baik": float(biaya_baik),
        "sedang": float(biaya_sedang),
        "rusak_ringan": float(biaya_rr),
        "rusak_berat": float(biaya_rb),
    },
    "condition_cost_zero_policy": condition_cost_zero_policy,
    "condition_cost_zero_fallback_condition": condition_cost_zero_fallback_condition,
    "condition_cost_zero_minimum_miliar": float(condition_cost_zero_minimum_miliar),
    "name_policy": name_policy,
    "tematik_missing_policy": tematik_missing_policy,
}

st.code("final_score = raw_score - (data_quality_penalty × penalty_factor)")

st.subheader("Ringkasan Rumus Saat Ini")
summary = build_formula_summary(params)
st.dataframe(format_dataframe_for_display(summary), use_container_width=True, height=360)

st.subheader("Editor Rumus / Parameter Penilaian")
st.caption("Tip: untuk mengganti RB/RR/Sedang, edit baris `kondisi_jalan`, kolom `settings_json`, bagian `weights`.")

edit_df = pd.DataFrame(params)
base_cols = ["id", "active", "group", "name", "formula_type", "source_columns", "weight", "cap_quantile", "settings_json", "description"]
if edit_df.empty:
    edit_df = pd.DataFrame(columns=base_cols)
for col in base_cols:
    if col not in edit_df.columns:
        if col == "active":
            edit_df[col] = True
        elif col in ["weight", "cap_quantile"]:
            edit_df[col] = 0.0
        elif col == "settings_json":
            edit_df[col] = "{}"
        else:
            edit_df[col] = ""
edit_df["source_columns"] = edit_df["source_columns"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
edit_df["settings_json"] = edit_df["settings_json"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else (x if str(x).strip() else "{}"))

edited = st.data_editor(
    edit_df[base_cols],
    use_container_width=True,
    num_rows="dynamic",
    height=560,
    column_config={
        "id": st.column_config.TextColumn("ID", help="Harus unik. Contoh: kondisi_jalan, sppg, biaya_per_km."),
        "active": st.column_config.CheckboxColumn("Aktif", default=True, help="Centang jika parameter ikut dinilai."),
        "group": st.column_config.TextColumn("Grup", help="Kelompok indikator: Eligibility, Kondisi, Konektivitas, Ekonomi, dll."),
        "name": st.column_config.TextColumn("Nama Parameter"),
        "formula_type": st.column_config.SelectboxColumn("Tipe Rumus", options=list(FORMULA_TYPES.keys()), required=True),
        "source_columns": st.column_config.TextColumn("Kolom Sumber", help="Bisa lebih dari satu, pisahkan dengan koma."),
        "weight": st.column_config.NumberColumn("Bobot", min_value=0.0, step=1.0, format="%.2f"),
        "cap_quantile": st.column_config.NumberColumn("Cap Quantile", min_value=0.0, max_value=1.0, step=0.01, format="%.2f", help="Pemotong outlier untuk normalisasi. Umumnya 0.95."),
        "settings_json": st.column_config.TextColumn("settings_json", help="Detail rumus dalam format JSON. Contoh: {\"rb_weight\":1.0}."),
        "description": st.column_config.TextColumn("Catatan"),
    },
)

with st.expander("🧾 Kolom yang tersedia untuk rumus", expanded=False):
    col_search = st.text_input("Cari nama kolom")
    cols_show = [c for c in available_cols if col_search.lower() in c.lower()] if col_search else available_cols
    st.dataframe(pd.DataFrame({"kolom_tersedia": cols_show}), use_container_width=True, height=360)

st.subheader("Editor Penalti Kualitas Data")
st.caption("Penalti mengurangi final score. Ini juga bagian dari rumus akhir dan bisa Bapak ubah.")
rule_df = pd.DataFrame(rules)
rule_cols = ["id", "active", "name", "rule_type", "source_columns", "penalty", "settings_json"]
for col in rule_cols:
    if col not in rule_df.columns:
        if col == "active":
            rule_df[col] = True
        elif col == "penalty":
            rule_df[col] = 0.0
        elif col == "settings_json":
            rule_df[col] = "{}"
        else:
            rule_df[col] = ""
rule_df["source_columns"] = rule_df["source_columns"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
rule_df["settings_json"] = rule_df["settings_json"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else (x if str(x).strip() else "{}"))

edited_rules = st.data_editor(
    rule_df[rule_cols],
    use_container_width=True,
    num_rows="dynamic",
    height=300,
    column_config={
        "id": st.column_config.TextColumn("ID"),
        "active": st.column_config.CheckboxColumn("Aktif", default=True),
        "name": st.column_config.TextColumn("Nama Penalti"),
        "rule_type": st.column_config.SelectboxColumn("Tipe Penalti", options=["blank", "nonpositive", "condition_length_mismatch"], required=True),
        "source_columns": st.column_config.TextColumn("Kolom Sumber"),
        "penalty": st.column_config.NumberColumn("Nilai Penalti", min_value=0.0, max_value=100.0, step=1.0, format="%.2f"),
        "settings_json": st.column_config.TextColumn("settings_json"),
    },
)

def _parse_json_cell(value, row_label: str, errors: list[str]) -> dict:
    if isinstance(value, dict):
        return value
    txt = str(value or "{}").strip()
    if not txt:
        return {}
    try:
        parsed = json.loads(txt)
        if not isinstance(parsed, dict):
            errors.append(f"settings_json pada {row_label} harus objek JSON, bukan list/string.")
            return {}
        return parsed
    except Exception as e:
        errors.append(f"settings_json tidak valid pada {row_label}: {e}")
        return {}


def table_to_params(table: pd.DataFrame) -> tuple[list[dict], list[str]]:
    clean = []
    errors = []
    for i, row in table.iterrows():
        pid = str(row.get("id", "")).strip()
        name = str(row.get("name", "")).strip()
        if not pid and not name:
            continue
        if not pid:
            pid = name.lower().replace(" ", "_")
        cols = [c.strip() for c in str(row.get("source_columns", "")).split(",") if c.strip()]
        try:
            weight = float(row.get("weight", 0) or 0)
        except Exception:
            weight = 0.0
        try:
            cap = float(row.get("cap_quantile", 0.95) or 0.95)
        except Exception:
            cap = 0.95
        row_label = pid or f"baris {i+1}"
        settings_obj = _parse_json_cell(row.get("settings_json", "{}"), row_label, errors)
        clean.append({
            "id": pid,
            "active": bool(row.get("active", True)),
            "group": str(row.get("group", "")).strip(),
            "name": name or pid,
            "formula_type": str(row.get("formula_type", "exists")).strip(),
            "source_columns": cols,
            "weight": weight,
            "cap_quantile": cap,
            "settings_json": settings_obj,
            "description": str(row.get("description", "")).strip(),
        })
    return clean, errors


def table_to_rules(table: pd.DataFrame) -> tuple[list[dict], list[str]]:
    clean = []
    errors = []
    for i, row in table.iterrows():
        rid = str(row.get("id", "")).strip()
        name = str(row.get("name", "")).strip()
        if not rid and not name:
            continue
        if not rid:
            rid = name.lower().replace(" ", "_")
        cols = [c.strip() for c in str(row.get("source_columns", "")).split(",") if c.strip()]
        try:
            penalty = float(row.get("penalty", 0) or 0)
        except Exception:
            penalty = 0.0
        row_label = rid or f"baris penalti {i+1}"
        settings_obj = _parse_json_cell(row.get("settings_json", "{}"), row_label, errors)
        clean.append({
            "id": rid,
            "active": bool(row.get("active", True)),
            "name": name or rid,
            "rule_type": str(row.get("rule_type", "blank")).strip(),
            "source_columns": cols,
            "penalty": penalty,
            "settings_json": settings_obj,
        })
    return clean, errors


def validate_params(new_params: list[dict], parse_errors: list[str]) -> list[str]:
    errors = list(parse_errors)
    ids = [p["id"] for p in new_params]
    dup = sorted({x for x in ids if ids.count(x) > 1})
    if dup:
        errors.append(f"ID parameter duplikat: {', '.join(dup)}")
    active_weight = sum(float(p.get("weight", 0) or 0) for p in new_params if bool(p.get("active", True)))
    if active_weight <= 0:
        errors.append("Minimal harus ada satu rumus aktif dengan bobot lebih besar dari 0.")
    for p in new_params:
        ft = p.get("formula_type")
        if ft not in FORMULA_TYPES:
            errors.append(f"Tipe rumus tidak dikenal pada {p.get('id')}: {ft}")
        for col in p.get("source_columns", []):
            if col and col not in available_cols:
                errors.append(f"Kolom sumber tidak ditemukan untuk {p.get('id')}: {col}")
    return errors


def validate_rules(new_rules: list[dict], parse_errors: list[str]) -> list[str]:
    errors = list(parse_errors)
    valid_types = {"blank", "nonpositive", "condition_length_mismatch"}
    ids = [r["id"] for r in new_rules]
    dup = sorted({x for x in ids if ids.count(x) > 1})
    if dup:
        errors.append(f"ID penalti duplikat: {', '.join(dup)}")
    for r in new_rules:
        if r.get("rule_type") not in valid_types:
            errors.append(f"Tipe penalti tidak dikenal pada {r.get('id')}: {r.get('rule_type')}")
        for col in r.get("source_columns", []):
            if col and col not in available_cols:
                errors.append(f"Kolom penalti tidak ditemukan untuk {r.get('id')}: {col}")
    return errors

new_params, parse_errors = table_to_params(edited)
new_rules, rule_parse_errors = table_to_rules(edited_rules)
errors = validate_params(new_params, parse_errors) + validate_rules(new_rules, rule_parse_errors)

with st.expander("🔎 Diagnosa sementara biaya 0", expanded=False):
    try:
        tmp = compute_scores_dynamic(df, new_params, penalty_factor=float(new_settings.get("penalty_factor", 0.0)), data_quality_rules=new_rules, scoring_settings=new_settings)
        zero_cost = tmp[pd.to_numeric(tmp.get("biaya_aktif_miliar"), errors="coerce").fillna(0) <= 0]
        st.write(f"Jumlah koridor dengan biaya aktif 0/kosong: **{format_metric_value(len(zero_cost), kind='int')}**")
        if len(zero_cost):
            cols_diag = [c for c in ["rank_nasional", "nama_koridor_display", "No. Koridor", "Panjang (KM)", "Baik", "Sedang", "Rusak Ringan", "Rusak Berat", "biaya_estimasi_kondisi_awal_miliar", "biaya_estimasi_kondisi_miliar", "biaya_aktif_miliar", "biaya_sumber", "biaya_nol_reason"] if c in zero_cost.columns]
            st.dataframe(format_dataframe_for_display(zero_cost[cols_diag].head(100)), use_container_width=True, height=300)
    except Exception as e:
        st.warning(f"Diagnosa belum bisa dihitung karena konfigurasi belum valid: {e}")

c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1.2])
with c1:
    save_clicked = st.button("💾 Simpan Rumus", type="primary")
with c2:
    recalc_clicked = st.button("🔁 Simpan + Hitung Ulang")
with c3:
    st.download_button(
        "Download JSON Rumus",
        data=json.dumps(new_params, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name="formula_parameters.json",
        mime="application/json",
    )
with c4:
    st.download_button(
        "Download JSON Penalti",
        data=json.dumps(new_rules, indent=2, ensure_ascii=False).encode("utf-8"),
        file_name="data_quality_rules.json",
        mime="application/json",
    )

if errors:
    st.error("Masih ada masalah konfigurasi rumus/penalti:")
    for e in errors[:40]:
        st.write(f"- {e}")
    if len(errors) > 40:
        st.write(f"...dan {len(errors)-40} error lain.")
else:
    st.success("Konfigurasi rumus dan penalti valid.")

if save_clicked or recalc_clicked:
    if errors:
        st.stop()
    save_formula_params(new_params)
    save_data_quality_rules(new_rules)
    save_scoring_settings(new_settings)
    st.success(f"Rumus tersimpan ke `{FORMULA_PARAMS_JSON}` dan penalti tersimpan ke `{DATA_QUALITY_RULES_JSON}`. Backup otomatis dibuat dengan ekstensi `.bak`.")

if recalc_clicked:
    if errors:
        st.stop()
    scored = compute_scores_dynamic(df, new_params, penalty_factor=float(new_settings.get("penalty_factor", 0.0)), data_quality_rules=new_rules, scoring_settings=new_settings)
    save_parquet(scored, SCORED_PARQUET)
    st.success("Ranking berhasil dihitung ulang memakai rumus terbaru.")
    st.dataframe(format_dataframe_for_display(scored.sort_values("final_score", ascending=False).head(50)), use_container_width=True, height=420)
