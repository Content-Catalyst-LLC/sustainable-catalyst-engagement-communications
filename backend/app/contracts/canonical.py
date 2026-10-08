"""v8.1 canonical models: validation contracts only, no persistence or legacy writes."""
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION = "8.1.0"

def utc_now():
    return datetime.now(timezone.utc)

class Classification(str, Enum):
    public="public"
    internal="internal"
    confidential="confidential"
    restricted="restricted"

class LegacySystem(str, Enum):
    product_support_feedback="product_support_feedback"
    engagement_intake="engagement_intake"

class LegacyIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: LegacySystem
    object_type: str = Field(min_length=1,max_length=80)
    external_id: str = Field(min_length=1,max_length=255)
    origin_version: str | None = Field(default=None, max_length=40)

class CanonicalBase(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID | None = None
    schema_version: Literal["8.1.0"] = CONTRACT_VERSION
    classification: Classification = Classification.internal
    legacy_identity: LegacyIdentity | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    @model_validator(mode="after")
    def dates(self):
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        return self

class Organization(CanonicalBase):
    name: str = Field(min_length=1,max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",max_length=100)

class Contact(CanonicalBase):
    display_name: str = Field(min_length=1,max_length=255)
    email: str | None = Field(default=None,max_length=320)
    marketing_consent: bool = False
    @model_validator(mode="after")
    def privacy(self):
        if self.classification == Classification.public:
            raise ValueError("contacts cannot be public")
        return self

class Case(CanonicalBase):
    title: str = Field(min_length=1,max_length=255)
    status: Literal["open","triaged","in_progress","resolved","closed"] = "open"
    requester_contact_id: UUID | None = None
    product_key: str | None = Field(default=None,max_length=100)

class Inquiry(CanonicalBase):
    subject: str = Field(min_length=1,max_length=255)
    status: Literal["new","reviewing","responded","closed"] = "new"
    contact_id: UUID | None = None

class AdvisoryEngagement(CanonicalBase):
    title: str = Field(min_length=1,max_length=255)
    status: Literal["proposed","active","paused","completed","cancelled"] = "proposed"

class Newsletter(CanonicalBase):
    title: str = Field(min_length=1,max_length=255)
    status: Literal["draft","review","approved","published"] = "draft"
    source_refs: list[str] = Field(default_factory=list)
    approval_actor_id: UUID | None = None

class Form(CanonicalBase):
    title: str = Field(min_length=1,max_length=255)
    revision: int = Field(default=1,ge=1)
    status: Literal["draft","published","archived"] = "draft"

class Survey(CanonicalBase):
    form_id: UUID
    title: str = Field(min_length=1,max_length=255)

class Submission(CanonicalBase):
    form_id: UUID
    form_revision: int = Field(ge=1)
    respondent_contact_id: UUID | None = None
    payload_ref: str = Field(min_length=1,max_length=512,description="Opaque reference only; no sensitive answers embedded")
    classification: Classification = Classification.confidential
    @model_validator(mode="after")
    def privacy(self):
        if self.classification in (Classification.public, Classification.internal):
            raise ValueError("submissions must be confidential or restricted")
        return self

class TestDefinition(CanonicalBase):
    title: str = Field(min_length=1,max_length=255)
    question_bank_refs: list[str] = Field(default_factory=list)
    answer_key_ref: str | None = None

class Assessment(CanonicalBase):
    title: str = Field(min_length=1,max_length=255)
    rubric_ref: str | None = None
    human_review_required: bool = True

class EngagementEvent(CanonicalBase):
    category: Literal["newsletter","form","test","assessment","support","contact","advisory"]
    event_type: str = Field(min_length=1,max_length=100)
    subject_ref: str = Field(min_length=1,max_length=255)
    occurred_at: datetime = Field(default_factory=utc_now)

MODEL_REGISTRY = {
    "organizations": Organization,
    "contacts": Contact,
    "cases": Case,
    "inquiries": Inquiry,
    "advisory_engagements": AdvisoryEngagement,
    "newsletters": Newsletter,
    "forms": Form,
    "surveys": Survey,
    "submissions": Submission,
    "tests": TestDefinition,
    "assessments": Assessment,
    "engagement_events": EngagementEvent,
}
