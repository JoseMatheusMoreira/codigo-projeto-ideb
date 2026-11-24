"""Agrega o Censo Escolar tratado para uma linha por município."""

from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "censo_escolar_2024_municipal_ativa_anos_iniciais_sem_nulos.csv"
IDEB_PATH = PROJECT_ROOT / "data" / "processed" / "ideb_municipal_2023_2025.csv"
OUTPUT_CENSO = PROJECT_ROOT / "data" / "processed" / "censo_escolar_2024_municipal_agregado.csv"
OUTPUT_MERGED = PROJECT_ROOT / "data" / "processed" / "base_ideb_censo_2024.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "agregacao_censo_municipio.json"


def aggregate_censo() -> dict:
    data = pd.read_csv(INPUT_PATH, sep=";", encoding="utf-8-sig", low_memory=False)
    ideb = pd.read_csv(IDEB_PATH, encoding="utf-8-sig", low_memory=False)

    for frame in [data, ideb]:
        frame["CO_MUNICIPIO"] = (
            pd.to_numeric(frame["CO_MUNICIPIO"], errors="raise")
            .astype("Int64")
            .astype("string")
            .str.zfill(7)
        )

    binary_columns = [
        column
        for column in data.columns
        if column.startswith("IN_") and column != "IN_FUND_AI"
    ]
    excluded_columns = ["QT_DOC_FUND_AI", "QT_TUR_FUND_AI", "IN_FUND_AI"]

    # Média de indicador 0/1 = proporção de escolas do município com o recurso.
    grouped_binary = data.groupby("CO_MUNICIPIO")[binary_columns].mean().add_prefix("prop_")
    grouped_binary.columns = [column.lower() for column in grouped_binary.columns]

    grouped_location = data.groupby("CO_MUNICIPIO").agg(
        prop_rural=("TP_LOCALIZACAO", lambda values: values.eq(2).mean()),
        prop_localizacao_diferenciada=(
            "TP_LOCALIZACAO_DIFERENCIADA",
            lambda values: values.ne(0).mean(),
        ),
    )

    grouped_counts = data.groupby("CO_MUNICIPIO").agg(
        n_escolas=("CO_ENTIDADE", "nunique"),
        total_matriculas_fund_ai=("QT_MAT_FUND_AI", "sum"),
        media_matriculas_fund_ai=("QT_MAT_FUND_AI", "mean"),
        mediana_matriculas_fund_ai=("QT_MAT_FUND_AI", "median"),
    )

    municipality_info = (
        data.groupby("CO_MUNICIPIO")[["SG_UF", "NO_MUNICIPIO"]]
        .first()
        .sort_index()
    )
    aggregated = municipality_info.join(grouped_counts).join(grouped_location).join(grouped_binary)
    aggregated = aggregated.reset_index()
    aggregated.to_csv(OUTPUT_CENSO, index=False, encoding="utf-8-sig")

    ideb_columns = ["CO_MUNICIPIO", "VL_OBSERVADO_2023", "VL_OBSERVADO_2025"]
    merged = ideb[ideb_columns].merge(aggregated, on="CO_MUNICIPIO", how="inner", validate="one_to_one")
    merged.to_csv(OUTPUT_MERGED, index=False, encoding="utf-8-sig")

    proportion_columns = [column for column in aggregated.columns if column.startswith("prop_")]
    proportions_valid = bool(
        aggregated[proportion_columns].ge(0).all().all()
        and aggregated[proportion_columns].le(1).all().all()
    )
    report = {
        "input_school_rows": len(data),
        "input_school_columns": len(data.columns),
        "aggregated_municipalities": len(aggregated),
        "aggregated_columns": len(aggregated.columns),
        "ideb_municipalities": ideb["CO_MUNICIPIO"].nunique(),
        "merged_rows": len(merged),
        "merged_columns": len(merged.columns),
        "ideb_without_censo": int(ideb["CO_MUNICIPIO"].nunique() - merged["CO_MUNICIPIO"].nunique()),
        "duplicate_municipalities_in_aggregate": int(aggregated["CO_MUNICIPIO"].duplicated().sum()),
        "proportions_between_zero_and_one": proportions_valid,
        "excluded_from_first_aggregate": excluded_columns,
        "aggregation_rules": {
            "IN_columns": "media dos indicadores 0/1, interpretada como proporção de escolas",
            "TP_LOCALIZACAO": "proporção de escolas rurais",
            "TP_LOCALIZACAO_DIFERENCIADA": "proporção de escolas em localização diferenciada",
            "QT_MAT_FUND_AI": "soma, média e mediana de matrículas",
            "CO_ENTIDADE": "contagem de escolas únicas",
        },
        "outputs": {
            "censo_aggregate": str(OUTPUT_CENSO),
            "ideb_censo_merge": str(OUTPUT_MERGED),
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(aggregate_censo(), ensure_ascii=False, indent=2))
