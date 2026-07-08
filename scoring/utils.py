from __future__ import annotations
import pandas as pd
import numpy as np

EMPTY_MARKERS = {"", "-", "--", "---", "nan", "none", "null", "NaN", "None"}

def exists_value(value) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, str) and value.strip() in EMPTY_MARKERS:
        return False
    return True

def yes_to_int(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.strip().str.upper()
    return s.isin(["YA", "YES", "Y", "TRUE", "1", "TERHUBUNG", "ADA"]).astype(int)

def flag_exists(series: pd.Series) -> pd.Series:
    return series.apply(lambda x: 1 if exists_value(x) else 0).astype(int)

def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")

def normalize_0_100(series: pd.Series, higher_is_better: bool = True, cap_quantile: float | None = 0.95) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    valid = x.dropna()
    if valid.empty:
        return pd.Series(0.0, index=series.index)
    if cap_quantile is not None and 0 < cap_quantile < 1 and len(valid) >= 10:
        upper = valid.quantile(cap_quantile)
        lower = valid.quantile(1 - cap_quantile) if not higher_is_better else valid.min()
        x = x.clip(lower=lower, upper=upper)
    min_v = x.min(skipna=True)
    max_v = x.max(skipna=True)
    if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
        out = pd.Series(50.0, index=series.index)
        out[x.isna()] = 0.0
        return out
    if higher_is_better:
        out = 100 * (x - min_v) / (max_v - min_v)
    else:
        out = 100 * (max_v - x) / (max_v - min_v)
    return out.fillna(0).clip(0, 100)

def inverse_priority_score(series: pd.Series) -> pd.Series:
    """Priority number: 1 is best; missing gets 0."""
    x = pd.to_numeric(series, errors="coerce")
    valid = x.dropna()
    if valid.empty:
        return pd.Series(0.0, index=series.index)
    min_v, max_v = valid.min(), valid.max()
    if max_v == min_v:
        out = pd.Series(100.0, index=series.index)
        out[x.isna()] = 0.0
        return out
    out = 100 * (max_v - x) / (max_v - min_v)
    return out.fillna(0).clip(0, 100)
