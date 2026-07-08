from __future__ import annotations
import argparse
from pathlib import Path
import sys
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from scoring.io import RAW_PARQUET, SCORED_PARQUET, save_parquet, load_formula_params, load_scoring_settings, load_data_quality_rules
from scoring.validation import validate_schema
from scoring.scoring_engine import compute_scores_dynamic


def main():
    parser = argparse.ArgumentParser(description="Process Excel koridor prioritas into scored Parquet.")
    parser.add_argument("excel_path", help="Path Excel agregasi koridor")
    args = parser.parse_args()

    excel_path = Path(args.excel_path)
    df = pd.read_excel(excel_path, sheet_name=0, engine="openpyxl")
    missing = validate_schema(df)
    if missing:
        raise SystemExit(f"Kolom wajib hilang: {missing}")
    save_parquet(df, RAW_PARQUET)
    params = load_formula_params()
    settings = load_scoring_settings()
    rules = load_data_quality_rules()
    scored = compute_scores_dynamic(df, params, penalty_factor=float(settings.get("penalty_factor", 0.30)), data_quality_rules=rules, scoring_settings=settings)
    save_parquet(scored, SCORED_PARQUET)
    print(f"OK: {len(scored):,} koridor diproses dengan rumus dinamis")
    print(f"Raw: {RAW_PARQUET}")
    print(f"Score: {SCORED_PARQUET}")

if __name__ == "__main__":
    main()
