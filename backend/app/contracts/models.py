from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class Domain(str, Enum):
    support = 'support'
    contacts = 'contacts'
    advisory = 'advisory'
    newsletters = 'newsletters'
    forms = 'forms'
    tests = 'tests'
    assessments = 'assessments'
    analytics = 'analytics'
    integrations = 'integrations'

class ObjectRef(BaseModel):
    system: str = Field(min_length=1, max_length=100)
    object_type: str = Field(min_length=1, max_length=100)
    object_id: str = Field(min_length=1, max_length=255)

class EngagementObject(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    domain: Domain
    source: ObjectRef
    organization_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    schema_version: str = '1.0.0'
    attributes: Dict[str, Any] = Field(default_factory=dict)

class HandoffEnvelope(BaseModel):
    contract_version: str = '1.0.0'
    correlation_id: str = Field(min_length=1, max_length=255)
    origin: ObjectRef
    destination: Domain
    subject: EngagementObject
    approved: bool = False

class DomainDescriptor(BaseModel):
    name: Domain
    status: str
    owner: str
    legacy_source: Optional[str] = None
    notes: str = ''
