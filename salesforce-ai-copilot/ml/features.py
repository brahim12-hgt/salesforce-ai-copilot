"""Features du modèle, adaptées au dataset « CRM Sales Opportunities » (Maven Analytics / Kaggle).

Principe anti-fuite : seules des informations connues AU MOMENT où l'affaire est engagée sont utilisées
(pas de close_value, pas de durée de l'affaire, pas de close_date).
"""
import numpy as np
import pandas as pd

NUMERIC = [
    "sales_price", "revenue", "employees", "company_age", "engage_month",
    "account_prior_deals", "account_prior_win_rate", "agent_prior_deals", "agent_prior_win_rate",
]
BINARY = ["is_subsidiary"]
CATEGORICAL = ["product", "series", "sector", "office_location", "sales_agent", "manager", "regional_office"]
FEATURES = NUMERIC + BINARY + CATEGORICAL

LABELS_FR = {
    "sales_price": "Prix catalogue du produit",
    "revenue": "Chiffre d'affaires du client (M$)",
    "employees": "Effectif du client",
    "company_age": "Ancienneté du client (ans)",
    "engage_month": "Mois d'engagement",
    "account_prior_deals": "Affaires passées avec ce client",
    "account_prior_win_rate": "Taux de succès passé avec ce client",
    "agent_prior_deals": "Affaires passées du commercial",
    "agent_prior_win_rate": "Taux de succès passé du commercial",
    "is_subsidiary": "Client filiale d'un groupe",
    "product": "Produit",
    "series": "Gamme",
    "sector": "Secteur du client",
    "office_location": "Pays du client",
    "sales_agent": "Commercial",
    "manager": "Manager",
    "regional_office": "Bureau régional",
}

PERCENT = {"account_prior_win_rate", "agent_prior_win_rate"}


def prepare(df: pd.DataFrame, defaults: dict | None = None) -> pd.DataFrame:
    """Nettoyage + typage, identique à l'entraînement et à l'inférence."""
    out = df.copy()
    for c in FEATURES:
        if c not in out.columns:
            out[c] = np.nan
    for c in NUMERIC:
        out[c] = pd.to_numeric(out[c], errors="coerce")
        if defaults and c in defaults:
            fill = defaults[c]
        else:
            fill = out[c].median() if out[c].notna().any() else 0
        out[c] = out[c].fillna(fill)
    for c in BINARY:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    for c in CATEGORICAL:
        out[c] = out[c].fillna("Inconnu").astype(str)
    return out[FEATURES]
