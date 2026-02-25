from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@postgres:5432/mezbon_clinic"
    DATABASE_URL_SYNC: str = "postgresql://user:pass@postgres:5432/mezbon_clinic"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Auth
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # Encryption
    ENCRYPTION_KEY: str

    # AI — Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # AI — Muxlisa STT/TTS
    MUXLISA_API_URL: str = "https://service.muxlisa.uz/api/v2"
    MUXLISA_API_KEY: str = ""
    MUXLISA_MOCK: bool = True

    # Face AI
    INSIGHTFACE_MODEL: str = "buffalo_l"
    INSIGHTFACE_DEVICE: str = "cpu"

    # Payments
    UZCARD_MERCHANT_ID: str = ""
    HUMO_MERCHANT_ID: str = ""
    CLICK_SERVICE_ID: str = ""
    PAYME_MERCHANT_ID: str = ""
    PAYMENT_MOCK: bool = True

    # CRM
    BITRIX24_WEBHOOK_URL: str = ""
    AMOCRM_API_KEY: str = ""

    # Storage — MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "mezbon-clinic"

    # Printer
    PRINTER_TYPE: str = "file"
    PRINTER_OUTPUT_DIR: str = "/tmp/receipts"
    PRINTER_HOST: str = "192.168.1.100"
    PRINTER_PORT: int = 9100
    PRINTER_VENDOR_ID: str = "0x04b8"
    PRINTER_PRODUCT_ID: str = "0x0e15"
    RECEIPT_LOGO_PATH: str = ""

    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"
    LOG_LEVEL: str = "DEBUG"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()  # type: ignore[call-arg]
