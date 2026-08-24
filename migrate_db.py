"""Apply local schema updates for the vulnerable-lab branch."""

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    db.create_all()

    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "display_name" not in columns:
        db.session.execute(
            text("ALTER TABLE users ADD COLUMN display_name VARCHAR(200)")
        )
        db.session.commit()
        print("Added users.display_name column.")
    else:
        print("users.display_name already exists.")

    print("Database migration complete.")
