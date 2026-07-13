import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# Import all models here so Alembic can detect them when autogenerating migrations.
# As you add new model files, import them here too.
from app.models import Base
from app.models.venue import Venue  # noqa: F401
from app.models.composer import Composer  # noqa: F401
from app.models.performer import Performer  # noqa: F401
from app.models.work import Work  # noqa: F401
from app.models.performance import Performance  # noqa: F401
from app.models.set_list_entry import SetListEntry  # noqa: F401
from app.models.set_list_performer import SetListPerformer  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = os.environ["DATABASE_URL"]


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
