from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "development"
    API_PORT: int = 8000

    MONGO_URI: str = "mongodb://mongodb:27017"
    MONGO_DATABASE: str = "ticketflow"

    REDIS_URI: str = "redis://redis:6379/0"

    JWT_SECRET: str = "change-me-for-local-development"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    TICKET_HMAC_SECRET: str = "change-ticket-hmac-for-local-development"

    SESSION_TTL_SECONDS: int = 1800
    IDEMPOTENCY_TTL_SECONDS: int = 86400
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
