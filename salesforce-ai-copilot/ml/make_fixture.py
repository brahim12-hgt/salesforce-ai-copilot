"""Génère de FAUX fichiers au format Maven (accounts/products/sales_pipeline/sales_teams).

Sert uniquement à tester le code sans télécharger le vrai dataset.
Les vrais fichiers se placent dans data/raw/ (voir README).
"""
from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
OUT = Path(__file__).resolve().parents[1] / "data" / "raw_sample"
OUT.mkdir(parents=True, exist_ok=True)

sectors = ["retail", "technology", "medical", "software", "finance", "telecommunications", "marketing", "entertainment"]
accounts = pd.DataFrame({
    "account": [f"Account {i}" for i in range(85)],
    "sector": rng.choice(sectors, 85),
    "year_established": rng.integers(1979, 2017, 85),
    "revenue": rng.gamma(2, 600, 85).round(2),
    "employees": rng.integers(100, 30000, 85),
    "office_location": rng.choice(["United States", "Kenya", "Korea", "Norway", "Japan", "Panama"], 85, p=[.7, .06, .06, .06, .06, .06]),
    "subsidiary_of": [None if rng.random() < .8 else f"Account {rng.integers(0, 85)}" for _ in range(85)],
})
products = pd.DataFrame({
    "product": ["GTX Basic", "GTX Pro", "MG Special", "MG Advanced", "GTX Plus Basic", "GTX Plus Pro", "GTK 500"],
    "series": ["GTX", "GTX", "MG", "MG", "GTX", "GTX", "GTK"],
    "sales_price": [550, 4821, 55, 3393, 1096, 5482, 26768],
})
teams = pd.DataFrame({
    "sales_agent": [f"Agent {i}" for i in range(30)],
    "manager": [f"Manager {i // 6}" for i in range(30)],
    "regional_office": [["Central", "East", "West"][i // 10] for i in range(30)],
})
n = 8800
pipe = pd.DataFrame({"opportunity_id": [f"{i:08X}" for i in range(n)]})
pipe["sales_agent"] = rng.choice(teams.sales_agent, n)
pipe["product"] = rng.choice(["GTX Basic", "GTXPro", "MG Special", "MG Advanced", "GTX Plus Basic", "GTX Plus Pro", "GTK 500"], n)
pipe["account"] = rng.choice(accounts.account, n)
stage = rng.choice(["Won", "Lost", "Engaging", "Prospecting"], n, p=[.48, .28, .18, .06])
skill = dict(zip(teams.sales_agent, rng.normal(0, .5, 30)))
logit = pd.Series(pipe.sales_agent.map(skill)).values + rng.normal(0, 1, n)
closed_mask = np.isin(stage, ["Won", "Lost"])
stage = np.where(closed_mask, np.where(logit + 0.55 > 0, "Won", "Lost"), stage)
pipe["deal_stage"] = stage
eng = pd.Timestamp("2016-10-01") + pd.to_timedelta(rng.integers(0, 450, n), unit="D")
pipe["engage_date"] = eng
pipe["close_date"] = eng + pd.to_timedelta(rng.integers(1, 138, n), unit="D")
pipe.loc[pipe.deal_stage == "Prospecting", "engage_date"] = pd.NaT
pipe.loc[pipe.deal_stage.isin(["Engaging", "Prospecting"]), "close_date"] = pd.NaT
price = pipe["product"].str.replace(" ", "").map({p.replace(" ", ""): s for p, s in zip(products["product"], products.sales_price)})
pipe["close_value"] = np.where(pipe.deal_stage == "Won", price, 0)
for name, d in [("accounts", accounts), ("products", products), ("sales_teams", teams), ("sales_pipeline", pipe)]:
    d.to_csv(OUT / f"{name}.csv", index=False)
print("Fixture écrite dans", OUT, "(FAUSSES données, test uniquement)")
