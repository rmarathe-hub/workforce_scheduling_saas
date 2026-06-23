from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "https://workforce-scheduling-saas.vercel.app",
)
VERCEL_PREVIEW_ORIGIN_REGEX = r"https://.*\.vercel\.app"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Workforce Scheduling SaaS"
    environment: str = "development"
    database_url: str
    jwt_secret_key: str = "replace-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    frontend_url: str = "http://localhost:5173"
    max_weekly_hours: float = 40
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = ""

    @property
    def cors_allowed_origins(self) -> list[str]:
        origins = list(DEFAULT_CORS_ORIGINS)
        if self.frontend_url not in origins:
            origins.append(self.frontend_url)
        return origins


settings = Settings()
