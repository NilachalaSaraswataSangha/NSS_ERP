"""
NSS ERP — Application configuration.

Reads database connection parameters from environment variables.
Uses python-dotenv for local development (.env file at api/ level).

No sensitive defaults — all DB parameters are required.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the api/ directory if present
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)


class Settings:
    """Application settings sourced from environment variables."""

    DB_NAME: str = os.environ.get("DB_NAME", "")
    DB_USER: str = os.environ.get("DB_USER", "")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_PORT: str = os.environ.get("DB_PORT", "5432")

    # API
    API_PORT: int = int(os.environ.get("API_PORT", "8001"))

    def validate(self) -> None:
        """Raise if required settings are missing."""
        missing = []
        if not self.DB_NAME:
            missing.append("DB_NAME")
        if not self.DB_USER:
            missing.append("DB_USER")
        if not self.DB_PASSWORD:
            missing.append("DB_PASSWORD")
        if missing:
            raise RuntimeError(
                f"Required environment variables not set: {', '.join(missing)}. "
                f"Create api/.env or export them before starting the server."
            )


settings = Settings()
