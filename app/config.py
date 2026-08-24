import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_SECONDS = 3600
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    @staticmethod
    def validate():
        if not Config.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError(
                "DATABASE_URL environment variable is required. "
                "Copy .env.example to .env and set your PostgreSQL connection string."
            )
        if not Config.JWT_SECRET_KEY:
            raise RuntimeError(
                "JWT_SECRET_KEY environment variable is required. "
                "Copy .env.example to .env and set a strong secret key."
            )
