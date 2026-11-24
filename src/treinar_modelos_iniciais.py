"""Treina e avalia os primeiros modelos de regressão do projeto."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyRegressor


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "base_ideb_censo_ibge_2024.csv"
RESULTS = ROOT / "results"


def metrics(y_true: pd.Series, y_pred) -> dict[str, float]:
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
    feature_cols = [
        c for c in df.select_dtypes(include="number").columns
        if c not in {target, id_col}
    ]
    X = df[feature_cols]
    y = df[target]

    X_train, X_temp, y_train, y_temp, id_train, id_temp = train_test_split(
        X, y, df[id_col], test_size=0.30, random_state=42
    )
    X_valid, X_test, y_valid, y_test, id_valid, id_test = train_test_split(
        X_temp, y_temp, id_temp, test_size=0.50, random_state=42
    )
    split = pd.concat([
        pd.DataFrame({"CO_MUNICIPIO": id_train, "amostra": "treino"}),
        pd.DataFrame({"CO_MUNICIPIO": id_valid, "amostra": "validacao"}),
        pd.DataFrame({"CO_MUNICIPIO": id_test, "amostra": "teste"}),
    ]).sort_values("CO_MUNICIPIO")
    split.to_csv(RESULTS / "separacao_amostras.csv", index=False, encoding="utf-8")

    models = {
        "dummy_media": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", DummyRegressor(strategy="mean")),
        ]),
        "ridge": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]),
        "random_forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=300, max_depth=12, min_samples_leaf=2,
                random_state=42, n_jobs=-1
            )),
        ]),
        "hist_gradient_boosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", HistGradientBoostingRegressor(
                max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                l2_regularization=1.0, random_state=42
            )),
        ]),
    }

    validation_rows = []
    fitted = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        fitted[name] = model
        validation_rows.append({"modelo": name, **metrics(y_valid, model.predict(X_valid))})
    validation = pd.DataFrame(validation_rows).sort_values("RMSE")
    validation.to_csv(RESULTS / "modelos_validacao_inicial.csv", index=False, encoding="utf-8")

    selected_name = validation.iloc[0]["modelo"]
    selected_model = models[selected_name]
    X_train_valid = pd.concat([X_train, X_valid])
    y_train_valid = pd.concat([y_train, y_valid])
    selected_model.fit(X_train_valid, y_train_valid)
    test_metrics = metrics(y_test, selected_model.predict(X_test))
    final = {"modelo_escolhido": selected_name, **test_metrics}
    (RESULTS / "modelo_final_teste.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pred = pd.DataFrame({
        "CO_MUNICIPIO": id_test,
        "y_real": y_test,
        "y_predito": selected_model.predict(X_test),
    })
    pred["erro"] = pred["y_real"] - pred["y_predito"]
    pred.to_csv(RESULTS / "predicoes_teste_modelo_final.csv", index=False, encoding="utf-8")

    if selected_name == "random_forest":
        importances = selected_model.named_steps["model"].feature_importances_
        pd.DataFrame({"variavel": feature_cols, "importancia": importances}) \
            .sort_values("importancia", ascending=False) \
            .to_csv(RESULTS / "importancias_random_forest.csv", index=False, encoding="utf-8")

    report = {
        "n_treino": int(len(X_train)),
        "n_validacao": int(len(X_valid)),
        "n_teste": int(len(X_test)),
        "n_variaveis": int(len(feature_cols)),
        "variaveis": feature_cols,
        "criterio_selecao": "menor RMSE na validação",
        "validacao": validation.to_dict(orient="records"),
        "teste_modelo_escolhido": final,
    }
    (RESULTS / "experimento_modelos_iniciais.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
