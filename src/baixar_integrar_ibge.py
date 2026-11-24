"""Baixa dados municipais do IBGE/SIDRA e integra-os à base do projeto.

Fontes consultadas:
- SIDRA 5938: PIB municipal a preços correntes, ano 2023, variável 37.
- SIDRA 9514: população residente, Censo 2022, variável 93, sexo/idade totais.

O PIB per capita é calculado como PIB de 2023 / população de 2022. Essa
aproximação é intencional e fica documentada porque os anos de referência não
são idênticos.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pandas as pd
import requests
import urllib3


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"


def municipality_key(series: pd.Series) -> pd.Series:
    return (
        pd.to_numeric(series, errors="coerce")
        .astype("Int64")
        .astype("string")
        .str.zfill(7)
    )


def sidra_get(table: int, variable: int, period: int) -> list[dict]:
    url = (
        f"https://apisidra.ibge.gov.br/values/t/{table}/n6/all/"
        f"v/{variable}/p/{period}"
    )
    response = requests.get(url, timeout=120, verify=False)
    response.raise_for_status()
    return response.json()


def convert_records(records: list[dict], value_name: str) -> pd.DataFrame:
    df = pd.DataFrame(records[1:])
    if df.empty:
        raise ValueError(f"A resposta SIDRA para {value_name} veio vazia.")
    out = df[["D1C", "D1N", "V"]].copy()
    out = out.rename(columns={"D1C": "CO_MUNICIPIO", "D1N": "NO_MUNICIPIO", "V": value_name})
    out["CO_MUNICIPIO"] = municipality_key(out["CO_MUNICIPIO"])
    out[value_name] = pd.to_numeric(out[value_name].astype(str).str.replace(",", "."), errors="coerce")
    return out


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

    pib_records = sidra_get(table=5938, variable=37, period=2023)
    pop_records = sidra_get(table=9514, variable=93, period=2022)

    (RAW / "sidra_5938_pib_municipal_2023.json").write_text(
        json.dumps(pib_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RAW / "sidra_9514_populacao_censo_2022.json").write_text(
        json.dumps(pop_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pib = convert_records(pib_records, "PIB_2023_mil_reais")
    pop = convert_records(pop_records, "POPULACAO_2022")
    pop = pop[pop["NO_MUNICIPIO"].notna()].copy()

    # A tabela 9514 possui dimensões adicionais. Mantemos uma linha por município.
    pop = pop.drop_duplicates("CO_MUNICIPIO", keep="first")
    ibge = pib.merge(pop, on=["CO_MUNICIPIO"], how="inner", suffixes=("", "_POP"))
    ibge = ibge[["CO_MUNICIPIO", "NO_MUNICIPIO", "PIB_2023_mil_reais", "POPULACAO_2022"]]
    ibge["PIB_PER_CAPITA_2023_APROX"] = (
        ibge["PIB_2023_mil_reais"] * 1000 / ibge["POPULACAO_2022"]
    )

    if ibge["CO_MUNICIPIO"].duplicated().any():
        raise ValueError("A base IBGE ficou com municípios duplicados.")
    if (ibge["POPULACAO_2022"] <= 0).any():
        raise ValueError("Há população não positiva na base IBGE.")

    ibge.to_csv(PROCESSED / "ibge_municipios_2022_2023.csv", index=False, encoding="utf-8")

    base = pd.read_csv(PROCESSED / "base_ideb_censo_2024.csv")
    base["CO_MUNICIPIO"] = municipality_key(base["CO_MUNICIPIO"])
    integrada = base.merge(ibge, on="CO_MUNICIPIO", how="left", validate="one_to_one")
    integrada.to_csv(PROCESSED / "base_ideb_censo_ibge_2024.csv", index=False, encoding="utf-8")

    report = {
        "pib_linhas_sidra": int(len(pib)),
        "populacao_linhas_sidra": int(len(pop)),
        "ibge_linhas_integradas": int(len(ibge)),
        "base_antes": int(len(base)),
        "base_depois": int(len(integrada)),
        "municipios_sem_ibge": int(integrada["PIB_2023_mil_reais"].isna().sum()),
        "chaves_duplicadas_ibge": int(ibge["CO_MUNICIPIO"].duplicated().sum()),
        "observacao_pib_per_capita": "PIB 2023 / população do Censo 2022; indicador aproximado por diferença de ano.",
    }
    (RESULTS / "integracao_ibge.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
