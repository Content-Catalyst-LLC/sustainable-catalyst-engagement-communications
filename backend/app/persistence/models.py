"""v8.2 PostgreSQL schema; canonical payloads persist as JSONB with relational identities.
No user-facing or external write endpoints. Do not point at legacy databases.
"""
from sqlalchemy import MetaData, Table, Column, String, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.contracts.canonical import MODEL_REGISTRY

metadata = MetaData(naming_convention={"ix":"ix_%(table_name)s_%(column_0_name)s","uq":"uq_%(table_name)s_%(column_0_name)s","ck":"ck_%(table_name)s_%(constraint_name)s","fk":"fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s","pk":"pk_%(table_name)s"})
organizations = Table('organizations', metadata,
 Column('id',UUID(as_uuid=True),primary_key=True),
 Column('organization_id',UUID(as_uuid=True),nullable=True),
 Column('schema_version',String(30),nullable=False),
 Column('classification',String(16),nullable=False),
 Column('created_at',DateTime(timezone=True),nullable=False),
 Column('updated_at',DateTime(timezone=True),nullable=False),
 Column('legacy_system',String(80)),Column('legacy_object_type',String(80)),Column('legacy_external_id',String(255)),
 Column('payload',JSONB,nullable=False),
 CheckConstraint("organization_id IS NULL OR organization_id = id",name='organization_self'),
 CheckConstraint("classification IN ('internal','confidential','restricted')",name='classification'),
 UniqueConstraint('id','organization_id',name='uq_organizations_id_tenant'),
 )
TABLES={'organizations':organizations}
for name in MODEL_REGISTRY:
 if name=='organizations': continue
 table=Table(name, metadata,
  Column('id',UUID(as_uuid=True),primary_key=True),
  Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id',ondelete='RESTRICT'),nullable=False,index=True),
  Column('schema_version',String(30),nullable=False),
  Column('classification',String(16),nullable=False),
  Column('created_at',DateTime(timezone=True),nullable=False),
  Column('updated_at',DateTime(timezone=True),nullable=False),
  Column('legacy_system',String(80)),Column('legacy_object_type',String(80)),Column('legacy_external_id',String(255)),
  Column('payload',JSONB,nullable=False),
  CheckConstraint("classification IN ('internal','confidential','restricted')",name='classification'),
  *( [CheckConstraint("classification IN ('confidential','restricted')",name='submission_privacy')] if name=='submissions' else []),
  UniqueConstraint('id','organization_id',name=f'uq_{name}_id_tenant'),
 )
 TABLES[name]=table
for name,t in TABLES.items():
 Index(f'ux_{name}_legacy_identity',t.c.legacy_system,t.c.legacy_object_type,t.c.legacy_external_id,unique=True,postgresql_where=text('legacy_system IS NOT NULL AND legacy_object_type IS NOT NULL AND legacy_external_id IS NOT NULL'))
 Index(f'ix_{name}_created_at',t.c.created_at)

# Provenance ledger records rehearsal imports, not a license to modify legacy systems.
import_batches=Table('import_batches',metadata,
 Column('id',UUID(as_uuid=True),primary_key=True),
 Column('legacy_system',String(80),nullable=False),
 Column('mode',String(12),nullable=False),
 Column('state',String(20),nullable=False),
 Column('created_at',DateTime(timezone=True),server_default=func.now(),nullable=False),
 CheckConstraint("mode IN ('rehearsal','planned')",name='mode'),
 CheckConstraint("state IN ('created','verified','cancelled')",name='state'))
