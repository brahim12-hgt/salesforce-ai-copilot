"""Accès aux données : tables préparées depuis le dataset Maven/Kaggle (ou Salesforce en production)."""
import json
from datetime import datetime, timezone
import pandas as pd
from ..config import settings

_open: pd.DataFrame | None = None
_closed: pd.DataFrame | None = None


def _read(path):
    if not path.exists():
        raise FileNotFoundError(f"{path} introuvable. Lancez d'abord : make prepare && make train (voir README).")
    return pd.read_csv(path)


def open_opportunities() -> pd.DataFrame:
    global _open
    if _open is None:
        _open = _read(settings.open_data_path)
    return _open


def closed_opportunities() -> pd.DataFrame:
    global _closed
    if _closed is None:
        _closed = _read(settings.data_path)
    return _closed


def list_opportunities() -> pd.DataFrame:
    return open_opportunities().copy()


def get_opportunity(opp_id: str) -> dict | None:
    for df in (open_opportunities(), closed_opportunities()):
        row = df[df.opportunity_id == opp_id]
        if not row.empty:
            return row.iloc[0].to_dict()
    return None


def get_interactions(opp_id: str) -> list[dict]:
    """Le dataset Maven ne contient PAS d'interactions (e-mails, appels, notes).
    En production, elles viennent des Task/Event Salesforce (voir CopilotPayloadBuilder.cls)."""
    return []


def lookups() -> dict:
    return json.loads(settings.lookups_path.read_text()) if settings.lookups_path.exists() else {}


def sf_client():
    from simple_salesforce import Salesforce
    return Salesforce(username=settings.sf_username, password=settings.sf_password,
                      security_token=settings.sf_security_token, domain=settings.sf_domain)


def log_audit(event: dict) -> None:
    event["ts"] = datetime.now(timezone.utc).isoformat()
    with open(settings.audit_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
