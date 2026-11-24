"""Diagnóstico de nulos, zeros e consistência da base Censo já filtrada.

Não imputa, não recodifica e não remove valores.
"""

from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "censo_escolar_2024_municipal_ativa_anos_iniciais.csv"
PROFILE_PATH = PROJECT_ROOT / "results" / "diagnostico_nulos_censo.csv"
REPORT_PATH = PROJECT_ROOT / "results" / "diagnostico_nulos_censo.json"


def diagnose() -> dict:
    data = pd.read_csv(INPUT_PATH, sep=";", encoding="utf-8-sig", low_memory=False)
    n_rows = len(data)

    identifier_columns = {
        "NU_ANO_CENSO",
        "SG_UF",
        "CO_MUNICIPIO",
        "NO_MUNICIPIO",
        "CO_ENTIDADE",
        "TP_DEPENDENCIA",
        "TP_SITUACAO_FUNCIONAMENTO",
        "TP_LOCALIZACAO",
        "TP_LOCALIZACAO_DIFERENCIADA",
        "IN_FUND_AI",
    }
    binary_columns = [c for c in data.columns if c.startswith("IN_") and c not in {"IN_FUND_AI"}]
    count_columns = [c for c in data.columns if c.startswith("QT_")]

    records = []
    for column in data.columns:
        series = data[column]
        non_null = int(series.notna().sum())
        zero_count = int(series.eq(0).sum()) if pd.api.types.is_numeric_dtype(series) else None
        if non_null:
            min_value = series.min() if pd.api.types.is_numeric_dtype(series) else None
            max_value = series.max() if pd.api.types.is_numeric_dtype(series) else None
        else:
            min_value = max_value = None

        if column in identifier_columns:
            category = "identificacao_filtro"
            recommendation = "manter; não imputar"
        elif column in binary_columns:
            category = "indicador_binario"
            recommendation = "zero parece categoria válida; avaliar nulo por variável"
        elif column in count_columns:
            category = "contagem"
            recommendation = "zero pode ser válido; validar coerência antes de imputar"
        else:
            category = "outro"
            recommendation = "avaliar definição no dicionário"

        records.append(
            {
                "variavel": column,
                "categoria": category,
                "tipo_lido": str(series.dtype),
                "n_linhas": n_rows,
                "nulos": int(series.isna().sum()),
                "percentual_nulos": round(series.isna().mean() * 100, 4),
                "zeros": zero_count,
                "percentual_zeros_sobre_nao_nulos": (
                    round(zero_count / non_null * 100, 4) if zero_count is not None and non_null else None
                ),
                "valores_distintos": int(series.nunique(dropna=True)),
                "minimo": min_value,
                "maximo": max_value,
                "recomendacao": recommendation,
            }
        )

    profile = pd.DataFrame(records)
    profile.to_csv(PROFILE_PATH, index=False, encoding="utf-8-sig")

    broadband_missing_no_internet = int(
        (data["IN_BANDA_LARGA"].isna() & data["IN_INTERNET"].eq(0)).sum()
    )
    broadband_missing_with_internet = int(
        (data["IN_BANDA_LARGA"].isna() & data["IN_INTERNET"].eq(1)).sum()
    )
    broadband_filled_without_internet = int(
        (data["IN_BANDA_LARGA"].notna() & data["IN_INTERNET"].eq(0)).sum()
    )
    subordinate_internet_inconsistent = {
        column: int(((data["IN_INTERNET"].eq(0)) & (data[column].eq(1))).sum())
        for column in [
            "IN_INTERNET_ALUNOS",
            "IN_INTERNET_ADMINISTRATIVO",
            "IN_INTERNET_APRENDIZAGEM",
        ]
    }
    teacher_zero = int(data["QT_DOC_FUND_AI"].eq(0).sum())
    class_zero = int(data["QT_TUR_FUND_AI"].eq(0).sum())
    teacher_and_class_zero = int(
        (data["QT_DOC_FUND_AI"].eq(0) & data["QT_TUR_FUND_AI"].eq(0)).sum()
    )
    students_positive = int((data["QT_MAT_FUND_AI"] > 0).sum())
    negative_counts = {
        column: int((data[column] < 0).sum()) for column in count_columns
    }

    report = {
        "input": str(INPUT_PATH),
        "rows": n_rows,
        "columns": len(data.columns),
        "total_null_cells": int(data.isna().sum().sum()),
        "columns_with_nulls": profile.loc[profile["nulos"] > 0, "variavel"].tolist(),
        "broadband_missing_no_internet": broadband_missing_no_internet,
        "broadband_missing_with_internet": broadband_missing_with_internet,
        "broadband_filled_without_internet": broadband_filled_without_internet,
        "subordinate_internet_ones_without_internet": subordinate_internet_inconsistent,
        "teacher_zero_rows": teacher_zero,
        "class_zero_rows": class_zero,
        "teacher_and_class_zero_rows": teacher_and_class_zero,
        "rows_with_positive_fund_ai_students": students_positive,
        "negative_count_values": negative_counts,
        "null_treatment_performed": False,
        "profile_output": str(PROFILE_PATH),
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(diagnose(), ensure_ascii=False, indent=2))
