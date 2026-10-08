"""Copy the current QR Event System SQLite data into PostgreSQL.

The migration is intentionally conservative:
- it creates the PostgreSQL schema from the application's SQLAlchemy models;
- it refuses to copy into a PostgreSQL database that already contains data;
- it preserves primary keys and timestamps;
- it validates row counts and foreign-key references after copying.

Run from the repository root with POSTGRES_URL set in the environment. The
SQLite database is never modified by this script.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, func, select, text

# Running this file directly puts ``scripts`` on sys.path. Add the repository
# root so the migration uses the same backend models as the application.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.database import Base
from backend.models import db_models  # noqa: F401 - register all models


TABLE_ORDER = (
    "coordinators",
    "attendee_accounts",
    "events",
    "attendees",
    "device_tokens",
    "notification_logs",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite",
        default="qrevent.db",
        help="SQLite database path, relative to the repository root (default: qrevent.db)",
    )
    return parser.parse_args()


def table_counts(connection, metadata: MetaData) -> dict[str, int]:
    return {
        table_name: connection.execute(
            select(func.count()).select_from(metadata.tables[table_name])
        ).scalar_one()
        for table_name in TABLE_ORDER
    }


def validate_foreign_keys(connection, metadata: MetaData) -> None:
    checks = (
        ("events", "coordinator_id", "coordinators", "id"),
        ("attendees", "event_id", "events", "id"),
        ("attendees", "account_id", "attendee_accounts", "id"),
        ("device_tokens", "attendee_id", "attendees", "id"),
        ("notification_logs", "event_id", "events", "id"),
        ("notification_logs", "sent_by", "coordinators", "id"),
    )
    for child, child_column, parent, parent_column in checks:
        child_table = metadata.tables[child]
        parent_table = metadata.tables[parent]
        orphan_count = connection.execute(
            select(func.count())
            .select_from(child_table.outerjoin(
                parent_table,
                child_table.c[child_column] == parent_table.c[parent_column],
            ))
            .where(
                child_table.c[child_column].is_not(None),
                parent_table.c[parent_column].is_(None),
            )
        ).scalar_one()
        if orphan_count:
            raise RuntimeError(
                f"Migration validation failed: {child}.{child_column} has "
                f"{orphan_count} orphaned reference(s) to {parent}.{parent_column}."
            )


def main() -> None:
    args = parse_args()
    postgres_url = os.getenv("POSTGRES_URL", "").strip()
    if not postgres_url.startswith(("postgresql://", "postgresql+")):
        raise SystemExit(
            "POSTGRES_URL must be set to a PostgreSQL SQLAlchemy URL, "
            "for example postgresql+psycopg://postgres:<password>@127.0.0.1:5432/qrevent"
        )

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path.resolve()}")

    sqlite_engine = create_engine(f"sqlite:///{sqlite_path.resolve().as_posix()}")
    postgres_engine = create_engine(postgres_url, pool_pre_ping=True)

    sqlite_metadata = MetaData()
    sqlite_metadata.reflect(bind=sqlite_engine)
    missing_tables = [name for name in TABLE_ORDER if name not in sqlite_metadata.tables]
    if missing_tables:
        raise SystemExit(f"SQLite database is missing table(s): {', '.join(missing_tables)}")

    Base.metadata.create_all(bind=postgres_engine)
    postgres_metadata = Base.metadata

    with sqlite_engine.connect() as sqlite_connection:
        source_counts = table_counts(sqlite_connection, sqlite_metadata)
        print(f"SQLite source counts: {source_counts}")

        with postgres_engine.begin() as postgres_connection:
            target_counts = table_counts(postgres_connection, postgres_metadata)
            if any(target_counts.values()):
                raise SystemExit(
                    "PostgreSQL already contains application data; refusing to merge. "
                    f"Target counts: {target_counts}"
                )

            for table_name in TABLE_ORDER:
                source_table = sqlite_metadata.tables[table_name]
                target_table = postgres_metadata.tables[table_name]
                rows = [
                    {
                        column.name: row._mapping[column.name]
                        for column in source_table.columns
                        if column.name in target_table.c
                    }
                    for row in sqlite_connection.execute(select(source_table))
                ]
                if rows:
                    postgres_connection.execute(target_table.insert(), rows)
                print(f"Copied {table_name}: {len(rows)} row(s)")

            # Explicitly copied IDs need their PostgreSQL sequences advanced so
            # the next newly-created record does not collide with old data.
            for table_name in TABLE_ORDER:
                postgres_connection.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
                        "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) "
                        f"FROM {table_name}"
                    ),
                    {"table_name": f"public.{table_name}"},
                )

            validate_foreign_keys(postgres_connection, postgres_metadata)
            copied_counts = table_counts(postgres_connection, postgres_metadata)
            if copied_counts != source_counts:
                raise RuntimeError(
                    f"Migration validation failed: source={source_counts}, "
                    f"target={copied_counts}"
                )

    print(f"PostgreSQL target counts: {source_counts}")
    print("Migration completed and foreign-key validation passed.")


if __name__ == "__main__":
    main()
