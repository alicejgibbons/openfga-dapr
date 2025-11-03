from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Configuration
    app_title: str = "FastAPI OpenFGA Project"
    app_version: str = "1.0.0"
    debug: bool = True

    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./db.sqlite3"

    # OpenFGA Configuration
    openfga_store_id: str = ""
    openfga_authorization_model_id: str = ""
    openfga_api_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
