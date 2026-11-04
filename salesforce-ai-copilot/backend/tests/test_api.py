from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services import data_source

H = {"X-API-Key": "dev-key"}


def _some_id():
    return str(data_source.list_opportunities().opportunity_id.iloc[0])


def test_auth_required():
    with TestClient(app) as c:
        assert c.get("/v1/dashboard").status_code == 401


def test_insights_flow():
    with TestClient(app) as c:
        r = c.post(f"/v1/opportunities/{_some_id()}/insights", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert 0 <= body["prediction"]["loss_risk"] <= 1
        assert len(body["prediction"]["factors"]) == 5
        assert body["recommendations"]


def test_enrichment_of_external_opportunity():
    """Une opportunité venant de Salesforce (champs partiels) est complétée puis scorée."""
    with TestClient(app) as c:
        opp = {"opportunity_id": "SF-1", "product": "GTX Pro", "sector": "retail", "sales_price": 4821}
        r = c.post("/v1/opportunities/SF-1/predict", headers=H, json={"opportunity": opp})
        assert r.status_code == 200 and 0 <= r.json()["loss_risk"] <= 1


def test_dashboard_and_chat():
    with TestClient(app) as c:
        d = c.get("/v1/dashboard", headers=H).json()
        assert d["total"] > 0 and len(d["top_priority"]) == 10
        a = c.post("/v1/chat", headers=H, json={"question": "Quelles opportunités ont le plus de risque de perte ?"}).json()
        assert a["data"]
        a = c.post("/v1/chat", headers=H, json={"question": "Quelles sont les principales raisons des échecs ?"}).json()
        assert "Taux de perte" in a["answer"]


def test_unknown_opportunity():
    with TestClient(app) as c:
        assert c.post("/v1/opportunities/NOPE/predict", headers=H).status_code == 404


def test_decision_logged():
    with TestClient(app) as c:
        r = c.post("/v1/decisions", headers=H, json={"opportunity_id": _some_id(), "recommendation_id": "x", "decision": "acceptée"})
        assert r.status_code == 200
