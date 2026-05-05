"""
Entrenamiento y serialización de los modelos del Algoritmo Cupido.

Modelos (Hito 3):
  - Clasificación : LogisticRegression + StandardScaler Pipeline
  - Regresión     : Ridge(alpha=1.0)  — target log-transformado (np.log1p)

Salida: models/clf_model.pkl  y  models/reg_model.pkl
"""
import os

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import DATA_PATH, MODELS_DIR, RANDOM_STATE, TEST_SIZE
from src.data.service import load_dataset
from src.features.service import create_pair_features, get_clf_features, get_reg_features


def _evaluate_clf(model, X, y) -> None:
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]
    print(f"  Accuracy : {(y_pred == y).mean():.4f}")
    print(f"  F1-Score : {f1_score(y, y_pred):.4f}")
    print(f"  ROC-AUC  : {roc_auc_score(y, y_prob):.4f}")


def _evaluate_reg(model, X, y_log, y_orig) -> None:
    y_pred = np.expm1(model.predict(X))
    print(f"  MAE      : {mean_absolute_error(y_orig, y_pred):.4f} meses")
    print(f"  RMSE     : {mean_squared_error(y_orig, y_pred) ** 0.5:.4f} meses")
    print(f"  R²       : {r2_score(y_orig, y_pred):.4f}")


def train() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)

    df = load_dataset(DATA_PATH)

    fe = create_pair_features(df)
    fe["compatible"] = df["compatible"].values
    fe["relationship_longevity_months"] = df["relationship_longevity_months"].values
    
    idx_train, idx_temp = train_test_split(
        fe.index, test_size=2 * TEST_SIZE, random_state=RANDOM_STATE, stratify=fe["compatible"]
    )
    idx_test = train_test_split(
        idx_temp, test_size=0.5, random_state=RANDOM_STATE,
        stratify=fe.loc[idx_temp, "compatible"]
    )[1]

    print(f"[training] Split → Train: {len(idx_train)} | Test: {len(idx_test)}")

    X_clf, y_clf = get_clf_features(fe), fe["compatible"]
    X_reg = get_reg_features(fe)
    y_reg_log = np.log1p(fe["relationship_longevity_months"])
    y_reg_orig = fe["relationship_longevity_months"]

    clf_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            C=1.0, class_weight="balanced", solver="lbfgs",
            max_iter=2000, random_state=RANDOM_STATE,
        )),
    ])
    clf_pipeline.fit(X_clf.loc[idx_train], y_clf.loc[idx_train])
    print("\n[training] Métricas clasificación (test):")
    _evaluate_clf(clf_pipeline, X_clf.loc[idx_test], y_clf.loc[idx_test])

    reg_model = Ridge(alpha=1.0)
    reg_model.fit(X_reg.loc[idx_train], y_reg_log.loc[idx_train])
    print("\n[training] Métricas regresión (test):")
    _evaluate_reg(reg_model, X_reg.loc[idx_test], y_reg_log.loc[idx_test], y_reg_orig.loc[idx_test])

    clf_path = os.path.join(MODELS_DIR, "clf_model.pkl")
    reg_path = os.path.join(MODELS_DIR, "reg_model.pkl")
    joblib.dump(clf_pipeline, clf_path)
    joblib.dump(reg_model, reg_path)
    print(f"\n[training] Modelos guardados en {clf_path}  y  {reg_path}")


if __name__ == "__main__":
    train()
