"""v9.1 staging-only Contact/Feedback validation boundary.

No inserts, migrations, queues, outbound requests, WordPress hooks or PII persistence.
Access requires an authenticated bound service principal, permitted role and organization.
"""
import os
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .identity import Principal, bound_mode, principal, tenant_for_principal

router = APIRouter(prefix="/v1/intake", tags=["intake-staging"])

class IntakeSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal["contact", "feedback"]
    source: Literal["wordpress-contact", "wordpress-feedback", "staging-test"]
    name: str = Field(min_length=1,max_length=160)
    email: str = Field(min_length=3,max_length=254)
    subject: str = Field(min_length=1,max_length=200)
    message: str = Field(min_length=1,max_length=8000)
    consent_to_reply: bool = False
    reference: str | None = Field(default=None,max_length=120)
    @field_validator("name","subject","message")
    @classmethod
    def meaningful(cls,value):
        if not value.strip() or any(ord(c)<32 and c not in "\n\r\t" for c in value):
            raise ValueError("Field cannot be empty or contain control characters")
        return value
    @field_validator("email")
    @classmethod
    def email_syntax(cls,value):
        # Syntax check only; ownership is not asserted.
        import re
        if not re.fullmatch(r"[^\s@]{1,64}@[^\s@]{1,189}\.[A-Za-z]{2,63}",value):
            raise ValueError("Invalid email syntax")
        return value.lower()


def intake_tenant(x_scec_organization_id: str | None = Header(default=None),actor:Principal|None=Depends(principal)) -> UUID:
    # Independent of SCEC_PERSISTENCE_ENABLED; never opens the DB.
    if os.getenv('SCEC_INTAKE_STAGING_ENABLED','0')!='1':
        raise HTTPException(503,'Intake staging disabled')
    if not bound_mode():
        raise HTTPException(503,'Bound service principal required for intake staging')
    tenant=tenant_for_principal(x_scec_organization_id,actor)
    allowed={v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}
    if str(tenant) not in allowed:
        raise HTTPException(403,'Organization not allowlisted')
    if not actor.roles.intersection({'contact_editor','administrator'}):
        raise HTTPException(403,'Intake permission denied')
    return tenant

@router.get('/status')
def status(tenant: UUID=Depends(intake_tenant)):
    return {'version':'9.1.0','staging':True,'writes_enabled':False,
            'bridge':'not-connected','organization_id':str(tenant),
            'supported_kinds':['contact','feedback']}

@router.post('/preview')
def preview(payload:IntakeSubmission,tenant:UUID=Depends(intake_tenant)):
    expected={'contact':'wordpress-contact','feedback':'wordpress-feedback'}
    if payload.source not in (expected[payload.kind],'staging-test'):
        raise HTTPException(422,'Source does not match intake kind')
    # Echo no PII; no storage, event emission or third-party side effects.
    return {'accepted_for_preview':True,'persisted':False,'forwarded':False,
            'organization_id':str(tenant),'kind':payload.kind,
            'source':payload.source,'normalized_email':True,
            'consent_to_reply':payload.consent_to_reply,
            'next_action':'human_review_required'}

@router.post('/commit')
def commit_denied(tenant:UUID=Depends(intake_tenant)):
    # Intentionally never honors SCEC_PERSISTENCE_ENABLED or user payload.
    raise HTTPException(503,'Production intake is disabled in v9.1.0')
