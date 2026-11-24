"""Análise exploratória e auditoria inicial da base municipal final."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "base_ideb_censo_ibge_2024.csv"
RESULTS = ROOT / "results"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT)
    target = "VL_OBSERVADO_2025"
    id_col = "CO_MUNICIPIO"
    numeric = df.select_dtypes(include="number").columns.tolist()
    feature_numeric = [c for c in numeric if c not in {target, id_col, "VL_OBSERVADO_2023"}]

    nulls = df.isna().sum().rename("nulos").to_frame()
    nulls["percentual"] = (nulls["nulos"] / len(df) * 100).round(4)
    nulls = nulls.sort_values(["nulos", "percentual"], ascending=False)
    nulls.to_csv(RESULTS / "eda_nulos_base_final.csv", encoding="utf-8")

    summary = df[feature_numeric + ["VL_OBSERVADO_2023", target]].describe().T
    summary["nulos"] = df[summary.index].isna().sum()
    summary["n_unicos"] = df[summary.index].nunique(dropna=True)
    summary.to_csv(RESULTS / "eda_resumo_numerico.csv", encoding="utf-8")

    corr_frame = df[feature_numeric + ["VL_OBSERVADO_2023", target]]
    # Spearman pode ser calculada como Pearson sobre os postos, sem depender de scipy.
    correlations = pd.DataFrame({
        "pearson": corr_frame.drop(columns=target).corrwith(corr_frame[target], method="pearson"),
        "spearman": corr_frame.drop(columns=target).rank().corrwith(corr_frame[target].rank(), method="pearson"),
    }).sort_values("spearman", ascending=False)
    correlations.to_csv(RESULTS / "eda_correlacoes_com_ideb_2025.csv", encoding="utf-8")

    uf = df.groupby("SG_UF").agg(
        municipios=(id_col, "nunique"),
        ideb_2023_medio=("VL_OBSERVADO_2023", "mean"),
        ideb_2025_medio=(target, "mean"),
        pib_per_capita_medio=("PIB_PER_CAPITA_2023_APROX", "mean"),
        prop_rural_media=("prop_rural", "mean"),
    ).sort_values("ideb_2025_medio", ascending=False)
    uf.to_csv(RESULTS / "eda_por_uf.csv", encoding="utf-8")

    target_stats = df[target].describe(percentiles=[.01, .05, .25, .5, .75, .95, .99]).to_dict()
    target_stats["nulos"] = int(df[target].isna().sum())
    target_stats["duplicidades_chave"] = int(df[id_col].duplicated().sum())

    # Valores atípicos por IQR: sinalização exploratória, sem remoção automática.
    outliers = []
    for col in feature_numeric + ["VL_OBSERVADO_2023", target]:
        s = df[col].dropna()
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers.append({
            "variavel": col,
            "limite_inferior_iqr": low,
            "limite_superior_iqr": high,
            "n_atipicos_iqr": int(((s < low) | (s > high)).sum()),
            "percentual_atipicos": float(((s < low) | (s > high)).mean() * 100),
        })
    pd.DataFrame(outliers).to_csv(RESULTS / "eda_atipicos_iqr.csv", index=False, encoding="utf-8")

    # Gráficos simples para a apresentação.
    plt.figure(figsize=(8, 5))
    plt.hist(df[target].dropna(), bins=25, color="#2563eb", edgecolor="white")
    plt.xlabel("IDEB 2025")
    plt.ylabel("Municípios")
    plt.title("Distribuição do IDEB 2025")
    plt.tight_layout()
    plt.savefig(RESULTS / "eda_distribuicao_ideb_2025.png", dpi=160)
    plt.close()

    top_corr = correlations.head(10).sort_values("spearman")
    plt.figure(figsize=(8, 5))
    plt.barh(top_corr.index, top_corr["spearman"], color="#0f766e")
    plt.xlabel("Correlação de Spearman com o IDEB 2025")
    plt.title("Variáveis com maior associação monotônica ao alvo")
    plt.tight_layout()
    plt.savefig(RESULTS / "eda_correlacoes_ideb_2025.png", dpi=160)
    plt.close()

    plt.figure(figsize=(7, 5))
    plt.scatter(df["VL_OBSERVADO_2023"], df[target], s=8, alpha=.35, color="#7c3aed")
    plt.xlabel("IDEB 2023")
    plt.ylabel("IDEB 2025")
    plt.title("Relação entre IDEB histórico e alvo")
    plt.tight_layout()
    plt.savefig(RESULTS / "eda_ideb_2023_vs_2025.png", dpi=160)
    plt.close()

    report = {
        "linhas": int(len(df)),
        "colunas": int(df.shape[1]),
        "unidade_observacao": "município com rede municipal e oferta de anos iniciais no Censo Escolar 2024",
        "municipios_unicos": int(df[id_col].nunique()),
        "duplicidades_chave": int(df[id_col].duplicated().sum()),
        "nulos_total": int(df.isna().sum().sum()),
        "nulos_por_coluna": {k: int(v) for k, v in df.isna().sum().items() if v},
        "ideb_2025": target_stats,
        "correlacao_spearman_ideb_2023_ideb_2025": float(correlations.loc["VL_OBSERVADO_2023", "spearman"]),
        "features_potencialmente_posteriores_a_2024": [],
        "observacao_atipicos": "Os pontos atípicos foram apenas sinalizados por IQR; nenhuma linha foi removida.",
    }
    (RESULTS / "eda_base_final.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
