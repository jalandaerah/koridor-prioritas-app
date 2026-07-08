from __future__ import annotations
import pandas as pd
from .schema import COL, REQUIRED_COLS
from .utils import exists_value
from .scoring_engine import compute_indicators, normalize_scoring_settings


def validate_schema(df: pd.DataFrame) -> list[str]:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    return missing


def build_validation_table(df: pd.DataFrame, scoring_settings: dict | None = None) -> pd.DataFrame:
    settings = normalize_scoring_settings(scoring_settings)
    base = compute_indicators(df, scoring_settings=settings)

    out = pd.DataFrame(index=base.index)
    out["ID Koridor"] = base.get(COL["id_koridor"])
    out["Provinsi"] = base.get(COL["provinsi"])
    out["Kabupaten/Kota"] = base.get(COL["kabupaten"])
    out["No. Koridor"] = base.get(COL["no_koridor"])
    out["Nama Koridor"] = base.get(COL["nama_koridor"])
    out["Nama Display"] = base.get("nama_koridor_display")

    panjang = pd.to_numeric(base.get(COL["panjang"]), errors="coerce")
    biaya_aktif = pd.to_numeric(base.get("biaya_aktif_miliar"), errors="coerce")
    biaya_excel = pd.to_numeric(base.get(COL["biaya"]), errors="coerce")
    kondisi_mismatch = pd.to_numeric(base.get("kondisi_mismatch_km"), errors="coerce").fillna(0)
    kml_used = pd.to_numeric(base.get("panjang_kml_used_km"), errors="coerce")

    error_items = []
    for i in base.index:
        errors = []

        if settings.get("name_policy") == "require_name" and not exists_value(base.at[i, COL["nama_koridor"]]):
            errors.append("Nama koridor kosong")

        if pd.isna(panjang.at[i]) or panjang.at[i] <= 0:
            errors.append("Panjang kosong/0")

        if settings.get("cost_mode") == "excel_total":
            if pd.isna(biaya_excel.at[i]) or biaya_excel.at[i] <= 0:
                errors.append("Biaya Excel kosong/0")
        else:
            if pd.isna(biaya_aktif.at[i]) or biaya_aktif.at[i] <= 0:
                errors.append("Biaya aktif kosong/0 meskipun mode biaya kondisi dipilih")

        if settings.get("condition_length_mode") == "raw":
            if not pd.isna(panjang.at[i]) and panjang.at[i] > 0 and kondisi_mismatch.at[i] > 0.05:
                errors.append("Panjang tidak sama dengan total kondisi")
        elif kondisi_mismatch.at[i] > 0.05:
            errors.append("Panjang kondisi dinormalisasi terhadap panjang koridor")

        if not exists_value(base.at[i, COL["tematik"]]) if COL["tematik"] in base.columns else True:
            if settings.get("tematik_missing_policy") == "score_only":
                errors.append("Tematik kosong - hanya mengurangi skor tematik")
            else:
                errors.append("Tematik kosong - mengurangi skor dan bisa kena penalti")

        if settings.get("kml_missing_policy") == "penalize":
            if pd.isna(kml_used.at[i]) or kml_used.at[i] <= 0:
                errors.append("Panjang KML/KMZ kosong/0")
        elif settings.get("kml_missing_policy") == "use_corridor_length":
            raw_kml = pd.to_numeric(base.get(COL["panjang_kml"]), errors="coerce") if COL["panjang_kml"] in base.columns else pd.Series(index=base.index, dtype="float")
            if (pd.isna(raw_kml.at[i]) or raw_kml.at[i] <= 0) and not (pd.isna(panjang.at[i]) or panjang.at[i] <= 0):
                errors.append("KML/KMZ kosong - memakai panjang koridor sebagai fallback")

        error_items.append("; ".join(errors))

    out["Masalah Data"] = error_items
    out["Jumlah Masalah"] = out["Masalah Data"].apply(lambda x: 0 if x == "" else len(x.split("; ")))
    out["Panjang KM"] = panjang
    out["Biaya Excel Rp M"] = biaya_excel
    out["Biaya Aktif Rp M"] = biaya_aktif
    out["Sumber Biaya"] = base.get("biaya_sumber")
    out["Mismatch Kondisi KM"] = kondisi_mismatch
    out["Panjang KML Used KM"] = kml_used
    return out[out["Jumlah Masalah"] > 0].sort_values(["Jumlah Masalah", "Provinsi", "Kabupaten/Kota"], ascending=[False, True, True])
