import hmac
from fastapi import Header, HTTPException, status
from .config import settings


def require_api_key(x_api_key: str = Header(default="")):
    """Authentification serveur-à-serveur (Named Credential Salesforce -> header X-API-Key)."""
    if not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Clé API invalide")
