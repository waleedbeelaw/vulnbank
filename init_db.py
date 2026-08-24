"""Create database tables for local development."""

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    db.create_all()
    print("Database tables created.")
