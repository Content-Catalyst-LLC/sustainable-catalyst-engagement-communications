import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from app.persistence.models import metadata, TABLES
from app.persistence.rehearsal import rehearse

def test_twelve_canonical_tables():
    assert len(TABLES)==12
    assert 'import_batches' in metadata.tables

def test_all_tables_have_required_columns():
    for table in TABLES.values():
        assert {'id','organization_id','payload','legacy_external_id','classification'} <= set(table.c.keys())

def test_tenant_fk_for_non_organizations():
    for name,table in TABLES.items():
        if name!='organizations':
            assert table.c.organization_id.nullable is False
            assert any(fk.column.table.name=='organizations' for fk in table.c.organization_id.foreign_keys)

def test_postgresql_compiles():
    for t in TABLES.values():
        assert 'CREATE TABLE' in str(CreateTable(t).compile(dialect=postgresql.dialect()))

def test_submission_has_privacy_constraint():
    assert any(getattr(c,'name','')=='ck_submissions_submission_privacy' for c in TABLES['submissions'].constraints)

def test_rehearsal_never_writes():
    o=uuid4(); now=datetime.now(timezone.utc).isoformat()
    data=[{'model':'contacts','record':{'organization_id':str(o),'display_name':'Example','created_at':now,'updated_at':now}}]
    x=rehearse(data)
    assert x['ready'] and x['writes']==0 and x['counts']['contacts']==1

def test_missing_tenant_rejected():
    x=rehearse([{'model':'contacts','record':{'display_name':'Example'}}])
    assert not x['ready'] and x['writes']==0

def test_duplicate_legacy_rejected():
    o=str(uuid4()); item={'organization_id':o,'display_name':'X','legacy_identity':{'system':'engagement_intake','object_type':'contact','external_id':'1'}}
    x=rehearse([{'model':'contacts','record':item},{'model':'contacts','record':item}])
    assert not x['ready']

def test_bad_model_rejected():
    assert not rehearse([{'model':'unknown','record':{}}])['ready']
