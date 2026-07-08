from __future__ import annotations
from pathlib import Path
import json
import shutil
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CONFIG_DIR = BASE_DIR / "config"
RAW_PARQUET = PROCESSED_DIR / "koridor_raw.parquet"
SCORED_PARQUET = PROCESSED_DIR / "koridor_score.parquet"
FORMULA_PARAMS_JSON = CONFIG_DIR / "formula_parameters.json"
SCORING_SETTINGS_JSON = CONFIG_DIR / "scoring_settings.json"
DATA_QUALITY_RULES_JSON = CONFIG_DIR / "data_quality_rules.json"
WEIGHTS_JSON = CONFIG_DIR / "weights_default.json"

for d in [RAW_DIR, PROCESSED_DIR, DATA_DIR / "db", CONFIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def read_excel_file(file) -> pd.DataFrame:
    return pd.read_excel(file, sheet_name=0, engine="openpyxl")


def save_uploaded_excel(file, filename: str = "input_koridor.xlsx") -> Path:
    path = RAW_DIR / filename
    with open(path, "wb") as f:
        f.write(file.getbuffer())
    return path


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_parquet(path: Path = SCORED_PARQUET) -> pd.DataFrame:
    return pd.read_parquet(path)


def has_raw_data() -> bool:
    return RAW_PARQUET.exists()


def has_scored_data() -> bool:
    return SCORED_PARQUET.exists()


def _read_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_formula_params(path: Path | None = None) -> list[dict]:
    if path is None:
        path = FORMULA_PARAMS_JSON
    params = _read_json(path, [])
    if not isinstance(params, list):
        raise ValueError("formula_parameters.json harus berupa list/array.")
    return params


def save_formula_params(params: list[dict], path: Path | None = None) -> None:
    if path is None:
        path = FORMULA_PARAMS_JSON
    backup_config_file(path)
    _write_json(path, params)


def load_data_quality_rules(path: Path | None = None) -> list[dict]:
    if path is None:
        path = DATA_QUALITY_RULES_JSON
    if not path.exists():
        from .scoring_engine import DEFAULT_DATA_QUALITY_RULES
        _write_json(path, DEFAULT_DATA_QUALITY_RULES)
        return DEFAULT_DATA_QUALITY_RULES
    rules = _read_json(path, [])
    if not isinstance(rules, list):
        raise ValueError("data_quality_rules.json harus berupa list/array.")
    return rules


def save_data_quality_rules(rules: list[dict], path: Path | None = None) -> None:
    if path is None:
        path = DATA_QUALITY_RULES_JSON
    backup_config_file(path)
    _write_json(path, rules)


def load_scoring_settings(path: Path | None = None) -> dict:
    if path is None:
        path = SCORING_SETTINGS_JSON
    from .scoring_engine import normalize_scoring_settings
    settings = _read_json(path, {})
    return normalize_scoring_settings(settings)


def save_scoring_settings(settings: dict, path: Path | None = None) -> None:
    if path is None:
        path = SCORING_SETTINGS_JSON
    backup_config_file(path)
    _write_json(path, settings)


def backup_config_file(path: Path) -> Path | None:
    """Make a simple .bak copy before overwriting config files."""
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    return bak


# Backward compatibility for older Scoring page/code.
def load_weights(path: Path | None = None) -> dict[str, float]:
    if path is None:
        path = WEIGHTS_JSON
    with open(path, "r", encoding="utf-8") as f:
        weights = json.load(f)
    total = sum(float(v) for v in weights.values())
    if total <= 0:
        raise ValueError("Total bobot harus lebih besar dari 0.")
    return {k: float(v) / total for k, v in weights.items()}


def save_weights(weights: dict[str, float], path: Path | None = None) -> None:
    if path is None:
        path = WEIGHTS_JSON
    total = sum(float(v) for v in weights.values())
    if total <= 0:
        raise ValueError("Total bobot harus lebih besar dari 0.")
    normalized = {k: float(v) / total for k, v in weights.items()}
    _write_json(path, normalized)
