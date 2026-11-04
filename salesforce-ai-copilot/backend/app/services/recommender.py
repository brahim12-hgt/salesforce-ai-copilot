"""Next Best Action : combine facteurs SHAP (qui augmentent le risque) et analyse des interactions."""
from ..schemas import Prediction, Recommendation, Summary

_RULES = {
    "account_prior_win_rate": ("Revoir la relation avec ce compte", "Taux de succès historique avec ce client : {v}.", "haute"),
    "account_prior_deals": ("Organiser une démonstration et partager des références clients", "Peu d'historique avec ce client ({v} affaire(s) passée(s)).", "moyenne"),
    "agent_prior_win_rate": ("Demander l'appui du manager (coaching / co-pilotage)", "Taux de succès historique du commercial : {v}.", "moyenne"),
    "is_subsidiary": ("Contacter le décideur principal au niveau du groupe", "Le client est une filiale : la décision peut se prendre ailleurs.", "haute"),
    "sales_price": ("Envoyer une proposition commerciale actualisée (prix / packaging)", "Prix catalogue élevé ({v}).", "moyenne"),
    "product": ("Préparer un argumentaire dédié au produit", "Le produit « {v} » pèse sur le risque de perte.", "moyenne"),
    "series": ("Préparer un argumentaire dédié à la gamme", "La gamme « {v} » pèse sur le risque de perte.", "basse"),
    "sector": ("Adapter le discours au secteur du client", "Secteur « {v} » : risque supérieur à la moyenne.", "moyenne"),
    "employees": ("Identifier les décideurs et le budget côté client", "Taille du client ({v} employés) : circuit de décision à clarifier.", "moyenne"),
    "revenue": ("Identifier les décideurs et le budget côté client", "Chiffre d'affaires du client ({v} M$) : budget à valider.", "moyenne"),
}
_ONLY_IF = {"is_subsidiary": lambda v: v == "oui"}


def recommend(pred: Prediction, summary: Summary | None) -> list[Recommendation]:
    recs: list[Recommendation] = []
    seen: set[str] = set()
    for f in pred.factors:
        if f.direction != "augmente_risque" or f.feature not in _RULES:
            continue
        if f.feature in _ONLY_IF and not _ONLY_IF[f.feature](f.value):
            continue
        action, why, prio = _RULES[f.feature]
        if action in seen:
            continue
        seen.add(action)
        recs.append(Recommendation(
            id=f"{pred.opportunity_id}-{f.feature}", action=action,
            justification=why.format(v=f.value) + f" (impact SHAP {f.impact:+.2f})", priority=prio))
    if summary and summary.objections:
        recs.append(Recommendation(
            id=f"{pred.opportunity_id}-objections", action="Préparer une réponse aux objections du client",
            justification="Objection détectée : " + summary.objections[0], priority="moyenne"))
    if not recs:
        recs.append(Recommendation(id=f"{pred.opportunity_id}-maintain", action="Maintenir le rythme de suivi",
                                   justification="Aucun facteur de risque dominant.", priority="basse"))
    order = {"haute": 0, "moyenne": 1, "basse": 2}
    return sorted(recs, key=lambda r: order[r.priority])[:5]
