import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./qrevent.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Enable foreign key enforcement for SQLite (disabled by default)
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from backend.models import db_models  # noqa: F401
    from backend.services.qr_service import generate_qr_token

    Base.metadata.create_all(bind=engine)

    # Add attendee QR tokens to databases created before personal QR support.
    # SQLite cannot add a NOT NULL column safely to an existing table, so the
    # model keeps this column nullable for backwards-compatible migrations.
    if "attendees" in inspect(engine).get_table_names():
        columns = {column["name"] for column in inspect(engine).get_columns("attendees")}
        if "qr_token" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE attendees ADD COLUMN qr_token VARCHAR(64)"))

        with engine.begin() as connection:
            attendee_ids = connection.execute(
                text("SELECT id FROM attendees WHERE qr_token IS NULL")
            ).scalars().all()
            for attendee_id in attendee_ids:
                connection.execute(
                    text("UPDATE attendees SET qr_token = :qr_token WHERE id = :attendee_id"),
                    {"qr_token": generate_qr_token(), "attendee_id": attendee_id},
                )
            connection.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_attendees_qr_token ON attendees (qr_token)")
            )
