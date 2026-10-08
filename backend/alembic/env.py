from logging.config import fileConfig
import os
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.persistence.models import metadata
config=context.config
target_metadata=metadata
url=os.environ.get('SCEC_DATABASE_URL')
if not url:
    raise RuntimeError('SCEC_DATABASE_URL required (dedicated database only)')
if not url.startswith(('postgresql+psycopg://','postgresql://')):
    raise RuntimeError('PostgreSQL required')
config.set_main_option('sqlalchemy.url',url.replace('%','%%'))
def run_migrations_offline():
    context.configure(url=url,target_metadata=target_metadata,literal_binds=True,dialect_opts={'paramstyle':'named'},compare_type=True)
    with context.begin_transaction():context.run_migrations()
def run_migrations_online():
    engine=engine_from_config(config.get_section(config.config_ini_section),prefix='sqlalchemy.',poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()
    engine.dispose()
if context.is_offline_mode():run_migrations_offline()
else:run_migrations_online()
