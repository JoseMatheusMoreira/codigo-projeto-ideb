"""Valida o formato do Censo Escolar 2024 e seleciona colunas relevantes.

Esta etapa não trata valores nulos nem filtra linhas. O arquivo bruto não é alterado.
"""

from pathlib import Path
import json
import os

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = Path(
    os.environ.get(
        "CENSO_ESCOLAR_PATH",
        PROJECT_ROOT / "data" / "raw" / "microdados_ed_basica_2024.csv",
    )
)
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "censo_escolar_2024_colunas_relevantes.csv"
VALIDATION_PATH = PROJECT_ROOT / "results" / "censo_escolar_2024_validacao.json"
CHUNK_SIZE = 25_000

# Colunas de oferta educacional, infraestrutura, tecnologia e anos iniciais.
SELECTED_COLUMNS = [
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
    "IN_AGUA_POTAVEL",
    "IN_AGUA_REDE_PUBLICA",
    "IN_ENERGIA_REDE_PUBLICA",
    "IN_ESGOTO_REDE_PUBLICA",
    "IN_ESGOTO_FOSSA_SEPTICA",
    "IN_LIXO_SERVICO_COLETA",
    "IN_BANHEIRO",
    "IN_BIBLIOTECA",
    "IN_SALA_LEITURA",
    "IN_LABORATORIO_INFORMATICA",
    "IN_LABORATORIO_CIENCIAS",
    "IN_QUADRA_ESPORTES",
    "IN_QUADRA_ESPORTES_COBERTA",
    "IN_COMPUTADOR",
    "IN_EQUIP_MULTIMIDIA",
    "IN_INTERNET",
    "IN_INTERNET_ALUNOS",
    "IN_INTERNET_ADMINISTRATIVO",
    "IN_INTERNET_APRENDIZAGEM",
    "IN_BANDA_LARGA",
    "QT_MAT_FUND_AI",
    "QT_DOC_FUND_AI",
    "QT_TUR_FUND_AI",
]


def validate_and_filter(
    source_path: Path = SOURCE_PATH,
    output_path: Path = OUTPUT_PATH,
) -> dict:
    """Valida estrutura e grava apenas as colunas selecionadas."""
    if not source_path.exists():
        raise FileNotFoundError(f"Fonte não encontrada: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)

    header = pd.read_csv(
        source_path,
        sep=";",
        encoding="latin1",
        nrows=0,
        low_memory=False,
    )
    all_columns = list(header.columns)
    missing_selected = [c for c in SELECTED_COLUMNS if c not in all_columns]
    if missing_selected:
        raise ValueError(f"Colunas selecionadas ausentes na fonte: {missing_selected}")

    seen_entities: set[str] = set()
    total_rows = 0
    null_municipality_rows = 0
    null_entity_rows = 0
    duplicate_entity_rows = 0
    malformed_or_parse_errors = []
    years = set()
    dependency_values = set()
    status_values = set()
    fund_ai_values = set()

    # Validação em blocos para evitar carregar o arquivo completo na memória.
    try:
        for chunk in pd.read_csv(
            source_path,
            sep=";",
            encoding="latin1",
            chunksize=CHUNK_SIZE,
            low_memory=False,
            on_bad_lines="error",
        ):
            total_rows += len(chunk)
            years.update(chunk["NU_ANO_CENSO"].dropna().unique().tolist())
            dependency_values.update(chunk["TP_DEPENDENCIA"].dropna().unique().tolist())
            status_values.update(
                chunk["TP_SITUACAO_FUNCIONAMENTO"].dropna().unique().tolist()
            )
            fund_ai_values.update(chunk["IN_FUND_AI"].dropna().unique().tolist())
            null_municipality_rows += int(chunk["CO_MUNICIPIO"].isna().sum())
            null_entity_rows += int(chunk["CO_ENTIDADE"].isna().sum())

            entities = chunk["CO_ENTIDADE"].dropna().astype("Int64").astype(str).tolist()
            unique_in_chunk = set(entities)
            duplicate_entity_rows += len(entities) - len(unique_in_chunk)
            duplicate_entity_rows += sum(entity in seen_entities for entity in unique_in_chunk)
            seen_entities.update(unique_in_chunk)
    except Exception as error:
        malformed_or_parse_errors.append(f"{type(error).__name__}: {error}")

    validation = {
        "source": str(source_path),
        "delimiter": ";",
        "encoding": "latin1",
        "header_columns": len(all_columns),
        "header_columns_unique": len(set(all_columns)) == len(all_columns),
        "selected_columns": SELECTED_COLUMNS,
        "selected_columns_count": len(SELECTED_COLUMNS),
        "missing_selected_columns": missing_selected,
        "total_rows": total_rows,
        "distinct_entities": len(seen_entities),
        "null_municipality_rows": null_municipality_rows,
        "null_entity_rows": null_entity_rows,
        "duplicate_entity_rows": duplicate_entity_rows,
        "years_found": sorted(years),
        "dependency_values_found": sorted(dependency_values),
        "status_values_found": sorted(status_values),
        "fund_ai_values_found": sorted(fund_ai_values),
        "parse_errors": malformed_or_parse_errors,
        "format_valid_for_selection": (
            len(all_columns) == 426
            and len(set(all_columns)) == len(all_columns)
            and not missing_selected
            and total_rows > 0
            and not malformed_or_parse_errors
            and null_municipality_rows == 0
            and null_entity_rows == 0
            and duplicate_entity_rows == 0
            and years == {2024}
            and dependency_values.issubset({1, 2, 3, 4})
            and status_values.issubset({1, 2, 3})
            and fund_ai_values.issubset({0, 1})
        ),
    }

    if not validation["format_valid_for_selection"]:
        VALIDATION_PATH.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        raise ValueError(
            "A validação do formato falhou. Consulte "
            f"{VALIDATION_PATH} antes de continuar."
        )

    # Segunda passagem: grava apenas as colunas selecionadas, sem recodificação.
    first_chunk = True
    written_rows = 0
    for chunk in pd.read_csv(
        source_path,
        sep=";",
        encoding="latin1",
        usecols=SELECTED_COLUMNS,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        chunk.to_csv(
            output_path,
            sep=";",
            index=False,
            mode="w" if first_chunk else "a",
            header=first_chunk,
            encoding="utf-8-sig",
        )
        written_rows += len(chunk)
        first_chunk = False

    validation["output"] = str(output_path)
    validation["output_rows"] = written_rows
    validation["output_columns"] = len(SELECTED_COLUMNS)
    validation["output_encoding"] = "utf-8-sig"
    validation["output_delimiter"] = ";"
    validation["output_matches_source_rows"] = written_rows == total_rows
    VALIDATION_PATH.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return validation


if __name__ == "__main__":
    result = validate_and_filter()
    print(json.dumps(result, ensure_ascii=False, indent=2))
