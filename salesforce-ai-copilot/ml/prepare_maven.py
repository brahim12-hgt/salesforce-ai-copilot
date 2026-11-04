"""Construit les tables d'entraînement / de scoring à partir des 4 CSV du dataset CRM Sales Opportunities.

Usage : python prepare_maven.py --raw ../data/raw
Produit : data/opportunities.csv (affaires closes, cible `won`), data/open_opportunities.csv (à scorer),
          data/lookups.json (référentiels pour enrichir de nouvelles affaires).
"""
import argparse
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "sales_pipeline": ["opportunity_id", "sales_agent", "product", "account", "deal_stage", "engage_date", "close_date"],
    "accounts": ["account", "sector", "year_established", "revenue", "employees", "office_location", "subsidiary_of"],
    "products": ["product", "series", "sales_price"],
    "sales_teams": ["sales_agent", "manager", "regional_office"],
}
K = 10  # lissage bayésien des taux de succès


def read(raw: Path, name: str) -> pd.DataFrame:
    path = raw / f"{name}.csv"
    if not path.exists():
        raise SystemExit(f"Fichier manquant : {path}. Attendus : {', '.join(f + '.csv' for f in REQUIRED)}")
    df = pd.read_csv(path)
    df.columns = [re.sub(r"\s+", "_", c.strip().lower()) for c in df.columns]
    missing = [c for c in REQUIRED[name] if c not in df.columns]
    if missing:
        raise SystemExit(f"{name}.csv : colonnes absentes {missing}. Colonnes trouvées : {list(df.columns)}")
    return df


def key(s):  # « GTX Pro » et « GTXPro » doivent correspondre
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def prior_stats(closed: pd.DataFrame, group: str, query: pd.DataFrame, qdate: pd.Series, base: float):
    """Pour chaque ligne de `query`: nb d'affaires closes AVANT qdate pour le même groupe et taux de succès lissé."""
    n_out = np.zeros(len(query))
    w_out = np.zeros(len(query))
    qd = qdate.values.astype("datetime64[ns]")
    for g, rows in closed.dropna(subset=["close_date"]).groupby(group):
        rows = rows.sort_values("close_date")
        dates = rows.close_date.values.astype("datetime64[ns]")
        cum = np.cumsum(rows.won.values)
        mask = (query[group] == g).values
        idx = np.searchsorted(dates, qd[mask], side="left")
        n_out[mask] = idx
        w_out[mask] = np.where(idx > 0, cum[np.maximum(idx - 1, 0)], 0)
    rate = (w_out + K * base) / (n_out + K)
    return n_out, rate


def main(raw: Path):
    pipe, acc, prod, team = (read(raw, n) for n in REQUIRED)
    for c in ["engage_date", "close_date"]:
        pipe[c] = pd.to_datetime(pipe[c], errors="coerce")
    for c in ["account", "sales_agent", "product"]:
        pipe[c] = pipe[c].astype("string").str.strip()
    prod["pkey"] = prod["product"].map(key)
    pipe["pkey"] = pipe["product"].map(key)
    prod = prod.rename(columns={"product": "product_std"})
    df = (pipe.merge(prod[["pkey", "product_std", "series", "sales_price"]], on="pkey", how="left")
              .merge(acc, on="account", how="left").merge(team, on="sales_agent", how="left"))
    df["product"] = df["product_std"].fillna(df["product"])
    df["is_subsidiary"] = df["subsidiary_of"].notna().astype(int)

    ref = pipe["close_date"].max()
    df["qdate"] = df["engage_date"].fillna(ref)
    df["engage_month"] = df["qdate"].dt.month
    df["company_age"] = df["qdate"].dt.year - pd.to_numeric(df["year_established"], errors="coerce")
    df["won"] = (df["deal_stage"] == "Won").astype(int)
    closed_mask = df["deal_stage"].isin(["Won", "Lost"])
    base = float(df.loc[closed_mask, "won"].mean())
    cl = df[closed_mask]
    df["account_prior_deals"], df["account_prior_win_rate"] = prior_stats(cl, "account", df, df["qdate"], base)
    df["agent_prior_deals"], df["agent_prior_win_rate"] = prior_stats(cl, "sales_agent", df, df["qdate"], base)

    df["name"] = df["product"].astype(str) + " — " + df["account"].fillna("Compte inconnu").astype(str)
    df["account_name"] = df["account"].fillna("Compte inconnu")
    df["amount"] = df["sales_price"]
    df["days_open"] = (ref - df["engage_date"]).dt.days.fillna(0).astype(int)

    from features import FEATURES
    meta = ["opportunity_id", "name", "account_name", "account", "amount", "deal_stage", "engage_date"]
    closed = df[closed_mask][meta + FEATURES + ["won"]]
    open_ = df[df["deal_stage"].isin(["Prospecting", "Engaging"])][meta + FEATURES + ["days_open"]]
    out = ROOT / "data"
    closed.to_csv(out / "opportunities.csv", index=False)
    open_.to_csv(out / "open_opportunities.csv", index=False)

    # Référentiels (état le plus récent) pour enrichir de nouvelles affaires
    all_acc = df.groupby("account").agg(prior_deals=("account_prior_deals", "max")).to_dict("index")
    final_acc_rate = cl.groupby("account").won.agg(["sum", "count"])
    final_ag_rate = cl.groupby("sales_agent").won.agg(["sum", "count"])
    lookups = {"base_win_rate": base, "reference_date": str(ref.date()), "accounts": {}, "products": {}, "agents": {}}
    for _, r in acc.iterrows():
        s = final_acc_rate.loc[r.account] if r.account in final_acc_rate.index else None
        n, w = (int(s["count"]), int(s["sum"])) if s is not None else (0, 0)
        lookups["accounts"][str(r.account)] = {
            "sector": r.sector, "revenue": float(r.revenue), "employees": float(r.employees),
            "year_established": float(r.year_established), "office_location": r.office_location,
            "is_subsidiary": int(pd.notna(r.subsidiary_of)), "account_prior_deals": n,
            "account_prior_win_rate": (w + K * base) / (n + K)}
    for _, r in prod.iterrows():
        lookups["products"][key(r.product_std)] = {"product": r.product_std, "series": r.series, "sales_price": float(r.sales_price)}
    for _, r in team.iterrows():
        s = final_ag_rate.loc[r.sales_agent] if r.sales_agent in final_ag_rate.index else None
        n, w = (int(s["count"]), int(s["sum"])) if s is not None else (0, 0)
        lookups["agents"][str(r.sales_agent)] = {"manager": r.manager, "regional_office": r.regional_office,
                                                  "agent_prior_deals": n, "agent_prior_win_rate": (w + K * base) / (n + K)}
    (out / "lookups.json").write_text(json.dumps(lookups, ensure_ascii=False, indent=1, default=str))
    print(f"Affaires closes : {len(closed)} (taux de gain {base:.1%}) | ouvertes : {len(open_)} | date de référence : {ref.date()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT / "data" / "raw"))
    main(Path(ap.parse_args().raw))
