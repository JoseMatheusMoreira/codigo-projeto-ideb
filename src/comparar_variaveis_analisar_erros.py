"""Compara grupos de variáveis e analisa os erros do modelo selecionado."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "base_ideb_censo_ibge_2024.csv"
RESULTS = ROOT / "results"


def model(alpha: float) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=alpha)),
    ])


def score(y_true, y_pred) -> dict[str, float]:
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(root_mean_squared_error(y_true, y_pred)),
        "R2": float(r2_score(y_true, y_pred)),
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT)
    target = "VL_OBSERVADO_2025"
    id_col = "CO_MUNICIPIO"
    numeric = df.select_dtypes(include="number").columns.tolist()
    all_features = [c for c in numeric if c not in {id_col, target}]
    ideb = ["VL_OBSERVADO_2023"]
    ibge = [c for c in all_features if c.startswith(("PIB_", "POPULACAO_"))]
    censo = [c for c in all_features if c not in ideb + ibge]
    groups = {
        "ideb_2023": ideb,
        "censo": censo,
        "ibge": ibge,
        "ideb_censo": ideb + censo,
        "ideb_ibge": ideb + ibge,
        "todas": all_features,
    }

    X_train, X_temp, y_train, y_temp, id_train, id_temp = train_test_split(
        df[all_features], df[target], df[id_col], test_size=.30, random_state=42
    )
    X_valid, X_test, y_valid, y_test, id_valid, id_test = train_test_split(
        X_temp, y_temp, id_temp, test_size=.50, random_state=42
    )

    alpha_values = [.01, .1, 1.0, 10.0, 100.0]
    rows = []
    fitted_validation = {}
    for group_name, columns in groups.items():
        for alpha in alpha_values:
            fitted = model(alpha)
            fitted.fit(X_train[columns], y_train)
            result = score(y_valid, fitted.predict(X_valid[columns]))
            rows.append({"grupo": group_name, "alpha": alpha, "n_variaveis": len(columns), **result})
            fitted_validation[(group_name, alpha)] = fitted
    comparison = pd.DataFrame(rows).sort_values("RMSE")
    comparison.to_csv(RESULTS / "comparacao_grupos_alpha_validacao.csv", index=False, encoding="utf-8")

    selected = comparison.iloc[0]
    selected_group = selected["grupo"]
    selected_alpha = float(selected["alpha"])
    selected_columns = groups[selected_group]
    final_model = model(selected_alpha)
    final_model.fit(pd.concat([X_train[selected_columns], X_valid[selected_columns]]), pd.concat([y_train, y_valid]))
    pred = final_model.predict(X_test[selected_columns])
    test_metrics = score(y_test, pred)

    pred_df = pd.DataFrame({
        "CO_MUNICIPIO": id_test.values,
        "SG_UF": df.set_index(id_col).loc[id_test.values, "SG_UF"].values,
        "NO_MUNICIPIO": df.set_index(id_col).loc[id_test.values, "NO_MUNICIPIO_x"].values,
        "ideb_2025_real": y_test.values,
        "ideb_2025_predito": pred,
    })
    pred_df["erro"] = pred_df["ideb_2025_real"] - pred_df["ideb_2025_predito"]
    pred_df["erro_absoluto"] = pred_df["erro"].abs()
    pred_df.to_csv(RESULTS / "predicoes_teste_configuracao_selecionada.csv", index=False, encoding="utf-8")

    pred_df["faixa_alvo"] = pd.qcut(pred_df["ideb_2025_real"], 4, duplicates="drop")
    por_faixa = pred_df.groupby("faixa_alvo", observed=True).agg(
        municipios=("CO_MUNICIPIO", "count"),
        erro_medio=("erro", "mean"),
        erro_absoluto_medio=("erro_absoluto", "mean"),
    ).reset_index()
    por_faixa.to_csv(RESULTS / "erros_por_faixa_ideb.csv", index=False, encoding="utf-8")

    por_uf = pred_df.groupby("SG_UF").agg(
        municipios=("CO_MUNICIPIO", "count"),
        erro_medio=("erro", "mean"),
        erro_absoluto_medio=("erro_absoluto", "mean"),
    ).sort_values("erro_absoluto_medio", ascending=False)
    por_uf.to_csv(RESULTS / "erros_por_uf.csv", encoding="utf-8")
    pred_df.nlargest(20, "erro_absoluto").to_csv(RESULTS / "maiores_erros_teste.csv", index=False, encoding="utf-8")

    report = {
        "criterio_selecao": "menor RMSE na validação",
        "grupo_escolhido": selected_group,
        "alpha_escolhido": selected_alpha,
        "n_variaveis": len(selected_columns),
        "variaveis": selected_columns,
        "metricas_teste": test_metrics,
        "interpretacao_erro": "erro = IDEB real - IDEB predito; positivo indica subestimação pelo modelo e negativo indica superestimação.",
        "maior_erro_absoluto": float(pred_df["erro_absoluto"].max()),
        "erro_medio_teste": float(pred_df["erro"].mean()),
    }
    (RESULTS / "comparacao_erros_final.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
