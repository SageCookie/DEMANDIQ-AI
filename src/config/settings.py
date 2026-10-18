import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'demandiq.db'}")
    model_path: str = os.getenv("MODEL_PATH", str(BASE_DIR / "models" / "production" / "demand_model.joblib"))
    metadata_path: str = os.getenv("METADATA_PATH", str(BASE_DIR / "models" / "production" / "metadata.json"))
    default_forecast_horizon: int = int(os.getenv("DEFAULT_FORECAST_HORIZON", "30"))
    default_service_level: float = float(os.getenv("DEFAULT_SERVICE_LEVEL", "0.95"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    port: int = int(os.getenv("PORT", "8000"))
    host: str = os.getenv("HOST", "0.0.0.0")
    cors_origins: list[str] = [x.strip().rstrip("/") for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173").split(",") if x.strip()]
    secret_key: str = os.getenv("SECRET_KEY", "demandiq_ai_default_secret_key_2026")
    base_dir: Path = BASE_DIR

settings = Settings()
