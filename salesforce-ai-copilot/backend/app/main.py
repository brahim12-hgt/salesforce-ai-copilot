from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .schemas import (ChatRequest, ChatResponse, DecisionRequest, InsightRequest,
                      InsightResponse, Prediction, Summary)
from .security import require_api_key
from .services import chat_service, data_source, llm_service, ml_service, rag_service
from .services.recommender import recommend


@asynccontextmanager
async def lifespan(_: FastAPI):
    rag_service.index.build(list(data_source.list_opportunities().opportunity_id.head(100)))  # vide sans interactions
    yield


app = FastAPI(title="Salesforce AI Copilot", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins.split(","),
                   allow_methods=["GET", "POST"], allow_headers=["*"])
auth = [Depends(require_api_key)]


@app.get("/health")
def health():
    return {"status": "ok", "llm": bool(settings.anthropic_api_key), "synthetic": settings.use_synthetic_data}


def _resolve(opp_id: str, body: InsightRequest | None) -> dict:
    opp = (body.opportunity if body and body.opportunity else None) or data_source.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(404, "Opportunité introuvable")
    opp.setdefault("opportunity_id", opp_id)
    return opp


@app.post("/v1/opportunities/{opp_id}/predict", response_model=Prediction, dependencies=auth)
def predict(opp_id: str, body: InsightRequest | None = None):
    pred = ml_service.predict_one(_resolve(opp_id, body))
    data_source.log_audit({"event": "prediction", "opportunity_id": opp_id, "loss_risk": pred.loss_risk})
    return pred


@app.post("/v1/opportunities/{opp_id}/summary", response_model=Summary, dependencies=auth)
def summary(opp_id: str, body: InsightRequest | None = None):
    inter = body.interactions if body and body.interactions else data_source.get_interactions(opp_id)
    inter = [i if hasattr(i, "text") else llm_service.Interaction(**i) for i in inter]
    return llm_service.summarize(inter)


@app.post("/v1/opportunities/{opp_id}/insights", response_model=InsightResponse, dependencies=auth)
def insights(opp_id: str, body: InsightRequest | None = None):
    """Flux complet: ML -> SHAP -> LLM -> Next Best Action."""
    opp = _resolve(opp_id, body)
    pred = ml_service.predict_one(opp)
    raw = body.interactions if body and body.interactions else data_source.get_interactions(opp_id)
    inter = [i if hasattr(i, "text") else llm_service.Interaction(**i) for i in raw]
    summ = llm_service.summarize(inter)
    recs = recommend(pred, summ)
    data_source.log_audit({"event": "insights", "opportunity_id": opp_id, "loss_risk": pred.loss_risk,
                           "recommendations": [r.id for r in recs]})
    return InsightResponse(prediction=pred, summary=summ, recommendations=recs)


@app.get("/v1/dashboard", dependencies=auth)
def dashboard():
    df = data_source.list_opportunities()
    df["win_probability"] = ml_service.predict_frame(df)
    df["loss_risk"] = 1 - df["win_probability"]
    df["risk_level"] = df.loss_risk.apply(ml_service.risk_level)
    top = df.sort_values("loss_risk", ascending=False).head(10)
    bins = [0, .2, .4, .6, .8, 1.0]
    dist = (df.win_probability.groupby(__import__("pandas").cut(df.win_probability, bins), observed=False)
            .count().reset_index(drop=True).tolist())
    return {
        "total": int(len(df)),
        "estimated_conversion_rate": round(float(df.win_probability.mean()), 4),
        "risk_counts": df.risk_level.value_counts().reindex(["élevé", "moyen", "faible"], fill_value=0).to_dict(),
        "distribution": {"bins": ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"], "counts": dist},
        "top_priority": [{"id": r.opportunity_id, "name": r["name"], "account": r.account_name,
                          "amount": float(r.amount), "loss_risk": round(float(r.loss_risk), 3),
                          "risk_level": r.risk_level} for _, r in top.iterrows()],
    }


@app.post("/v1/chat", response_model=ChatResponse, dependencies=auth)
def chat(req: ChatRequest):
    data_source.log_audit({"event": "chat", "user_id": req.user_id, "question_len": len(req.question)})
    return chat_service.answer(req.question, req.user_id)


@app.post("/v1/decisions", dependencies=auth)
def decision(req: DecisionRequest):
    """Validation humaine: trace l'acceptation / modification / rejet (base du suivi de dérive)."""
    data_source.log_audit({"event": "decision", **req.model_dump()})
    return {"status": "enregistré"}


@app.get("/v1/model/metrics", dependencies=auth)
def metrics():
    import json
    return json.loads((settings.model_path.parent / "metrics.json").read_text())
