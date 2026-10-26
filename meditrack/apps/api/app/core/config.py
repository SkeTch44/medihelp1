from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str = "sqlite:///./meditrack.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-only-change-this-secret"
    jwt_access_token_minutes: int = 30
    cors_origins: str = "http://localhost:3000"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_api_version: str = "v23.0"
    call_provider: str = "stub"
    call_provider_api_key: str = ""
    call_provider_from_number: str = ""
    prescription_upload_dir: str = "./private_uploads"
    prescription_max_upload_mb: int = 10
    prescription_ai_enabled: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

settings = Settings()
