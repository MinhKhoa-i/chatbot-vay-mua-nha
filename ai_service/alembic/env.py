from logging.config import fileConfig

from alembic import context

from app.core.config import Settings


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = Settings().database_url
if not database_url:
    raise RuntimeError("DATABASE_URL is not configured")
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = None


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=None,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline Alembic migrations are not supported")
else:
    run_migrations_online()
