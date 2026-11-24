"""Aplica o filtro metodológico de linhas do Censo, sem tratar nulos."""

from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "censo_escolar_2024_colunas_relevantes.csv"
IDEB_PATH = PROJECT_ROOT / "data" / "processed" / "ideb_municipal_2023_2025.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "censo_escolar_2024_municipal_ativa_anos_iniciais.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "censo_escolar_2024_filtro_linhas.json"
CHUNK_SIZE = 25_000


def _municipality_keys(values: pd.Series) -> set[str]:
    return set(values.dropna().astype("Int64").astype("string"))


def filter_rows() -> dict:
    """Filtra rede municipal, escola ativa e oferta de anos iniciais."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {INPUT_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    ideb_keys = set(
        pd.read_csv(IDEB_PATH, usecols=["CO_MUNICIPIO"], dtype={"CO_MUNICIPIO": "string"})[
            "CO_MUNICIPIO"
        ]
    )

    counts = {
        "input_rows": 0,
        "municipal_rows": 0,
        "municipal_active_rows": 0,
        "municipal_active_fund_ai_1_rows": 0,
        "municipal_active_fund_ai_0_rows": 0,
        "municipal_active_fund_ai_missing_rows": 0,
    }
    municipality_sets = {
        "input": set(),
        "municipal": set(),
        "municipal_active": set(),
        "municipal_active_fund_ai_1": set(),
    }
    written_rows = 0
    first_chunk = True

    for chunk in pd.read_csv(
        INPUT_PATH,
        sep=";",
        encoding="utf-8-sig",
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        counts["input_rows"] += len(chunk)
        municipality_sets["input"].update(_municipality_keys(chunk["CO_MUNICIPIO"]))

        municipal = chunk.loc[chunk["TP_DEPENDENCIA"].eq(3)].copy()
        active = municipal.loc[municipal["TP_SITUACAO_FUNCIONAMENTO"].eq(1)].copy()
        fund_ai_1 = active.loc[active["IN_FUND_AI"].eq(1)].copy()

        counts["municipal_rows"] += len(municipal)
        counts["municipal_active_rows"] += len(active)
        counts["municipal_active_fund_ai_1_rows"] += len(fund_ai_1)
        counts["municipal_active_fund_ai_0_rows"] += int(active["IN_FUND_AI"].eq(0).sum())
        counts["municipal_active_fund_ai_missing_rows"] += int(active["IN_FUND_AI"].isna().sum())

        municipality_sets["municipal"].update(_municipality_keys(municipal["CO_MUNICIPIO"]))
        municipality_sets["municipal_active"].update(_municipality_keys(active["CO_MUNICIPIO"]))
        municipality_sets["municipal_active_fund_ai_1"].update(
            _municipality_keys(fund_ai_1["CO_MUNICIPIO"])
        )

        fund_ai_1.to_csv(
            OUTPUT_PATH,
            sep=";",
            index=False,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            encoding="utf-8-sig",
        )
        written_rows += len(fund_ai_1)
        first_chunk = False

    counts.update(
        {
            "input_municipalities": len(municipality_sets["input"]),
            "municipal_municipalities": len(municipality_sets["municipal"]),
            "municipal_active_municipalities": len(municipality_sets["municipal_active"]),
            "municipal_active_fund_ai_1_municipalities": len(
                municipality_sets["municipal_active_fund_ai_1"]
            ),
            "ideb_target_municipalities": len(ideb_keys),
            "ideb_target_covered_by_filter": len(
                ideb_keys & municipality_sets["municipal_active_fund_ai_1"]
            ),
            "ideb_target_missing_from_filter": len(
                ideb_keys - municipality_sets["municipal_active_fund_ai_1"]
            ),
            "output_rows": written_rows,
            "output_columns": 33,
            "rows_preserved_only_by_filter": True,
            "null_treatment_performed": False,
            "output": str(OUTPUT_PATH),
        }
    )
    REPORT_PATH.write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
    return counts


if __name__ == "__main__":
    print(json.dumps(filter_rows(), ensure_ascii=False, indent=2))
