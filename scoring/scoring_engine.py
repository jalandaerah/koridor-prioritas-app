from __future__ import annotations
import json
import re
from typing import Any

import pandas as pd
import numpy as np

from .schema import COL, NUMERIC_COLS, PRODUCTION_TYPE_COLS, PRODUCTION_AMOUNT_COLS, LAND_AREA_COLS, PRODUCTION_SLOTS
from .utils import flag_exists, normalize_0_100, inverse_priority_score, EMPTY_MARKERS

DEFAULT_SCORING_SETTINGS = {
    "use_data_quality_penalty": True,
    "penalty_factor": 0.30,
    "kml_missing_policy": "penalize",  # penalize | use_corridor_length | ignore
    "condition_length_mode": "normalize_to_corridor_length",  # raw | normalize_to_corridor_length
    "cost_mode": "excel_total",  # excel_total | condition_based | condition_if_excel_missing
    "unit_cost_miliar_per_km": {
        "baik": 0.0,
        "sedang": 0.5,
        "rusak_ringan": 1.5,
        "rusak_berat": 3.0,
    },
    # What to do when condition-based estimated cost is still 0 while corridor length > 0.
    # allow_zero | use_fallback_condition | minimum_cost
    "condition_cost_zero_policy": "allow_zero",
    "condition_cost_zero_fallback_condition": "sedang",  # baik | sedang | rusak_ringan | rusak_berat
    "condition_cost_zero_minimum_miliar": 0.0,
    "name_policy": "name_or_no_koridor",  # require_name | name_or_no_koridor
    "tematik_missing_policy": "score_and_penalty",  # score_only | score_and_penalty
}

DEFAULT_COMMODITY_WEIGHTS = {
    # Default awal bersifat editable, bukan angka final kebijakan.
    # Ubah bobot ini dari settings_json parameter produksi bila ada prioritas komoditas resmi.
    "padi": 1.50,
    "beras": 1.50,
    "jagung": 1.20,
    "kedelai": 1.25,
    "ubi kayu": 1.05,
    "sagu": 1.05,
    "tebu": 1.10,
    "kelapa sawit": 1.15,
    "kelapa": 1.05,
    "kopi": 1.15,
    "kakao": 1.15,
    "cengkeh": 1.10,
    "lada": 1.10,
    "karet": 1.05,
    "bawang merah": 1.20,
    "cabai": 1.20,
    "sayuran lain": 1.05,
    "perikanan tangkap": 1.25,
    "rumput laut": 1.20,
    "udang": 1.30,
    "sapi potong": 1.25,
    "ayam buras": 1.10,
    "garam": 1.05,
}


def normalize_scoring_settings(settings: dict | None = None) -> dict[str, Any]:
    out = json.loads(json.dumps(DEFAULT_SCORING_SETTINGS))
    if isinstance(settings, dict):
        for k, v in settings.items():
            if k == "unit_cost_miliar_per_km" and isinstance(v, dict):
                out[k].update(v)
            else:
                out[k] = v
    try:
        out["penalty_factor"] = float(out.get("penalty_factor", 0.30))
    except Exception:
        out["penalty_factor"] = 0.30
    out["use_data_quality_penalty"] = bool(out.get("use_data_quality_penalty", True))
    if out.get("condition_cost_zero_fallback_condition") not in {"baik", "sedang", "rusak_ringan", "rusak_berat"}:
        out["condition_cost_zero_fallback_condition"] = "sedang"
    try:
        out["condition_cost_zero_minimum_miliar"] = float(out.get("condition_cost_zero_minimum_miliar", 0.0))
    except Exception:
        out["condition_cost_zero_minimum_miliar"] = 0.0
    if out.get("condition_cost_zero_policy") not in {"allow_zero", "use_fallback_condition", "minimum_cost"}:
        out["condition_cost_zero_policy"] = "allow_zero"
    return out


FORMULA_TYPES: dict[str, dict[str, str]] = {
    "exists": {
        "label": "Cek isi / tidak kosong",
        "formula": "score = 100 jika kolom sumber terisi; selain itu missing_score",
        "notes": "Cocok untuk RPJMN, Tematik, KSPP, atau status yang hanya perlu ada/tidak ada. Bisa atur missing_score lewat settings_json.",
        "settings_example": '{"missing_score": 0}'
    },
    "yes_no": {
        "label": "Cek YA / TIDAK",
        "formula": "score = true_score jika nilai masuk daftar true_values; selain itu false_score",
        "notes": "Cocok untuk konektivitas, koridor awal, checklist. true_values bisa diedit.",
        "settings_example": '{"true_values":["YA","YES","Y","TRUE","1","TERHUBUNG","ADA"],"true_score":100,"false_score":0}'
    },
    "numeric_higher": {
        "label": "Angka semakin besar semakin baik",
        "formula": "score = 100 x (nilai - min) / (max - min)",
        "notes": "Cocok untuk jumlah fasilitas, produksi, penduduk, luas layanan. cap_quantile dan missing_score bisa diedit.",
        "settings_example": '{"cap_quantile":0.95,"missing_score":0}'
    },
    "numeric_lower": {
        "label": "Angka semakin kecil semakin baik",
        "formula": "score = 100 x (max - nilai) / (max - min)",
        "notes": "Cocok untuk biaya, waktu tempuh, jarak ke layanan, atau risiko.",
        "settings_example": '{"cap_quantile":0.95,"missing_score":0}'
    },
    "numeric_lower_positive": {
        "label": "Angka positif semakin kecil semakin baik",
        "formula": "score = 100 x (max - nilai) / (max - min); nilai kosong/0 = zero_or_missing_score",
        "notes": "Cocok untuk biaya per km. Nilai 0 tidak dianggap bagus karena biasanya berarti data belum ada.",
        "settings_example": '{"cap_quantile":0.95,"zero_or_missing_score":0}'
    },
    "rank_lower": {
        "label": "Ranking/prioritas semakin kecil semakin baik",
        "formula": "score = 100 x (rank_maks - rank) / (rank_maks - rank_min)",
        "notes": "Cocok untuk Prioritas Kabupaten/Kota dan Prioritas Provinsi.",
        "settings_example": '{"missing_score":0}'
    },
    "completeness": {
        "label": "Kelengkapan data",
        "formula": "score = complete_score jika kolom sumber terisi; missing_score jika kosong",
        "notes": "Cocok untuk ketersediaan KML, biaya, panjang, atau dokumen pendukung.",
        "settings_example": '{"complete_score":100,"missing_score":0}'
    },
    "weighted_percent_sum": {
        "label": "Rumus persen tertimbang",
        "formula": "score = Σ(kolom_persen x bobot_kolom), lalu dibatasi 0-100",
        "notes": "Cocok untuk kondisi jalan. Contoh: RB% x 1.00 + RR% x 0.60 + Sedang% x 0.25.",
        "settings_example": '{"weights":{"persen_rusak_berat":1.0,"persen_rusak_ringan":0.6,"persen_sedang":0.25},"clip_min":0,"clip_max":100}'
    },
    "condition_urgency": {
        "label": "Urgensi kondisi jalan",
        "formula": "score = RB% x rb_weight + RR% x rr_weight + Sedang% x sedang_weight",
        "notes": "Alias lama untuk weighted_percent_sum. Angka rb_weight/rr_weight/sedang_weight bisa diedit.",
        "settings_example": '{"rb_weight":1.0,"rr_weight":0.6,"sedang_weight":0.25,"clip_max":100}'
    },
    "weighted_sum_higher": {
        "label": "Jumlah tertimbang, semakin besar semakin baik",
        "formula": "score = normalize(Σ(kolom x bobot_kolom))",
        "notes": "Cocok untuk fasilitas publik: pendidikan x1, kesehatan x2, pemerintahan x1, SPPG x3. Bobot kolom bisa diedit.",
        "settings_example": '{"weights":{"Faslilitas Umum Dilewati - Pendidikan":1,"Faslilitas Umum Dilewati - Kesehatan":2,"Faslilitas Umum Dilewati - Pemerintahan":1,"Faslilitas Umum Dilewati - SPPG":3},"cap_quantile":0.95}'
    },
    "weighted_sum_lower": {
        "label": "Jumlah tertimbang, semakin kecil semakin baik",
        "formula": "score = inverse_normalize(Σ(kolom x bobot_kolom))",
        "notes": "Cocok untuk gabungan beberapa indikator risiko/biaya yang makin kecil makin baik.",
        "settings_example": '{"weights":{"kolom_a":1,"kolom_b":2},"cap_quantile":0.95}'
    },
    "economic_combined": {
        "label": "Ekonomi: produksi + luas lahan",
        "formula": "score = normalize(produksi_total) x production_weight + normalize(luas_lahan_total) x land_weight",
        "notes": "Bobot produksi dan lahan bisa diedit. Jika total bobot tidak 1, aplikasi menormalisasi otomatis.",
        "settings_example": '{"production_weight":0.6,"land_weight":0.4,"cap_quantile":0.95}'
    },
    "production_amount_by_type": {
        "label": "Jumlah produksi tertimbang jenis komoditas",
        "formula": "nilai = Σ(jumlah produksi i x bobot jenis produksi i), lalu dinormalisasi 0-100",
        "notes": "Cocok untuk menilai volume produksi dengan bobot komoditas. Padi bisa dibuat lebih tinggi dari jagung, dst.",
        "settings_example": '{"commodity_weights":{"Padi":1.5,"Jagung":1.2,"Kelapa Sawit":1.15},"default_weight":1.0,"cap_quantile":0.95,"missing_score":0}'
    },
    "land_area_by_type": {
        "label": "Luas lahan tertimbang jenis komoditas",
        "formula": "nilai = Σ(luas lahan i x bobot jenis produksi i), lalu dinormalisasi 0-100",
        "notes": "Cocok untuk menilai luas lahan yang dilayani dengan bobot komoditas.",
        "settings_example": '{"commodity_weights":{"Padi":1.5,"Jagung":1.2,"Kelapa Sawit":1.15},"default_weight":1.0,"cap_quantile":0.95,"missing_score":0}'
    },
    "production_type_priority": {
        "label": "Prioritas jenis produksi",
        "formula": "score = bobot jenis produksi tertinggi pada koridor / bobot maksimum x 100",
        "notes": "Menilai jenis komoditasnya saja, tanpa volume. Gunakan bersama produksi/lahan agar tidak hanya berbasis nama komoditas.",
        "settings_example": '{"commodity_weights":{"Padi":1.5,"Jagung":1.2,"Kelapa Sawit":1.15},"default_weight":1.0,"missing_score":0}'
    },
    "production_land_by_type": {
        "label": "Ekonomi komoditas: produksi + lahan tertimbang",
        "formula": "score = normalize(Σproduksi x bobot komoditas) x production_weight + normalize(Σlahan x bobot komoditas) x land_weight",
        "notes": "Ini versi ekonomi yang mengaitkan jenis produksi, jumlah produksi, dan luas lahan dalam satu rumus.",
        "settings_example": '{"commodity_weights":{"Padi":1.5,"Jagung":1.2,"Kelapa Sawit":1.15},"default_weight":1.0,"production_weight":0.6,"land_weight":0.4,"cap_quantile":0.95}'
    },
    "kml_ratio": {
        "label": "Kesesuaian panjang KML terhadap panjang koridor",
        "formula": "score = min(Panjang KML/KMZ / Panjang Koridor, max_ratio) x multiplier",
        "notes": "Cocok untuk kesiapan data spasial. max_ratio dan multiplier bisa diedit.",
        "settings_example": '{"max_ratio":1.0,"multiplier":100,"missing_score":0}'
    },
}


def slugify(text: str) -> str:
    text = str(text).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "parameter"


def _settings(param_or_settings: dict | str | None) -> dict[str, Any]:
    """Read formula-specific settings from a dict or JSON string."""
    if param_or_settings is None:
        return {}
    if isinstance(param_or_settings, str):
        txt = param_or_settings.strip()
        if not txt:
            return {}
        return json.loads(txt)
    if isinstance(param_or_settings, dict):
        raw = param_or_settings.get("settings_json", {})
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            return json.loads(raw)
        return {}
    return {}


def _float_setting(settings: dict, key: str, default: float) -> float:
    try:
        return float(settings.get(key, default))
    except Exception:
        return float(default)


def _int_or_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def get_formula_catalog() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "formula_type": k,
            "nama": v["label"],
            "rumus": v["formula"],
            "contoh_settings_json": v.get("settings_example", "{}"),
            "catatan": v["notes"],
        }
        for k, v in FORMULA_TYPES.items()
    ])


def prepare_numeric(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in NUMERIC_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _safe_numeric_col(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(default, index=df.index, dtype="float64")


def compute_indicators(df: pd.DataFrame, scoring_settings: dict | None = None) -> pd.DataFrame:
    """Create derived indicators used by dynamic formulas.

    Important settings:
    - condition_length_mode='normalize_to_corridor_length': scales Baik/Sedang/RR/RB so total equals Panjang.
    - cost_mode='condition_based': ignores Excel cost and estimates cost from condition lengths.
    - kml_missing_policy='use_corridor_length': uses Panjang Koridor when Panjang KML/KMZ is blank/0.
    """
    settings = normalize_scoring_settings(scoring_settings)
    df = prepare_numeric(df)
    out = df.copy()

    panjang = _safe_numeric_col(out, COL["panjang"])
    baik_raw = _safe_numeric_col(out, COL["baik"]).fillna(0).clip(lower=0)
    sedang_raw = _safe_numeric_col(out, COL["sedang"]).fillna(0).clip(lower=0)
    rr_raw = _safe_numeric_col(out, COL["rusak_ringan"]).fillna(0).clip(lower=0)
    rb_raw = _safe_numeric_col(out, COL["rusak_berat"]).fillna(0).clip(lower=0)
    biaya_excel = _safe_numeric_col(out, COL["biaya"])

    kondisi_sum_raw = baik_raw + sedang_raw + rr_raw + rb_raw
    out["kondisi_total_raw_km"] = kondisi_sum_raw
    out["kondisi_mismatch_km"] = (panjang.fillna(0) - kondisi_sum_raw.fillna(0)).abs()

    # Normalize condition lengths to corridor length when requested.
    if settings.get("condition_length_mode") == "normalize_to_corridor_length":
        faktor = (panjang / kondisi_sum_raw.where(kondisi_sum_raw > 0)).replace([np.inf, -np.inf], np.nan)
        faktor = faktor.where((panjang > 0) & (kondisi_sum_raw > 0), 1.0).fillna(1.0)
    else:
        faktor = pd.Series(1.0, index=out.index)
    out["kondisi_normalization_factor"] = faktor

    baik = (baik_raw * faktor).fillna(0).clip(lower=0)
    sedang = (sedang_raw * faktor).fillna(0).clip(lower=0)
    rr = (rr_raw * faktor).fillna(0).clip(lower=0)
    rb = (rb_raw * faktor).fillna(0).clip(lower=0)

    out["baik_used_km"] = baik
    out["sedang_used_km"] = sedang
    out["rusak_ringan_used_km"] = rr
    out["rusak_berat_used_km"] = rb
    out["kondisi_total_used_km"] = baik + sedang + rr + rb

    safe_panjang = panjang.where(panjang > 0)
    out["persen_baik"] = (baik / safe_panjang * 100).replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 100)
    out["persen_sedang"] = (sedang / safe_panjang * 100).replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 100)
    out["persen_rusak_ringan"] = (rr / safe_panjang * 100).replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 100)
    out["persen_rusak_berat"] = (rb / safe_panjang * 100).replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 100)
    out["persen_rusak_total"] = (out["persen_rusak_ringan"] + out["persen_rusak_berat"]).clip(0, 100)

    # KML/KMZ fallback policy.
    kml_raw = _safe_numeric_col(out, COL["panjang_kml"], default=np.nan)
    if settings.get("kml_missing_policy") == "use_corridor_length":
        kml_used = kml_raw.where(kml_raw > 0, panjang)
    elif settings.get("kml_missing_policy") == "ignore":
        kml_used = kml_raw
    else:
        kml_used = kml_raw
    out["panjang_kml_used_km"] = kml_used
    out["kml_missing_after_policy"] = kml_used.isna() | (kml_used <= 0)

    # Cost policy: Excel cost, estimated condition cost, or estimated only when Excel cost is blank/0.
    unit_cost = settings.get("unit_cost_miliar_per_km", {}) or {}
    c_baik = _int_or_float(unit_cost.get("baik", 0.0))
    c_sedang = _int_or_float(unit_cost.get("sedang", 0.5))
    c_rr = _int_or_float(unit_cost.get("rusak_ringan", 1.5))
    c_rb = _int_or_float(unit_cost.get("rusak_berat", 3.0))
    biaya_estimasi_awal = baik * c_baik + sedang * c_sedang + rr * c_rr + rb * c_rb

    # Some corridors can still get 0 in condition-based costing. Typical causes:
    # 1) all length is Baik and biaya Baik is set to 0;
    # 2) all unit costs for the present condition classes are 0;
    # 3) corridor length is 0/blank.
    zero_policy = str(settings.get("condition_cost_zero_policy", "allow_zero"))
    zero_candidate = (panjang.fillna(0) > 0) & (biaya_estimasi_awal.fillna(0) <= 0)
    fallback_condition = str(settings.get("condition_cost_zero_fallback_condition", "sedang"))
    fallback_unit_cost = {
        "baik": c_baik,
        "sedang": c_sedang,
        "rusak_ringan": c_rr,
        "rusak_berat": c_rb,
    }.get(fallback_condition, c_sedang)
    minimum_cost = _int_or_float(settings.get("condition_cost_zero_minimum_miliar", 0.0))

    biaya_estimasi = biaya_estimasi_awal.copy()
    biaya_estimasi_zero_action = pd.Series("tidak_ada", index=out.index)
    if zero_policy == "use_fallback_condition":
        fallback_cost = panjang.fillna(0) * fallback_unit_cost
        biaya_estimasi = biaya_estimasi.where(~zero_candidate, fallback_cost)
        biaya_estimasi_zero_action = pd.Series(np.where(zero_candidate, f"fallback_{fallback_condition}", "tidak_ada"), index=out.index)
    elif zero_policy == "minimum_cost":
        biaya_estimasi = biaya_estimasi.where(~zero_candidate, minimum_cost)
        biaya_estimasi_zero_action = pd.Series(np.where(zero_candidate, "minimum_cost", "tidak_ada"), index=out.index)

    out["biaya_estimasi_kondisi_awal_miliar"] = biaya_estimasi_awal
    out["biaya_estimasi_kondisi_miliar"] = biaya_estimasi
    out["biaya_estimasi_zero_action"] = biaya_estimasi_zero_action

    cost_mode = str(settings.get("cost_mode", "excel_total"))
    if cost_mode == "condition_based":
        biaya_aktif = biaya_estimasi
        biaya_sumber = pd.Series("kondisi_jalan", index=out.index)
        biaya_sumber = biaya_sumber.where(biaya_estimasi_zero_action.eq("tidak_ada"), "kondisi_jalan_" + biaya_estimasi_zero_action.astype(str))
    elif cost_mode == "condition_if_excel_missing":
        has_excel_cost = biaya_excel.notna() & (biaya_excel > 0)
        biaya_aktif = biaya_excel.where(has_excel_cost, biaya_estimasi)
        biaya_sumber = pd.Series(np.where(has_excel_cost, "excel", "kondisi_jalan"), index=out.index)
        biaya_sumber = biaya_sumber.where(has_excel_cost | biaya_estimasi_zero_action.eq("tidak_ada"), "kondisi_jalan_" + biaya_estimasi_zero_action.astype(str))
    else:
        biaya_aktif = biaya_excel
        biaya_sumber = pd.Series("excel", index=out.index)

    def _zero_reason(row: pd.Series) -> str:
        if pd.isna(row.get("biaya_aktif_miliar")):
            return "biaya_aktif_nan"
        if float(row.get("biaya_aktif_miliar") or 0) > 0:
            return ""
        if float(row.get(COL["panjang"], 0) or 0) <= 0:
            return "Panjang Koridor 0/kosong"
        if str(row.get("biaya_sumber", "")).startswith("excel"):
            return "Mode biaya masih memakai Excel dan nilai Biaya Excel 0/kosong"
        if zero_policy == "allow_zero" and float(row.get("baik_used_km", 0) or 0) > 0 and float(row.get("sedang_used_km", 0) or 0) <= 0 and float(row.get("rusak_ringan_used_km", 0) or 0) <= 0 and float(row.get("rusak_berat_used_km", 0) or 0) <= 0 and c_baik == 0:
            return "Semua kondisi Baik dan biaya Baik = 0"
        if zero_policy == "use_fallback_condition" and fallback_unit_cost <= 0:
            return f"Fallback {fallback_condition} dipilih tetapi biaya per km-nya 0"
        if zero_policy == "minimum_cost" and minimum_cost <= 0:
            return "Minimum cost dipilih tetapi nilainya 0"
        return "Unit biaya kondisi yang berlaku bernilai 0 atau kondisi tidak memiliki panjang efektif"

    out["biaya_aktif_miliar"] = biaya_aktif
    out["biaya_sumber"] = biaya_sumber
    out["biaya_per_km_miliar"] = (biaya_aktif / safe_panjang).replace([np.inf, -np.inf], np.nan)
    out["biaya_nol_reason"] = out.apply(_zero_reason, axis=1)

    prod_cols = [c for c in PRODUCTION_AMOUNT_COLS if c in out.columns]
    lahan_cols = [c for c in LAND_AREA_COLS if c in out.columns]
    out["produksi_total_ton_tahun"] = out[prod_cols].clip(lower=0).fillna(0).sum(axis=1) if prod_cols else 0
    out["luas_lahan_total_ha"] = out[lahan_cols].clip(lower=0).fillna(0).sum(axis=1) if lahan_cols else 0
    jenis_cols = [c for c in PRODUCTION_TYPE_COLS if c in out.columns]
    if jenis_cols:
        out["jenis_produksi_detail"] = out[jenis_cols].fillna("").astype(str).apply(lambda r: "; ".join([x.strip() for x in r.tolist() if x.strip() and x.strip().lower() not in {"nan", "none", "-"}]), axis=1)
    else:
        out["jenis_produksi_detail"] = ""

    facility_cols = [COL["pendidikan"], COL["kesehatan"], COL["pemerintahan"], COL["sppg"]]
    for c in facility_cols:
        if c not in out.columns:
            out[c] = 0
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["facility_weighted"] = (
        out[COL["pendidikan"]].fillna(0) * 1.0 +
        out[COL["kesehatan"]].fillna(0) * 2.0 +
        out[COL["pemerintahan"]].fillna(0) * 1.0 +
        out[COL["sppg"]].fillna(0) * 3.0
    )

    # Better display label when Nama Koridor is blank and No. Koridor exists.
    if COL["nama_koridor"] in out.columns and COL["no_koridor"] in out.columns:
        nama = out[COL["nama_koridor"]].fillna("").astype(str).str.strip()
        no = out[COL["no_koridor"]].fillna("").astype(str).str.strip()
        out["nama_koridor_display"] = np.where(nama.ne(""), nama, "Koridor " + no)
    return out

def _blank_series(df: pd.DataFrame) -> pd.Series:
    return pd.Series(np.nan, index=df.index)


def _first_existing_series(df: pd.DataFrame, source_columns: list[str]) -> pd.Series:
    for col in source_columns:
        if col in df.columns:
            return df[col]
    return _blank_series(df)


def _source_columns(param: dict) -> list[str]:
    cols = param.get("source_columns", [])
    if isinstance(cols, str):
        return [c.strip() for c in cols.split(",") if c.strip()]
    return [str(c).strip() for c in cols if str(c).strip()]


def _custom_yes_to_score(series: pd.Series, settings: dict) -> pd.Series:
    true_values = settings.get("true_values", ["YA", "YES", "Y", "TRUE", "1", "TERHUBUNG", "ADA"])
    true_values = {str(x).strip().upper() for x in true_values}
    true_score = _float_setting(settings, "true_score", 100.0)
    false_score = _float_setting(settings, "false_score", 0.0)
    s = series.fillna("").astype(str).str.strip().str.upper()
    return pd.Series(np.where(s.isin(true_values), true_score, false_score), index=series.index).clip(0, 100)


def _series_exists_score(series: pd.Series, complete_score: float = 100.0, missing_score: float = 0.0) -> pd.Series:
    def ok(v: Any) -> bool:
        if pd.isna(v):
            return False
        if isinstance(v, str) and v.strip() in EMPTY_MARKERS:
            return False
        return True
    return series.apply(lambda x: complete_score if ok(x) else missing_score).astype(float).clip(0, 100)


def _weights_dict(settings: dict, source_columns: list[str], default_weight: float = 1.0) -> dict[str, float]:
    weights = settings.get("weights", {})
    if isinstance(weights, str):
        try:
            weights = json.loads(weights)
        except Exception:
            weights = {}
    if isinstance(weights, dict) and weights:
        return {str(k): _int_or_float(v) for k, v in weights.items()}
    return {col: float(default_weight) for col in source_columns}


def _weighted_sum_series(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    total = pd.Series(0.0, index=df.index)
    for col, w in weights.items():
        if col in df.columns:
            total += pd.to_numeric(df[col], errors="coerce").fillna(0) * float(w)
    return total


def _normalize_commodity_name(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _commodity_weights(settings: dict) -> dict[str, float]:
    raw = settings.get("commodity_weights", DEFAULT_COMMODITY_WEIGHTS)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    merged = dict(DEFAULT_COMMODITY_WEIGHTS)
    merged.update({_normalize_commodity_name(k): _int_or_float(v) for k, v in raw.items()})
    return merged


def _production_weighted_values(df: pd.DataFrame, settings: dict) -> dict[str, pd.Series]:
    weights = _commodity_weights(settings)
    default_weight = _float_setting(settings, "default_weight", 1.0)
    weighted_prod = pd.Series(0.0, index=df.index)
    weighted_land = pd.Series(0.0, index=df.index)
    max_weight = pd.Series(0.0, index=df.index)
    count_known = pd.Series(0.0, index=df.index)

    display_parts = pd.Series("", index=df.index, dtype="object")

    for type_col, prod_col, land_col in PRODUCTION_SLOTS:
        if type_col in df.columns:
            jenis = df[type_col].fillna("").astype(str).str.strip()
        else:
            jenis = pd.Series("", index=df.index)
        jenis_norm = jenis.map(_normalize_commodity_name)
        w = jenis_norm.map(lambda x: weights.get(x, default_weight) if x else 0.0).astype(float)
        prod = pd.to_numeric(df[prod_col], errors="coerce").fillna(0).clip(lower=0) if prod_col in df.columns else pd.Series(0.0, index=df.index)
        land = pd.to_numeric(df[land_col], errors="coerce").fillna(0).clip(lower=0) if land_col in df.columns else pd.Series(0.0, index=df.index)

        weighted_prod += prod * w
        weighted_land += land * w
        max_weight = pd.concat([max_weight, w], axis=1).max(axis=1)
        count_known += np.where(jenis_norm.ne(""), 1.0, 0.0)

        # Human-readable audit string; keep it compact.
        part = jenis.where(jenis_norm.eq(""), jenis + " x" + w.map(lambda v: f"{v:g}"))
        display_parts = np.where(
            (jenis_norm.ne("")) & (display_parts.astype(str).ne("")),
            display_parts.astype(str) + "; " + part.astype(str),
            np.where(jenis_norm.ne(""), part.astype(str), display_parts.astype(str)),
        )
        display_parts = pd.Series(display_parts, index=df.index, dtype="object")

    return {
        "produksi_tertimbang_ton_tahun": weighted_prod,
        "luas_lahan_tertimbang_ha": weighted_land,
        "jenis_produksi_bobot_maks": max_weight,
        "jumlah_jenis_produksi_terisi": count_known,
        "jenis_produksi_bobot_detail": display_parts,
    }


def add_production_weighted_indicators(df: pd.DataFrame, settings: dict | None = None) -> pd.DataFrame:
    out = df.copy()
    vals = _production_weighted_values(out, settings or {})
    for k, v in vals.items():
        out[k] = v
    return out


def compute_parameter_score(df: pd.DataFrame, param: dict) -> pd.Series:
    formula_type = str(param.get("formula_type", "")).strip()
    cols = _source_columns(param)
    settings = _settings(param)
    cap = settings.get("cap_quantile", param.get("cap_quantile", 0.95))
    try:
        cap = float(cap)
    except Exception:
        cap = 0.95

    if formula_type == "exists":
        return _series_exists_score(
            _first_existing_series(df, cols),
            complete_score=_float_setting(settings, "complete_score", 100.0),
            missing_score=_float_setting(settings, "missing_score", 0.0),
        )

    if formula_type == "yes_no":
        return _custom_yes_to_score(_first_existing_series(df, cols), settings)

    if formula_type == "numeric_higher":
        out = normalize_0_100(_first_existing_series(df, cols), higher_is_better=True, cap_quantile=cap)
        missing_score = _float_setting(settings, "missing_score", 0.0)
        x = pd.to_numeric(_first_existing_series(df, cols), errors="coerce")
        out.loc[x.isna()] = missing_score
        return out.clip(0, 100)

    if formula_type == "numeric_lower":
        out = normalize_0_100(_first_existing_series(df, cols), higher_is_better=False, cap_quantile=cap)
        missing_score = _float_setting(settings, "missing_score", 0.0)
        x = pd.to_numeric(_first_existing_series(df, cols), errors="coerce")
        out.loc[x.isna()] = missing_score
        return out.clip(0, 100)

    if formula_type == "numeric_lower_positive":
        x = pd.to_numeric(_first_existing_series(df, cols), errors="coerce")
        positive = x.where(x > 0)
        out = normalize_0_100(positive, higher_is_better=False, cap_quantile=cap)
        out.loc[positive.isna()] = _float_setting(settings, "zero_or_missing_score", 0.0)
        return out.clip(0, 100)

    if formula_type == "rank_lower":
        out = inverse_priority_score(_first_existing_series(df, cols))
        x = pd.to_numeric(_first_existing_series(df, cols), errors="coerce")
        out.loc[x.isna()] = _float_setting(settings, "missing_score", 0.0)
        return out.clip(0, 100)

    if formula_type == "completeness":
        return _series_exists_score(
            _first_existing_series(df, cols),
            complete_score=_float_setting(settings, "complete_score", 100.0),
            missing_score=_float_setting(settings, "missing_score", 0.0),
        )

    if formula_type == "weighted_percent_sum":
        weights = _weights_dict(settings, cols, default_weight=1.0)
        out = _weighted_sum_series(df, weights)
        return out.clip(_float_setting(settings, "clip_min", 0.0), _float_setting(settings, "clip_max", 100.0))

    if formula_type == "condition_urgency":
        # Backward-compatible and editable. New usage can use weighted_percent_sum directly.
        rb_w = _float_setting(settings, "rb_weight", 1.00)
        rr_w = _float_setting(settings, "rr_weight", 0.60)
        sedang_w = _float_setting(settings, "sedang_weight", 0.25)
        rb = pd.to_numeric(df.get("persen_rusak_berat", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
        rr = pd.to_numeric(df.get("persen_rusak_ringan", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
        sedang = pd.to_numeric(df.get("persen_sedang", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
        out = rb * rb_w + rr * rr_w + sedang * sedang_w
        return out.clip(_float_setting(settings, "clip_min", 0.0), _float_setting(settings, "clip_max", 100.0))

    if formula_type == "weighted_sum_higher":
        weights = _weights_dict(settings, cols, default_weight=1.0)
        raw = _weighted_sum_series(df, weights)
        return normalize_0_100(raw, higher_is_better=True, cap_quantile=cap).clip(0, 100)

    if formula_type == "weighted_sum_lower":
        weights = _weights_dict(settings, cols, default_weight=1.0)
        raw = _weighted_sum_series(df, weights)
        return normalize_0_100(raw, higher_is_better=False, cap_quantile=cap).clip(0, 100)

    if formula_type == "economic_combined":
        prod = pd.to_numeric(df.get("produksi_total_ton_tahun", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
        lahan = pd.to_numeric(df.get("luas_lahan_total_ha", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
        prod_score = normalize_0_100(prod, higher_is_better=True, cap_quantile=cap)
        lahan_score = normalize_0_100(lahan, higher_is_better=True, cap_quantile=cap)
        prod_w = _float_setting(settings, "production_weight", 0.60)
        land_w = _float_setting(settings, "land_weight", 0.40)
        total_w = prod_w + land_w
        if total_w <= 0:
            return pd.Series(0.0, index=df.index)
        return (prod_score * (prod_w / total_w) + lahan_score * (land_w / total_w)).clip(0, 100)

    if formula_type in {"production_amount_by_type", "land_area_by_type", "production_type_priority", "production_land_by_type"}:
        vals = _production_weighted_values(df, settings)
        prod = vals["produksi_tertimbang_ton_tahun"]
        land = vals["luas_lahan_tertimbang_ha"]
        max_w = vals["jenis_produksi_bobot_maks"]
        missing_score = _float_setting(settings, "missing_score", 0.0)

        if formula_type == "production_amount_by_type":
            out = normalize_0_100(prod, higher_is_better=True, cap_quantile=cap)
            out.loc[prod <= 0] = missing_score
            return out.clip(0, 100)

        if formula_type == "land_area_by_type":
            out = normalize_0_100(land, higher_is_better=True, cap_quantile=cap)
            out.loc[land <= 0] = missing_score
            return out.clip(0, 100)

        if formula_type == "production_type_priority":
            weights = _commodity_weights(settings)
            max_possible = max([v for v in weights.values() if v is not None] + [1.0])
            out = (max_w / max_possible * 100).replace([np.inf, -np.inf], np.nan).fillna(missing_score)
            out.loc[max_w <= 0] = missing_score
            return out.clip(0, 100)

        prod_score = normalize_0_100(prod, higher_is_better=True, cap_quantile=cap)
        land_score = normalize_0_100(land, higher_is_better=True, cap_quantile=cap)
        prod_score.loc[prod <= 0] = missing_score
        land_score.loc[land <= 0] = missing_score
        prod_w = _float_setting(settings, "production_weight", 0.60)
        land_w = _float_setting(settings, "land_weight", 0.40)
        total_w = prod_w + land_w
        if total_w <= 0:
            return pd.Series(0.0, index=df.index)
        return (prod_score * (prod_w / total_w) + land_score * (land_w / total_w)).clip(0, 100)

    if formula_type == "kml_ratio":
        # Uses `panjang_kml_used_km` when available. That column applies the global KML fallback policy.
        kml_col = "panjang_kml_used_km" if "panjang_kml_used_km" in df.columns else COL["panjang_kml"]
        if kml_col in df.columns and COL["panjang"] in df.columns:
            kml = pd.to_numeric(df[kml_col], errors="coerce")
            panjang = pd.to_numeric(df[COL["panjang"]], errors="coerce")
            ratio = (kml / panjang.where(panjang > 0)).replace([np.inf, -np.inf], np.nan)
            missing_score = _float_setting(settings, "missing_score", 0.0)
            out = ratio.clip(0, _float_setting(settings, "max_ratio", 1.0)).fillna(missing_score / max(_float_setting(settings, "multiplier", 100.0), 1.0))
            return (out * _float_setting(settings, "multiplier", 100.0)).clip(0, 100)
        return pd.Series(_float_setting(settings, "missing_score", 0.0), index=df.index).clip(0, 100)

    return pd.Series(0.0, index=df.index)


DEFAULT_DATA_QUALITY_RULES = [
    {"id": "nama_koridor_kosong", "active": True, "name": "Nama Koridor kosong", "rule_type": "blank", "source_columns": [COL["nama_koridor"]], "penalty": 10, "settings_json": {}},
    {"id": "panjang_kosong_atau_nol", "active": True, "name": "Panjang kosong/0", "rule_type": "nonpositive", "source_columns": [COL["panjang"]], "penalty": 25, "settings_json": {}},
    {"id": "biaya_kosong_atau_nol", "active": True, "name": "Biaya kosong/0", "rule_type": "nonpositive", "source_columns": [COL["biaya"]], "penalty": 15, "settings_json": {}},
    {"id": "kondisi_tidak_sama_panjang", "active": True, "name": "Panjang kondisi tidak sama dengan panjang koridor", "rule_type": "condition_length_mismatch", "source_columns": [COL["baik"], COL["sedang"], COL["rusak_ringan"], COL["rusak_berat"], COL["panjang"]], "penalty": 15, "settings_json": {"tolerance_km": 0.05}},
    {"id": "tematik_kosong", "active": True, "name": "Tematik kosong", "rule_type": "blank", "source_columns": [COL["tematik"]], "penalty": 5, "settings_json": {}},
    {"id": "produksi_kosong", "active": True, "name": "Produksi total 0", "rule_type": "nonpositive", "source_columns": ["produksi_total_ton_tahun"], "penalty": 5, "settings_json": {}},
    {"id": "fasilitas_kosong", "active": True, "name": "Fasilitas publik 0", "rule_type": "nonpositive", "source_columns": ["facility_weighted"], "penalty": 5, "settings_json": {}},
    {"id": "kml_kosong", "active": True, "name": "Panjang KML/KMZ kosong/0", "rule_type": "nonpositive", "source_columns": [COL["panjang_kml"]], "penalty": 5, "settings_json": {}},
]


def _rule_is_skipped_by_settings(rule: dict, scoring_settings: dict) -> bool:
    rid = str(rule.get("id", "")).strip()
    name = str(rule.get("name", "")).lower()
    cols = set(_source_columns(rule))

    if not scoring_settings.get("use_data_quality_penalty", True):
        return True

    if rid == "kml_kosong" or COL["panjang_kml"] in cols or "kml" in rid.lower():
        if scoring_settings.get("kml_missing_policy") in {"use_corridor_length", "ignore"}:
            return True

    if rid == "nama_koridor_kosong" or COL["nama_koridor"] in cols:
        if scoring_settings.get("name_policy") == "name_or_no_koridor":
            return True

    if rid == "kondisi_tidak_sama_panjang" or "kondisi" in rid.lower() or "kondisi" in name:
        if scoring_settings.get("condition_length_mode") == "normalize_to_corridor_length":
            return True

    if rid == "tematik_kosong" or COL["tematik"] in cols:
        if scoring_settings.get("tematik_missing_policy") == "score_only":
            return True

    if rid == "biaya_kosong_atau_nol" or COL["biaya"] in cols:
        if scoring_settings.get("cost_mode") in {"condition_based", "condition_if_excel_missing"}:
            return True

    return False


def compute_data_quality_penalty(
    out: pd.DataFrame,
    rules: list[dict] | None = None,
    scoring_settings: dict | None = None,
) -> pd.Series:
    rules = DEFAULT_DATA_QUALITY_RULES if rules is None else rules
    scoring_settings = normalize_scoring_settings(scoring_settings)
    penalty = pd.Series(0.0, index=out.index)

    for rule in rules:
        if not bool(rule.get("active", True)):
            continue
        if _rule_is_skipped_by_settings(rule, scoring_settings):
            continue

        rule_type = str(rule.get("rule_type", "")).strip()
        cols = _source_columns(rule)
        p = _float_setting(rule, "penalty", 0.0)
        settings = _settings(rule)

        if p <= 0:
            continue

        if rule_type == "blank":
            s = _first_existing_series(out, cols)
            missing = _series_exists_score(s, 1, 0).eq(0)
            penalty += np.where(missing, p, 0)

        elif rule_type == "nonpositive":
            # If the cost policy creates an active cost, use it for biaya rules.
            if (COL["biaya"] in cols or str(rule.get("id", "")).strip() == "biaya_kosong_atau_nol") and "biaya_aktif_miliar" in out.columns:
                s = pd.to_numeric(out["biaya_aktif_miliar"], errors="coerce")
            elif (COL["panjang_kml"] in cols or str(rule.get("id", "")).strip() == "kml_kosong") and "panjang_kml_used_km" in out.columns:
                s = pd.to_numeric(out["panjang_kml_used_km"], errors="coerce")
            else:
                s = pd.to_numeric(_first_existing_series(out, cols), errors="coerce")
            penalty += np.where(s.isna() | (s <= 0), p, 0)

        elif rule_type == "condition_length_mismatch":
            needed = [COL["baik"], COL["sedang"], COL["rusak_ringan"], COL["rusak_berat"], COL["panjang"]]
            if all(c in out.columns for c in needed):
                kondisi_sum = out[COL["baik"]].fillna(0) + out[COL["sedang"]].fillna(0) + out[COL["rusak_ringan"]].fillna(0) + out[COL["rusak_berat"]].fillna(0)
                mismatch = (out[COL["panjang"]].fillna(0) - kondisi_sum).abs()
                tolerance = _float_setting(settings, "tolerance_km", 0.05)
                penalty += np.where((out[COL["panjang"]].fillna(0) > 0) & (mismatch > tolerance), p, 0)

    return penalty.clip(0, 100)

def compute_scores_dynamic(
    df: pd.DataFrame,
    formula_params: list[dict],
    penalty_factor: float | None = None,
    data_quality_rules: list[dict] | None = None,
    scoring_settings: dict | None = None,
) -> pd.DataFrame:
    scoring_settings = normalize_scoring_settings(scoring_settings)
    # Backward compatibility: explicit penalty_factor argument still overrides settings.
    if penalty_factor is not None:
        scoring_settings["penalty_factor"] = float(penalty_factor)
    out = compute_indicators(df, scoring_settings=scoring_settings)
    active_params = [p for p in formula_params if bool(p.get("active", True)) and float(p.get("weight", 0) or 0) > 0]
    # Add audit columns for commodity-weighted production/lahan using the first active production formula settings.
    prod_param = next((p for p in active_params if str(p.get("formula_type", "")) in {"production_amount_by_type", "land_area_by_type", "production_type_priority", "production_land_by_type"}), None)
    if prod_param is not None:
        out = add_production_weighted_indicators(out, _settings(prod_param))
    total_weight = sum(float(p.get("weight", 0) or 0) for p in active_params)
    if total_weight <= 0:
        raise ValueError("Minimal harus ada 1 rumus aktif dengan bobot lebih besar dari 0.")

    raw = pd.Series(0.0, index=out.index)
    formula_records = []

    for p in active_params:
        pid = slugify(p.get("id") or p.get("name") or "parameter")
        score_col = f"score__{pid}"
        weighted_col = f"weighted__{pid}"
        weight = float(p.get("weight", 0) or 0)
        normalized_weight = weight / total_weight
        score = compute_parameter_score(out, p).fillna(0).clip(0, 100)
        out[score_col] = score
        out[weighted_col] = score * normalized_weight
        raw += out[weighted_col]
        formula_records.append({
            "id": pid,
            "group": p.get("group", ""),
            "name": p.get("name", pid),
            "formula_type": p.get("formula_type", ""),
            "weight_input": weight,
            "weight_normalized": normalized_weight,
            "score_col": score_col,
            "weighted_col": weighted_col,
        })

    out["raw_score"] = raw.clip(0, 100)
    out["data_quality_penalty"] = compute_data_quality_penalty(out, data_quality_rules, scoring_settings=scoring_settings)
    if not scoring_settings.get("use_data_quality_penalty", True):
        out["data_quality_penalty"] = 0.0
    out["data_quality_score"] = (100 - out["data_quality_penalty"]).clip(0, 100)
    out["penalty_factor"] = float(scoring_settings.get("penalty_factor", 0.30))
    out["use_data_quality_penalty"] = bool(scoring_settings.get("use_data_quality_penalty", True))
    out["kml_missing_policy"] = scoring_settings.get("kml_missing_policy", "penalize")
    out["condition_length_mode"] = scoring_settings.get("condition_length_mode", "raw")
    out["cost_mode"] = scoring_settings.get("cost_mode", "excel_total")
    out["condition_cost_zero_policy"] = scoring_settings.get("condition_cost_zero_policy", "allow_zero")
    out["condition_cost_zero_fallback_condition"] = scoring_settings.get("condition_cost_zero_fallback_condition", "sedang")
    out["condition_cost_zero_minimum_miliar"] = scoring_settings.get("condition_cost_zero_minimum_miliar", 0.0)
    out["name_policy"] = scoring_settings.get("name_policy", "require_name")
    out["tematik_missing_policy"] = scoring_settings.get("tematik_missing_policy", "score_and_penalty")
    out["final_score"] = (out["raw_score"] - out["data_quality_penalty"] * float(scoring_settings.get("penalty_factor", 0.30))).clip(0, 100)

    out["kategori_prioritas"] = pd.cut(
        out["final_score"],
        bins=[-0.01, 50, 65, 80, 100],
        labels=["Rendah", "Sedang", "Tinggi", "Sangat Tinggi"],
    ).astype(str)
    out["rank_nasional"] = out["final_score"].rank(method="dense", ascending=False).astype(int)
    if COL["provinsi"] in out.columns:
        out["rank_provinsi"] = out.groupby(COL["provinsi"])["final_score"].rank(method="dense", ascending=False).astype(int)
    else:
        out["rank_provinsi"] = out["rank_nasional"]
    if COL["provinsi"] in out.columns and COL["kabupaten"] in out.columns:
        out["rank_kabupaten"] = out.groupby([COL["provinsi"], COL["kabupaten"]])["final_score"].rank(method="dense", ascending=False).astype(int)
    else:
        out["rank_kabupaten"] = out["rank_nasional"]

    out.attrs["formula_records"] = formula_records
    return out.sort_values("rank_nasional")


# Backward-compatible wrapper.
def compute_scores(df: pd.DataFrame, weights_or_params, penalty_factor: float = 0.30) -> pd.DataFrame:
    if isinstance(weights_or_params, list):
        return compute_scores_dynamic(df, weights_or_params, penalty_factor=penalty_factor)
    raise ValueError("Mode bobot lama tidak dipakai lagi. Gunakan formula_parameters.json.")


def get_score_component_columns(df: pd.DataFrame) -> list[str]:
    fixed = ["raw_score", "data_quality_penalty", "data_quality_score", "final_score"]
    dynamic = [c for c in df.columns if c.startswith("score__") or c.startswith("weighted__")]
    old = [c for c in ["eligibility_score", "urgency_score", "connectivity_score", "facility_score", "economic_score", "cost_efficiency_score", "readiness_score"] if c in df.columns]
    return old + dynamic + [c for c in fixed if c in df.columns]


def _display_settings_json(param: dict) -> str:
    settings = _settings(param)
    return json.dumps(settings, ensure_ascii=False, sort_keys=True)


def describe_formula(param: dict) -> str:
    ft = str(param.get("formula_type", ""))
    settings = _settings(param)
    cols = _source_columns(param)

    if ft == "condition_urgency":
        return (
            f"score = RB% x {_float_setting(settings, 'rb_weight', 1.0):g} + "
            f"RR% x {_float_setting(settings, 'rr_weight', 0.6):g} + "
            f"Sedang% x {_float_setting(settings, 'sedang_weight', 0.25):g}"
        )
    if ft == "weighted_percent_sum":
        weights = _weights_dict(settings, cols)
        return "score = " + " + ".join([f"{k} x {v:g}" for k, v in weights.items()])
    if ft in ["weighted_sum_higher", "weighted_sum_lower"]:
        weights = _weights_dict(settings, cols)
        direction = "dinormalisasi semakin besar lebih baik" if ft.endswith("higher") else "dinormalisasi semakin kecil lebih baik"
        return "nilai = " + " + ".join([f"{k} x {v:g}" for k, v in weights.items()]) + f"; {direction}"
    if ft == "economic_combined":
        pw = _float_setting(settings, "production_weight", 0.6)
        lw = _float_setting(settings, "land_weight", 0.4)
        total = pw + lw if (pw + lw) > 0 else 1
        return f"score = produksi_score x {pw/total:.2f} + lahan_score x {lw/total:.2f}"
    if ft == "production_amount_by_type":
        return "score = normalize(Σ jumlah produksi x bobot jenis produksi)"
    if ft == "land_area_by_type":
        return "score = normalize(Σ luas lahan x bobot jenis produksi)"
    if ft == "production_type_priority":
        return "score = bobot jenis produksi tertinggi / bobot maksimum x 100"
    if ft == "production_land_by_type":
        pw = _float_setting(settings, "production_weight", 0.6)
        lw = _float_setting(settings, "land_weight", 0.4)
        total = pw + lw if (pw + lw) > 0 else 1
        return f"score = produksi_tertimbang_score x {pw/total:.2f} + lahan_tertimbang_score x {lw/total:.2f}"
    if ft == "yes_no":
        true_values = settings.get("true_values", ["YA", "YES", "Y", "TRUE", "1", "TERHUBUNG", "ADA"])
        return f"score = {_float_setting(settings,'true_score',100):g} jika nilai ∈ {true_values}; selain itu {_float_setting(settings,'false_score',0):g}"
    if ft == "exists":
        return f"score = {_float_setting(settings,'complete_score',100):g} jika terisi; kosong = {_float_setting(settings,'missing_score',0):g}"
    if ft == "kml_ratio":
        return f"score = min(KML/Panjang, {_float_setting(settings,'max_ratio',1):g}) x {_float_setting(settings,'multiplier',100):g}"
    return FORMULA_TYPES.get(ft, {}).get("formula", "Tipe rumus tidak dikenal")


def build_formula_summary(params: list[dict]) -> pd.DataFrame:
    records = []
    active = [p for p in params if bool(p.get("active", True)) and float(p.get("weight", 0) or 0) > 0]
    total = sum(float(p.get("weight", 0) or 0) for p in active)
    for p in params:
        ft = str(p.get("formula_type", ""))
        catalog = FORMULA_TYPES.get(ft, {})
        weight = float(p.get("weight", 0) or 0)
        records.append({
            "aktif": bool(p.get("active", True)),
            "id": p.get("id", ""),
            "grup": p.get("group", ""),
            "nama_parameter": p.get("name", ""),
            "tipe_rumus": ft,
            "rumus_aktif": describe_formula(p),
            "kolom_sumber": ", ".join(_source_columns(p)),
            "settings_json": _display_settings_json(p),
            "bobot_input": weight,
            "bobot_normalisasi_%": (weight / total * 100) if total > 0 and bool(p.get("active", True)) else 0,
            "cap_quantile": p.get("cap_quantile", _settings(p).get("cap_quantile", 0.95)),
            "catatan": p.get("description", catalog.get("notes", "")),
        })
    return pd.DataFrame(records)


def export_columns(df: pd.DataFrame, include_audit: bool = False) -> pd.DataFrame:
    """Return columns for table/export.

    Default is a user-facing view: only the effective values used in scoring are shown.
    Audit columns such as original Excel cost, condition-cost estimate, source labels, and
    internal policies can be included by passing include_audit=True.
    """
    user_cols = [
        "rank_nasional", "rank_provinsi", "rank_kabupaten", COL["id_koridor"], COL["provinsi"], COL["kabupaten"],
        COL["no_koridor"], COL["nama_koridor"], "nama_koridor_display", COL["panjang"],
        "biaya_aktif_miliar", "biaya_per_km_miliar",
        "persen_rusak_total", "persen_rusak_berat", "persen_rusak_ringan", "persen_sedang",
        "data_quality_penalty", "raw_score", "final_score", "kategori_prioritas",
        COL["status_pengajuan"], COL["tematik"], COL["jenis_produksi"],
        "Jenis Produksi 1", "Jumlah Produksi 1 (Ton/Tahun)", "Luas Lahan 1 (Ha)",
        "Jenis Produksi 2", "Jumlah Produksi 2 (Ton/Tahun)", "Luas Lahan 2 (Ha)",
        "Jenis Produksi 3", "Jumlah Produksi 3 (Ton/Tahun)", "Luas Lahan 3 (Ha)",
        "Jenis Produksi 4", "Jumlah Produksi 4 (Ton/Tahun)", "Luas Lahan 4 (Ha)",
        "produksi_total_ton_tahun", "luas_lahan_total_ha",
        "produksi_tertimbang_ton_tahun", "luas_lahan_tertimbang_ha", "jenis_produksi_bobot_maks", "jenis_produksi_bobot_detail",
        COL["prioritas_kab"], COL["prioritas_prov"], COL["koridor_awal"],
        "panjang_kml_used_km",
    ]
    audit_cols = [
        COL["biaya"], "biaya_estimasi_kondisi_awal_miliar", "biaya_estimasi_kondisi_miliar",
        "biaya_sumber", "biaya_nol_reason", "biaya_estimasi_zero_action",
        "kondisi_mismatch_km", "kondisi_normalization_factor",
        COL["panjang_kml"], "kml_missing_policy", "condition_length_mode", "cost_mode",
        "condition_cost_zero_policy", "condition_cost_zero_fallback_condition",
        "condition_cost_zero_minimum_miliar", "name_policy", "tematik_missing_policy",
    ]
    cols = user_cols + (audit_cols if include_audit else [])
    dynamic_score_cols = [c for c in df.columns if c.startswith("score__")]
    existing = [c for c in cols if c in df.columns]
    return df[existing + dynamic_score_cols]
