import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

from backend.models.db_models import AccountDeviceToken, Base


def main() -> None:
    load_dotenv()
    database_url = os.getenv("SCHEMA_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Set SCHEMA_DATABASE_URL or DATABASE_URL before running this migration")

    engine = create_engine(database_url)
    Base.metadata.create_all(engine, tables=[AccountDeviceToken.__table__])
    table_names = inspect(engine).get_table_names()
    if "account_device_tokens" not in table_names:
        raise RuntimeError("account_device_tokens table was not created")
    print("account_device_tokens migration complete")


if __name__ == "__main__":
    main()
