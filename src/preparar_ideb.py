"""Prepara a base municipal do IDEB 2023/2025 a partir do arquivo bruto."""

from pathlib import Path

import numpy as np
import pandas as pd


SOURCE_FILE = "ideb_anos_iniciais_municipios_2025.xlsx"
OUTPUT_FILE = "ideb_municipal_2023_2025.csv"
SUMMARY_FILE = "ideb_municipal_2023_2025_resumo.csv"
HEADER_ROW = 9  # índice zero; corresponde à linha 10 no Excel


def prepare_base(project_root: str | Path | None = None) -> dict:
    """Lê, filtra e valida a base municipal com IDEB 2023 e 2025."""
    if project_root is None:
        project_root = Path(__file__).resolve().parents[1]
    project_root = Path(project_root)

    source_path = project_root / "data" / "raw" / SOURCE_FILE
    processed_dir = project_root / "data" / "processed"
    results_dir = project_root / "results"
    processed_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {source_path}")

    raw = pd.read_excel(source_path, header=HEADER_ROW)
    required_columns = {
        "CO_MUNICIPIO",
        "REDE",
        "VL_OBSERVADO_2023",
        "VL_OBSERVADO_2025",
    }
    missing_columns = required_columns.difference(raw.columns)
    if missing_columns:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(missing_columns)}")

    municipal = raw.loc[
        raw["REDE"].astype("string").str.strip().eq("Municipal")
    ].copy()

    # Mantém o código como identificador textual de sete dígitos.
    municipal["CO_MUNICIPIO"] = (
        pd.to_numeric(municipal["CO_MUNICIPIO"], errors="coerce")
        .astype("Int64")
        .astype("string")
        .str.zfill(7)
    )

    # O arquivo usa '-' para indicar ausência e algumas colunas usam vírgula decimal.
    municipal = municipal.replace({"-": np.nan, "": np.nan, " ": np.nan})
    excluded_from_numeric = {"SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "REDE"}
    numeric_columns = [
        column for column in municipal.columns if column not in excluded_from_numeric
    ]
    for column in numeric_columns:
        municipal[column] = pd.to_numeric(
            municipal[column].astype("string").str.replace(",", ".", regex=False),
            errors="coerce",
        )

    if municipal["CO_MUNICIPIO"].isna().any():
        raise ValueError("Há códigos de município ausentes ou inválidos.")
    if municipal["CO_MUNICIPIO"].duplicated().any():
        duplicated = municipal.loc[
            municipal["CO_MUNICIPIO"].duplicated(keep=False), "CO_MUNICIPIO"
        ].unique()
        raise ValueError(f"Há municípios duplicados na rede municipal: {duplicated[:10]}")

    base = municipal.dropna(
        subset=["VL_OBSERVADO_2023", "VL_OBSERVADO_2025"]
    ).copy()
    base = base.sort_values("CO_MUNICIPIO").reset_index(drop=True)

    expected_rows = 5196
    if len(base) != expected_rows:
        raise ValueError(
            f"A interseção encontrada tem {len(base)} municípios; esperado: {expected_rows}."
        )

    output_path = processed_dir / OUTPUT_FILE
    summary_path = results_dir / SUMMARY_FILE
    base.to_csv(output_path, index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(
        {
            "indicador": [
                "linhas_brutas",
                "linhas_rede_municipal",
                "municipios_unicos_municipal",
                "ideb_2023_disponivel",
                "ideb_2025_disponivel",
                "intersecao_ideb_2023_2025",
            ],
            "valor": [
                len(raw),
                len(municipal),
                municipal["CO_MUNICIPIO"].nunique(),
                municipal["VL_OBSERVADO_2023"].notna().sum(),
                municipal["VL_OBSERVADO_2025"].notna().sum(),
                len(base),
            ],
        }
    )
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    return {
        "raw": raw,
        "municipal": municipal,
        "base": base,
        "summary": summary,
        "output_path": output_path,
        "summary_path": summary_path,
    }


if __name__ == "__main__":
    result = prepare_base()
    print(result["summary"].to_string(index=False))
    print(f"\nBase salva em: {result['output_path']}")
