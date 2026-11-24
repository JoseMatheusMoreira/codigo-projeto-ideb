"""Aplica o tratamento estrutural de IN_BANDA_LARGA."""

from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "censo_escolar_2024_municipal_ativa_anos_iniciais.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "censo_escolar_2024_municipal_ativa_anos_iniciais_sem_nulos.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "tratamento_banda_larga.json"


def treat_broadband() -> dict:
    data = pd.read_csv(INPUT_PATH, sep=";", encoding="utf-8-sig", low_memory=False)
    original = data["IN_BANDA_LARGA"].copy()

    missing_with_internet = int(
        (data["IN_BANDA_LARGA"].isna() & data["IN_INTERNET"].eq(1)).sum()
    )
    missing_without_internet = int(
        (data["IN_BANDA_LARGA"].isna() & data["IN_INTERNET"].eq(0)).sum()
    )
    nonmissing_without_internet = int(
        (data["IN_BANDA_LARGA"].notna() & data["IN_INTERNET"].eq(0)).sum()
    )

    if missing_with_internet != 0 or nonmissing_without_internet != 0:
        raise ValueError(
            "A regra estrutural não é válida: há inconsistências entre IN_INTERNET e IN_BANDA_LARGA."
        )

    # Regra documentada: sem internet, banda larga não é aplicável e recebe 0.
    data["IN_BANDA_LARGA"] = data["IN_BANDA_LARGA"].fillna(0).astype("int8")

    if data["IN_BANDA_LARGA"].isna().any():
        raise ValueError("Ainda existem nulos em IN_BANDA_LARGA após o tratamento.")
    if not data["IN_BANDA_LARGA"].isin([0, 1]).all():
        raise ValueError("IN_BANDA_LARGA contém valores fora de 0 e 1.")
    if not data.loc[data["IN_INTERNET"].eq(0), "IN_BANDA_LARGA"].eq(0).all():
        raise ValueError("Há escola sem internet marcada com banda larga após o tratamento.")

    changed = int(original.isna().sum())
    comparison_columns = [column for column in data.columns if column != "IN_BANDA_LARGA"]
    original_without_target = pd.read_csv(
        INPUT_PATH,
        sep=";",
        encoding="utf-8-sig",
        usecols=comparison_columns,
        low_memory=False,
    )
    unchanged_other_columns = data[comparison_columns].equals(original_without_target)
    if not unchanged_other_columns:
        raise ValueError("Alguma coluna além de IN_BANDA_LARGA foi alterada.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT_PATH, sep=";", index=False, encoding="utf-8-sig")

    report = {
        "input": str(INPUT_PATH),
        "output": str(OUTPUT_PATH),
        "rows": len(data),
        "columns": len(data.columns),
        "original_nulls_in_broadband": changed,
        "original_nulls_with_internet": missing_with_internet,
        "original_nulls_without_internet": missing_without_internet,
        "original_nonnull_without_internet": nonmissing_without_internet,
        "final_nulls_in_broadband": int(data["IN_BANDA_LARGA"].isna().sum()),
        "final_values_in_broadband": sorted(data["IN_BANDA_LARGA"].unique().tolist()),
        "other_columns_unchanged": unchanged_other_columns,
        "treatment_rule": "IN_BANDA_LARGA ausente recebe 0 somente porque IN_INTERNET=0",
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(treat_broadband(), ensure_ascii=False, indent=2))
