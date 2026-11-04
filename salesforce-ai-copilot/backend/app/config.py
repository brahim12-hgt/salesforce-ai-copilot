from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")
    api_key: str = "dev-key"
    allowed_origins: str = "*"
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    use_synthetic_data: bool = True
    sf_username: str = ""
    sf_password: str = ""
    sf_security_token: str = ""
    sf_domain: str = "login"
    model_path: Path = ROOT / "models" / "model.joblib"
    background_path: Path = ROOT / "models" / "background.csv"
    data_path: Path = ROOT / "data" / "opportunities.csv"
    open_data_path: Path = ROOT / "data" / "open_opportunities.csv"
    lookups_path: Path = ROOT / "data" / "lookups.json"
    defaults_path: Path = ROOT / "data" / "defaults.json"
    audit_log: Path = ROOT / "data" / "audit_log.jsonl"


settings = Settings()
