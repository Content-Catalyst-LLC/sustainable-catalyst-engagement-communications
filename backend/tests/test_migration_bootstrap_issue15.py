"""Compile the actual migration chain, including Alembic's audit registration."""
import io
from pathlib import Path
from alembic import command
from alembic.config import Config


def migration_sql(monkeypatch, target):
    backend = Path(__file__).resolve().parents[1]
    monkeypatch.setenv('SCEC_DATABASE_URL', 'postgresql+psycopg://synthetic@localhost/scec_engagement_compile_only')
    output = io.StringIO()
    config = Config(str(backend / 'alembic.ini'), output_buffer=output)
    config.set_main_option('script_location', str(backend / 'alembic'))
    command.upgrade(config, target, sql=True)
    return output.getvalue()


def test_initial_revision_does_not_create_later_audit_table(monkeypatch):
    sql = migration_sql(monkeypatch, '820_001')
    assert sql.count('CREATE TABLE organizations (') == 1
    assert sql.count('CREATE TABLE contacts (') == 1
    assert sql.count('CREATE TABLE import_batches (') == 1
    assert 'CREATE TABLE engagement_audit_log (' not in sql
    assert 'CREATE TABLE support_history (' not in sql


def test_complete_chain_creates_each_ledger_once(monkeypatch):
    sql = migration_sql(monkeypatch, 'head')
    for name in ('organizations', 'contacts', 'engagement_audit_log',
                 'support_history', 'advisory_approvals', 'advisory_workflow_history'):
        assert sql.count(f'CREATE TABLE {name} (') == 1
    assert "'850_001'" in sql
