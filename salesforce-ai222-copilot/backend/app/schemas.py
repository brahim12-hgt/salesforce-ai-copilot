from typing import Literal, Optional
from pydantic import BaseModel, Field


class Interaction(BaseModel):
    id: str
    type: Literal["email", "call", "meeting", "note"] = "note"
    date: str
    text: str


class Factor(BaseModel):
    feature: str
    label: str
    value: str
    impact: float = Field(description="Contribution SHAP (>0 = augmente le risque de perte)")
    direction: Literal["augmente_risque", "reduit_risque"]


class Prediction(BaseModel):
    opportunity_id: str
    win_probability: float
    loss_risk: float
    risk_level: Literal["faible", "moyen", "élevé"]
    priority: int = Field(description="1 = très urgent … 5 = faible")
    factors: list[Factor]


class Summary(BaseModel):
    summary: str
    needs: list[str] = []
    objections: list[str] = []
    budget_constraints: list[str] = []
    commitments: list[str] = []
    sources: list[str] = []
    generated_by: str = "règles"


class Recommendation(BaseModel):
    id: str
    action: str
    justification: str
    priority: Literal["haute", "moyenne", "basse"]
    status: Literal["proposée", "acceptée", "modifiée", "rejetée"] = "proposée"


class InsightResponse(BaseModel):
    prediction: Prediction
    summary: Optional[Summary] = None
    recommendations: list[Recommendation]


class InsightRequest(BaseModel):
    opportunity: Optional[dict] = None
    interactions: list[Interaction] = []


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    references: list[str] = []
    data: list[dict] = []


class DecisionRequest(BaseModel):
    opportunity_id: str
    recommendation_id: str
    decision: Literal["acceptée", "modifiée", "rejetée"]
    comment: Optional[str] = None
    modified_action: Optional[str] = None
    user_id: Optional[str] = None
