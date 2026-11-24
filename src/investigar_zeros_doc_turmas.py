"""Investiga os zeros de docentes e turmas dos anos iniciais."""

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
RESULTS_DIR = PROJECT_ROOT / "results"
PROFILE_PATH = RESULTS_DIR / "zeros_doc_turmas_por_grupo.csv"
UF_PATH = RESULTS_DIR / "zeros_doc_turmas_por_uf.csv"
MUNICIPALITY_PATH = RESULTS_DIR / "zeros_doc_turmas_por_municipio.csv"
REPORT_PATH = RESULTS_DIR / "analise_zeros_doc_turmas.json"

USECOLS = [
    "CO_MUNICIPIO",
    "CO_ENTIDADE",
    "SG_UF",
    "TP_LOCALIZACAO",
    "TP_DEPENDENCIA",
    "TP_SITUACAO_FUNCIONAMENTO",
    "IN_FUND_AI",
    "IN_FUND_AF",
    "IN_EJA_FUND",
    "IN_REGULAR",
    "QT_MAT_FUND_AI",
    "QT_DOC_BAS",
    "QT_DOC_FUND",
    "QT_DOC_FUND_AI",
    "QT_TUR_BAS",
    "QT_TUR_FUND",
    "QT_TUR_FUND_AI",
]


def investigate() -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(
        SOURCE_PATH,
        sep=";",
        encoding="latin1",
        usecols=USECOLS,
        low_memory=False,
    )

    # Reproduz o recorte adotado no projeto. Nenhum nulo é preenchido.
    data = data.loc[
        data["TP_DEPENDENCIA"].eq(3)
        & data["TP_SITUACAO_FUNCIONAMENTO"].eq(1)
        & data["IN_FUND_AI"].eq(1)
    ].copy()
    data["zero_doc_turma"] = data["QT_DOC_FUND_AI"].eq(0) & data["QT_TUR_FUND_AI"].eq(0)
    data["grupo"] = data["zero_doc_turma"].map(
        {True: "zero_docentes_e_turmas", False: "algum_docente_ou_turma"}
    )
    data["localizacao"] = data["TP_LOCALIZACAO"].map({1: "Urbana", 2: "Rural"})

    group_rows = []
    for group, subset in data.groupby("grupo", sort=False):
        group_rows.append(
            {
                "grupo": group,
                "escolas": len(subset),
                "percentual_escolas": round(len(subset) / len(data) * 100, 4),
                "matriculas_ai_media": round(subset["QT_MAT_FUND_AI"].mean(), 2),
                "matriculas_ai_mediana": float(subset["QT_MAT_FUND_AI"].median()),
                "docentes_fund_media": round(subset["QT_DOC_FUND"].mean(), 2),
                "turmas_fund_media": round(subset["QT_TUR_FUND"].mean(), 2),
                "percentual_rural": round(subset["TP_LOCALIZACAO"].eq(2).mean() * 100, 4),
                "percentual_com_anos_finais": round(subset["IN_FUND_AF"].eq(1).mean() * 100, 4),
                "percentual_com_eja_fundamental": round(subset["IN_EJA_FUND"].eq(1).mean() * 100, 4),
                "percentual_regular": round(subset["IN_REGULAR"].eq(1).mean() * 100, 4),
            }
        )
    group_profile = pd.DataFrame(group_rows)
    group_profile.to_csv(PROFILE_PATH, index=False, encoding="utf-8-sig")

    by_uf = (
        data.groupby("SG_UF")
        .agg(escolas=("CO_ENTIDADE", "size"), zeros_doc_turma=("zero_doc_turma", "sum"))
        .reset_index()
    )
    by_uf["percentual_zeros"] = (by_uf["zeros_doc_turma"] / by_uf["escolas"] * 100).round(4)
    by_uf = by_uf.sort_values("percentual_zeros", ascending=False)
    by_uf.to_csv(UF_PATH, index=False, encoding="utf-8-sig")

    by_municipality = (
        data.groupby("CO_MUNICIPIO")
        .agg(
            escolas=("CO_ENTIDADE", "size"),
            zeros_doc_turma=("zero_doc_turma", "sum"),
            uf=("SG_UF", "first"),
            nome_localizacao=("localizacao", lambda values: values.mode().iat[0]),
        )
        .reset_index()
    )
    by_municipality["proporcao_zeros"] = (
        by_municipality["zeros_doc_turma"] / by_municipality["escolas"]
    ).round(6)
    by_municipality.to_csv(MUNICIPALITY_PATH, index=False, encoding="utf-8-sig")

    zero = data.loc[data["zero_doc_turma"]]
    report = {
        "source": str(SOURCE_PATH),
        "filtered_rows": len(data),
        "zero_doc_turma_rows": len(zero),
        "zero_doc_turma_percent": round(len(zero) / len(data) * 100, 4),
        "zero_rows_with_positive_students": int((zero["QT_MAT_FUND_AI"] > 0).sum()),
        "zero_rows_with_positive_fund_teachers": int((zero["QT_DOC_FUND"] > 0).sum()),
        "zero_rows_with_positive_fund_classes": int((zero["QT_TUR_FUND"] > 0).sum()),
        "zero_rows_urban": int((zero["TP_LOCALIZACAO"] == 1).sum()),
        "zero_rows_rural": int((zero["TP_LOCALIZACAO"] == 2).sum()),
        "zero_rate_urban_percent": round(
            data.loc[data["TP_LOCALIZACAO"] == 1, "zero_doc_turma"].mean() * 100, 4
        ),
        "zero_rate_rural_percent": round(
            data.loc[data["TP_LOCALIZACAO"] == 2, "zero_doc_turma"].mean() * 100, 4
        ),
        "municipalities_with_any_zero_school": int((by_municipality["zeros_doc_turma"] > 0).sum()),
        "municipalities_all_schools_zero": int(
            (by_municipality["zeros_doc_turma"] == by_municipality["escolas"]).sum()
        ),
        "municipalities_total": len(by_municipality),
        "municipality_zero_share_median": float(by_municipality["proporcao_zeros"].median()),
        "municipality_zero_share_q75": float(by_municipality["proporcao_zeros"].quantile(0.75)),
        "municipality_zero_share_max": float(by_municipality["proporcao_zeros"].max()),
        "decision": "manter_zeros_observados_e_nao_imputar_nesta_etapa",
        "feature_recommendation": "nao_usar_docentes_e_turmas_ai_na_primeira_modelagem_sem_validacao_conceitual",
        "outputs": {
            "group_profile": str(PROFILE_PATH),
            "by_uf": str(UF_PATH),
            "by_municipality": str(MUNICIPALITY_PATH),
        },
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(investigate(), ensure_ascii=False, indent=2))
