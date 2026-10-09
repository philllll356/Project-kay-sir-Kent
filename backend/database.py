import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./qrevent.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine_options = {"connect_args": connect_args, "pool_pre_ping": True}
if not DATABASE_URL.startswith("sqlite"):
    engine_options.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    })
engine = create_engine(DATABASE_URL, **engine_options)
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

    # New PostgreSQL tables are created by explicit schema migrations so the
    # restricted runtime role does not need DDL privileges.
    app_tables = [table for table in Base.metadata.tables.values() if table.name != "account_device_tokens"]
    Base.metadata.create_all(bind=engine, tables=app_tables)

    # Add attendee QR tokens to legacy SQLite databases. PostgreSQL schemas
    # are created and changed through a real migration process; the runtime
    # application role must not need table ownership or DDL privileges.
    if DATABASE_URL.startswith("sqlite") and "attendees" in inspect(engine).get_table_names():
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

        if "account_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE attendees ADD COLUMN account_id INTEGER"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_attendees_account_id ON attendees (account_id)"))

    if DATABASE_URL.startswith("sqlite") and "coordinators" in inspect(engine).get_table_names():
        columns = {column["name"] for column in inspect(engine).get_columns("coordinators")}
        if "google_sub" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE coordinators ADD COLUMN google_sub VARCHAR(255)"))
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_coordinators_google_sub ON coordinators (google_sub)"))
        if "role" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE coordinators ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'host'"))
        if "is_active" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE coordinators ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))

    if DATABASE_URL.startswith("sqlite") and "attendee_accounts" in inspect(engine).get_table_names():
        columns = {column["name"] for column in inspect(engine).get_columns("attendee_accounts")}
        if "google_sub" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE attendee_accounts ADD COLUMN google_sub VARCHAR(255)"))
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_attendee_accounts_google_sub ON attendee_accounts (google_sub)"))
        if "is_active" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE attendee_accounts ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
