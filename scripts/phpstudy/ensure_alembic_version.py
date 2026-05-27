from __future__ import annotations

from sqlalchemy import create_engine, text

from app.config import get_settings


def main() -> int:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    statements = [
        """
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(128) NOT NULL,
            PRIMARY KEY (version_num)
        )
        """,
        """
        ALTER TABLE alembic_version
        MODIFY version_num VARCHAR(128) NOT NULL
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print("alembic_version table is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
