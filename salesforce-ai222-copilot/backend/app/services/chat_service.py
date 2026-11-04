"""Assistant conversationnel : routage d'intention + réponses ancrées dans les données autorisées."""
import re
import pandas as pd
from . import data_source, ml_service, rag_service
from ..schemas import ChatResponse


def _scored_open() -> pd.DataFrame:
    df = data_source.list_opportunities()
    df["loss_risk"] = 1 - ml_service.predict_frame(df)
    return df


def _find_id(question: str) -> str | None:
    ids = set(data_source.open_opportunities().opportunity_id.astype(str)) | set(
        data_source.closed_opportunities().opportunity_id.astype(str))
    for tok in re.findall(r"[A-Za-z0-9]{6,}", question):
        if tok.upper() in ids:
            return tok.upper()
        if tok in ids:
            return tok
    return None


def _worst(df: pd.DataFrame, col: str, min_n: int = 50):
    g = df.groupby(col).won.agg(["count", "mean"])
    g = g[g["count"] >= min_n].sort_values("mean")
    return None if g.empty else (g.index[0], 1 - g.iloc[0]["mean"], int(g.iloc[0]["count"]))


def answer(question: str, user_id: str | None = None) -> ChatResponse:
    q = question.lower()
    opp_id = _find_id(question)

    if opp_id and any(k in q for k in ["action", "améliorer", "faire", "recommand"]):
        from .recommender import recommend
        opp = data_source.get_opportunity(opp_id)
        recs = recommend(ml_service.predict_one(opp), None)
        return ChatResponse(answer=f"Actions recommandées pour {opp_id} :\n" + "\n".join(
            f"- [{r.priority}] {r.action} — {r.justification}" for r in recs), references=[r.id for r in recs])

    if opp_id and any(k in q for k in ["résume", "resume", "interaction", "dernier", "échange"]):
        return ChatResponse(answer=f"Aucune interaction (e-mail, appel, note) n'est disponible pour {opp_id} dans ce jeu de données. "
                                   "Avec Salesforce connecté, elles proviennent des activités de l'opportunité.", references=[opp_id])

    if any(k in q for k in ["risque", "perte", "perdre"]):
        top = _scored_open().sort_values("loss_risk", ascending=False).head(5)
        rows = [{"id": r.opportunity_id, "nom": r["name"], "client": r.account_name,
                 "prix": float(r.amount), "risque_perte": round(float(r.loss_risk), 3)} for _, r in top.iterrows()]
        return ChatResponse(answer="Opportunités ouvertes au risque de perte le plus élevé :\n" + "\n".join(
            f"- {r['id']} ({r['nom']}) : {r['risque_perte']:.0%}" for r in rows), data=rows, references=[r["id"] for r in rows])

    if any(k in q for k in ["montant", "plus gros", "valeur"]):
        df = data_source.list_opportunities().sort_values("amount", ascending=False).head(5)
        rows = [{"id": r.opportunity_id, "nom": r["name"], "prix": float(r.amount)} for _, r in df.iterrows()]
        return ChatResponse(answer="Opportunités ouvertes de plus forte valeur (prix catalogue) :\n" + "\n".join(
            f"- {r['id']} ({r['nom']}) : {r['prix']:,.0f} $".replace(",", " ") for r in rows),
            data=rows, references=[r["id"] for r in rows])

    if any(k in q for k in ["suivi", "urgent", "relancer"]):
        df = data_source.list_opportunities().sort_values("days_open", ascending=False).head(5)
        rows = [{"id": r.opportunity_id, "nom": r["name"], "jours_ouverte": int(r.days_open)} for _, r in df.iterrows()]
        return ChatResponse(answer="Affaires ouvertes depuis le plus longtemps (à relancer) :\n" + "\n".join(
            f"- {r['id']} ({r['nom']}) : {r['jours_ouverte']} jours" for r in rows),
            data=rows, references=[r["id"] for r in rows])

    if any(k in q for k in ["raison", "échec", "echec", "pourquoi"]):
        closed = data_source.closed_opportunities()
        parts = []
        for col, lab in [("product", "produit"), ("sector", "secteur"), ("manager", "manager")]:
            w = _worst(closed, col)
            if w:
                parts.append(f"- Pire {lab} : {w[0]} ({w[1]:.0%} de pertes sur {w[2]} affaires)")
        base = 1 - closed.won.mean()
        return ChatResponse(answer=f"Taux de perte global : {base:.0%}. Segments les plus défavorables :\n" + "\n".join(parts),
                            references=["historique des affaires closes"])

    hits = rag_service.index.search(question, k=3)
    if hits:
        return ChatResponse(answer="Passages pertinents :\n" + "\n".join(f"- ({h['opportunity_id']}) {h['text']}" for h in hits),
                            references=[h["id"] for h in hits])
    return ChatResponse(answer="Je n'ai pas trouvé de réponse. Essayez : « Quelles opportunités ont le plus de risque de perte ? », "
                               "« Quels clients nécessitent un suivi urgent ? » ou « Quelles actions pour l'opportunité <ID> ? ».")
