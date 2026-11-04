"""Entraîne et compare 4 modèles, calibre et sauvegarde le meilleur."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, brier_score_loss, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from features import BINARY, CATEGORICAL, FEATURES, NUMERIC, prepare

ROOT = Path(__file__).resolve().parents[1]


def build_preprocessor():
    return ColumnTransformer([
        ("num", StandardScaler(), NUMERIC + BINARY),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
    ])


def candidates():
    return {
        "logistic_regression": LogisticRegression(max_iter=2000),
        "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=42, n_jobs=-1),
        "gradient_boosting": GradientBoostingClassifier(random_state=42),
        "xgboost": XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.9,
                                 colsample_bytree=0.9, eval_metric="logloss", random_state=42),
    }


def metrics(y, proba):
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": accuracy_score(y, pred), "precision": precision_score(y, pred),
        "recall": recall_score(y, pred), "f1": f1_score(y, pred),
        "roc_auc": roc_auc_score(y, proba), "brier": brier_score_loss(y, proba),
    }


def main():
    df = pd.read_csv(ROOT / "data" / "opportunities.csv", parse_dates=["engage_date"]).sort_values("engage_date")
    n = len(df)
    i1, i2 = int(n * 0.70), int(n * 0.85)  # découpage CHRONOLOGIQUE : on prédit le futur à partir du passé
    defaults = df.iloc[:i1][NUMERIC].median().to_dict()
    X, y = prepare(df, defaults), df["won"].values
    X_tr, y_tr = X.iloc[:i1], y[:i1]
    X_val, y_val = X.iloc[i1:i2], y[i1:i2]
    X_te, y_te = X.iloc[i2:], y[i2:]

    results, fitted = {}, {}
    for name, clf in candidates().items():
        pipe = Pipeline([("prep", build_preprocessor()), ("clf", clf)]).fit(X_tr, y_tr)
        results[name] = metrics(y_val, pipe.predict_proba(X_val)[:, 1])
        fitted[name] = pipe
        print(f"{name:22s} AUC={results[name]['roc_auc']:.3f} F1={results[name]['f1']:.3f}")

    best = max(results, key=lambda k: results[k]["roc_auc"])
    # Calibration des probabilités (isotonic) sur l'ensemble de validation
    try:  # scikit-learn >= 1.6
        from sklearn.frozen import FrozenEstimator
        cal = CalibratedClassifierCV(FrozenEstimator(fitted[best]), method="isotonic").fit(X_val, y_val)
    except ImportError:  # scikit-learn < 1.6
        cal = CalibratedClassifierCV(fitted[best], method="isotonic", cv="prefit").fit(X_val, y_val)
    test_proba = cal.predict_proba(X_te)[:, 1]
    final = metrics(y_te, test_proba)
    frac_pos, mean_pred = calibration_curve(y_te, test_proba, n_bins=10)
    print(f"\nMeilleur: {best} | Test -> " + ", ".join(f"{k}={v:.3f}" for k, v in final.items()))

    (ROOT / "models").mkdir(exist_ok=True)
    joblib.dump({"calibrated": cal, "base": fitted[best], "features": FEATURES, "name": best},
                ROOT / "models" / "model.joblib")
    # Fond de référence pour SHAP
    X_tr.sample(200, random_state=1).to_csv(ROOT / "models" / "background.csv", index=False)
    val_loss = 1 - cal.predict_proba(X_val)[:, 1]
    thresholds = {"moyen": float(np.quantile(val_loss, 0.5)), "élevé": float(np.quantile(val_loss, 0.8))}
    (ROOT / "data" / "defaults.json").write_text(json.dumps(defaults))
    report = {"risk_thresholds": thresholds, "baseline_win_rate_test": float(y_te.mean()),
              "split": {"train": i1, "validation": i2 - i1, "test": n - i2}, "validation": results, "best_model": best, "test": final,
              "calibration": {"observed": frac_pos.tolist(), "predicted": mean_pred.tolist()}}
    (ROOT / "models" / "metrics.json").write_text(json.dumps(report, indent=2))
    print("Modèle sauvegardé dans models/")


if __name__ == "__main__":
    main()
