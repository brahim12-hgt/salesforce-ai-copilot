"""Prédiction + explications SHAP."""
import json
import re
import sys
from datetime import datetime
from functools import lru_cache
import joblib
import numpy as np
import pandas as pd
import shap

from ..config import ROOT, settings
from ..schemas import Factor, Prediction
from . import data_source

sys.path.insert(0, str(ROOT / "ml"))
from features import BINARY, CATEGORICAL, FEATURES, LABELS_FR, PERCENT, prepare  # noqa: E402


@lru_cache(maxsize=1)
def _bundle():
    return joblib.load(settings.model_path)


@lru_cache(maxsize=1)
def _defaults():
    return json.loads(settings.defaults_path.read_text()) if settings.defaults_path.exists() else None


@lru_cache(maxsize=1)
def _thresholds():
    p = settings.model_path.parent / "metrics.json"
    t = json.loads(p.read_text()).get("risk_thresholds") if p.exists() else None
    return t or {"moyen": 0.4, "élevé": 0.6}


@lru_cache(maxsize=1)
def _explainer():
    base = _bundle()["base"]
    prep, clf = base.named_steps["prep"], base.named_steps["clf"]
    bg = prep.transform(prepare(pd.read_csv(settings.background_path)[FEATURES], _defaults()))
    if clf.__class__.__name__ == "LogisticRegression":
        return shap.LinearExplainer(clf, bg)
    return shap.TreeExplainer(clf, bg)


def _missing(v) -> bool:
    return v is None or (isinstance(v, float) and np.isnan(v)) or v == ""


def enrich(opp: dict) -> dict:
    """Complète les champs manquants depuis les référentiels (comptes, produits, commerciaux)."""
    L, o = data_source.lookups(), dict(opp)

    def fill(src: dict | None):
        for k, v in (src or {}).items():
            if _missing(o.get(k)):
                o[k] = v

    fill(L.get("accounts", {}).get(o.get("account") or o.get("account_name")))
    fill(L.get("products", {}).get(re.sub(r"[^a-z0-9]", "", str(o.get("product", "")).lower())))
    fill(L.get("agents", {}).get(o.get("sales_agent")))
    if _missing(o.get("sales_price")) and not _missing(o.get("amount")):
        o["sales_price"] = o["amount"]
    if _missing(o.get("company_age")) and not _missing(o.get("year_established")):
        o["company_age"] = datetime.now().year - float(o["year_established"])
    if _missing(o.get("engage_month")):
        o["engage_month"] = datetime.now().month
    return o


def risk_level(loss: float) -> str:
    t = _thresholds()
    return "élevé" if loss >= t["élevé"] else "moyen" if loss >= t["moyen"] else "faible"


def _priority(loss: float, amount: float, level: str) -> int:
    score = loss * 0.7 + min(amount / 5000, 1) * 0.3
    return 1 if level == "élevé" and score > 0.55 else 2 if level == "élevé" else 3 if level == "moyen" else 4 if score > 0.3 else 5


def _fmt(feature: str, v) -> str:
    if feature in BINARY:
        return "oui" if int(v) else "non"
    if feature in CATEGORICAL:
        return str(v)
    if feature in PERCENT:
        return f"{float(v):.0%}"
    if feature == "sales_price":
        return f"{float(v):,.0f} $".replace(",", " ")
    return f"{float(v):.0f}"


def predict_frame(df: pd.DataFrame) -> np.ndarray:
    return np.clip(_bundle()["calibrated"].predict_proba(prepare(df, _defaults()))[:, 1], 0.02, 0.98)


def predict_one(opp: dict, top_k: int = 5) -> Prediction:
    X = prepare(pd.DataFrame([enrich(opp)]), _defaults())
    win = float(np.clip(_bundle()["calibrated"].predict_proba(X)[0, 1], 0.02, 0.98))
    loss = 1 - win

    prep = _bundle()["base"].named_steps["prep"]
    sv = _explainer().shap_values(prep.transform(X))
    sv = np.asarray(sv[1] if isinstance(sv, list) else sv).reshape(-1)

    agg: dict[str, float] = {}
    for n, v in zip(prep.get_feature_names_out(), sv):
        raw = n.split("__", 1)[1]
        feat = next((c for c in CATEGORICAL if raw.startswith(c + "_")), raw)
        agg[feat] = agg.get(feat, 0.0) + float(v)

    factors = []
    for feat, val in sorted(agg.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_k]:
        risk_impact = -val  # SHAP porte sur P(gain) : on inverse pour parler de risque
        factors.append(Factor(
            feature=feat, label=LABELS_FR[feat], value=_fmt(feat, X.iloc[0][feat]), impact=round(risk_impact, 4),
            direction="augmente_risque" if risk_impact > 0 else "reduit_risque"))
    level = risk_level(loss)
    return Prediction(
        opportunity_id=str(opp.get("opportunity_id", "")), win_probability=round(win, 4), loss_risk=round(loss, 4),
        risk_level=level, priority=_priority(loss, float(X.iloc[0]["sales_price"]), level), factors=factors)
