
from __future__ import annotations

from typing import Any
import math
import pandas as pd

DASH = "-"

def _is_missing(value: Any) -> bool:
    try:
        return pd.isna(value)
    except Exception:
        return value is None


def _to_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def format_number_id(value: Any, decimals: int = 2, prefix: str = "", suffix: str = "", strip_zero: bool = False) -> str:
    num = _to_float(value)
    if num is None or not math.isfinite(num):
        return DASH
    s = f"{num:,.{decimals}f}"
    s = s.replace(",", "_").replace(".", ",").replace("_", ".")
    if strip_zero and decimals > 0:
        s = s.rstrip("0").rstrip(",")
    return f"{prefix}{s}{suffix}"


def format_int_id(value: Any, suffix: str = "") -> str:
    num = _to_float(value)
    if num is None or not math.isfinite(num):
        return DASH
    s = f"{int(round(num)):,.0f}".replace(",", ".")
    return f"{s}{suffix}"


def column_format_kind(col: str) -> tuple[str, int, str, str]:
    """Return (kind, decimals, prefix, suffix) inferred from column name."""
    c = str(col).lower()
    if c in {"rank_nasional", "rank", "jumlah", "jumlah_koridor"} or c.startswith("rank_"):
        return ("int", 0, "", "")
    if any(x in c for x in ["persen", "percentage", "percent"]):
        return ("number", 2, "", "%")
    if c.startswith("score__") or c.startswith("weighted__") or any(x in c for x in ["final_score", "raw_score", "avg_score", "max_score", "min_score", "penalty", "rata_rata_score"]):
        return ("number", 2, "", "")
    if any(x in c for x in ["biaya", "cost", "miliar", "rp ", "rp_"]):
        return ("number", 2, "", "")
    if any(x in c for x in ["panjang", "km", "baik_used", "sedang_used", "rusak", "mismatch"]):
        return ("number", 2, "", "")
    if any(x in c for x in ["luas", "lahan", "produksi", "ton", "volume", "penduduk", "fasilitas", "sppg", "pendidikan", "kesehatan", "pemerintahan"]):
        return ("number", 2, "", "")
    if any(x in c for x in ["factor", "ratio", "rasio", "quantile"]):
        return ("number", 4, "", "")
    return ("text", 0, "", "")


def format_cell_by_column(value: Any, col: str) -> Any:
    kind, decimals, prefix, suffix = column_format_kind(col)
    if kind == "int":
        return format_int_id(value, suffix=suffix)
    if kind == "number":
        return format_number_id(value, decimals=decimals, prefix=prefix, suffix=suffix)
    if _is_missing(value):
        return DASH
    return value


def format_dataframe_for_display(df: pd.DataFrame, max_rows: int | None = None) -> pd.DataFrame:
    """Return a copy formatted for on-screen display only. Do not use for calculations/export."""
    if df is None:
        return df
    show = df.copy()
    if max_rows is not None:
        show = show.head(max_rows).copy()
    for col in show.columns:
        kind, _, _, _ = column_format_kind(col)
        if kind != "text" or pd.api.types.is_numeric_dtype(show[col]):
            show[col] = show[col].map(lambda v, c=col: format_cell_by_column(v, c))
        else:
            show[col] = show[col].where(show[col].notna(), DASH)
    return show


def format_metric_value(value: Any, kind: str = "number", decimals: int = 2, suffix: str = "", prefix: str = "") -> str:
    if kind == "int":
        return format_int_id(value, suffix=suffix)
    if kind == "percent":
        return format_number_id(value, decimals=decimals, suffix="%")
    return format_number_id(value, decimals=decimals, prefix=prefix, suffix=suffix)


def format_series_for_display(s: pd.Series) -> pd.Series:
    return pd.Series({idx: format_cell_by_column(val, str(idx)) for idx, val in s.items()})
