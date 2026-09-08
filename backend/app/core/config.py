"""Central configuration loaded from environment variables."""
import os


class Settings:
    MONGO_URL: str = os.environ["MONGO_URL"]
    DB_NAME: str = os.environ["DB_NAME"]

    JWT_SECRET: str = os.environ["JWT_SECRET"]
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_MINUTES", "30"))
    REFRESH_TOKEN_DAYS: int = int(os.environ.get("REFRESH_TOKEN_DAYS", "7"))

    PLATFORM_SUPERADMIN_EMAIL: str = os.environ["PLATFORM_SUPERADMIN_EMAIL"]
    PLATFORM_SUPERADMIN_PASSWORD: str = os.environ["PLATFORM_SUPERADMIN_PASSWORD"]

    CORS_ORIGINS: list = [
        o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()
    ]

    API_V1_PREFIX: str = "/api/v1"


settings = Settings()
