"""v9.4 advisory relationship intelligence: deterministic, private, non-persistent decision support."""
import os
import re
from collections import Counter
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .identity import Principal, bound_mode, principal, tenant_for_principal

router = APIRouter(prefix="/v1/institutional-intelligence", tags=["institutional-intelligence-staging"])
KINDS = ("research-partnership","academic-collaboration","public-sector","funding","advisory","vendor","other")
STATES = ("inquiry","qualified","discovery","proposal","review","approved","declined","closed")
NEXT = {
    "inquiry": ("qualified","declined"), "qualified": ("discovery","declined"),
    "discovery": ("proposal","declined"), "proposal": ("review","declined"),
    "review": ("approved","declined"), "approved": ("closed",),
    "declined": ("closed",), "closed": ()
}
SIGNALS = {
    "research-partnership": ("research","study","research collaboration","joint publication"),
    "academic-collaboration": ("university","faculty","academic","student"),
    "public-sector": ("government","municipal","public agency","city council"),
    "funding": ("grant","funding","sponsor","donation"),
    "advisory": ("advisory","consulting","expertise","guidance"),
    "vendor": ("procurement","vendor","supplier","license")
}
class RelationshipPreview(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    organization_name:str=Field(min_length=2,max_length=180)
    inquiry_title:str=Field(min_length=4,max_length=180)
    description:str=Field(min_length=12,max_length=4000)
    source:str=Field(default="staging-test",pattern=r"^(staging-test|wordpress-contact|institutional-referral)$")
    relationship_type:str|None=None
    current_stage:str=Field(default="inquiry")
    proposed_stage:str|None=None
    public_interest_relevance:bool=False
    data_sharing_requested:bool=False
    conflict_of_interest_flag:bool=False
    human_approval_recorded:bool=False

    @field_validator("relationship_type")
    @classmethod
    def valid_kind(cls,v):
        if v is not None and v not in KINDS: raise ValueError("Invalid relationship type")
        return v
    @field_validator("current_stage","proposed_stage")
    @classmethod
    def valid_stage(cls,v):
        if v is not None and v not in STATES: raise ValueError("Invalid stage")
        return v
    @field_validator("organization_name","inquiry_title","description")
    @classmethod
    def valid_text(cls,v):
        if any(ord(c)<32 and c not in "\\n\\r\\t" for c in v): raise ValueError("Invalid text")
        return v

class RelationshipBatch(BaseModel):
    model_config=ConfigDict(extra="forbid")
    inquiries:list[RelationshipPreview]=Field(min_length=1,max_length=25)

def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv("SCEC_INSTITUTIONAL_STAGING_ENABLED","0")!="1": raise HTTPException(503,"Institutional intelligence staging disabled")
    if not bound_mode(): raise HTTPException(503,"Bound identity required")
    org=tenant_for_principal(x_scec_organization_id,actor)
    allowed={v.strip() for v in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS","").split(",") if v.strip()}
    if str(org) not in allowed: raise HTTPException(403,"Organization not allowlisted")
    if not actor.roles.intersection({"administrator","advisor"}): raise HTTPException(403,"Advisory role required")
    return org

def analyze(item:RelationshipPreview)->dict:
    words=(item.inquiry_title+" "+item.description).casefold()
    scores={kind:sum(bool(re.search(r"(?<!\\w)"+re.escape(term)+r"(?!\\w)",words)) for term in terms) for kind,terms in SIGNALS.items()}
    kind=item.relationship_type or (max(SIGNALS,key=lambda k:scores[k]) if any(scores.values()) else "other")
    risk=[]
    if item.data_sharing_requested:risk.append("data-sharing-review")
    if item.conflict_of_interest_flag:risk.append("conflict-of-interest-review")
    stage_allowed=NEXT[item.current_stage]
    transition_valid=item.proposed_stage in stage_allowed if item.proposed_stage is not None else None
    # Never authorize approvals or infer consent from a preview.
    return {"relationship_type":kind,"classification":"explicit" if item.relationship_type else "rules-based",
            "current_stage":item.current_stage,"allowed_next_stages":list(stage_allowed),
            "transition_valid":transition_valid,"review_flags":risk,
            "public_interest_relevance_reported":item.public_interest_relevance,
            "approval_effective":False,"human_review_required":True}

@router.get("/status")
def status(org:UUID=Depends(scope)):
    return {"version":"9.4.0","organization_id":str(org),"staging":True,
            "writes_enabled":False,"wordpress_bridge":"not-connected","max_batch":25}

@router.post("/relationship-preview")
def relationship_preview(payload:RelationshipPreview,org:UUID=Depends(scope)):
    return {"version":"9.4.0","organization_id":str(org),"preview_only":True,
            "persisted":False,"forwarded":False,"analysis":analyze(payload)}

@router.post("/portfolio-preview")
def portfolio_preview(payload:RelationshipBatch,org:UUID=Depends(scope)):
    items=[analyze(item) for item in payload.inquiries]
    return {"version":"9.4.0","organization_id":str(org),"preview_only":True,
            "persisted":False,"forwarded":False,"count":len(items),
            "type_counts":dict(Counter(i["relationship_type"] for i in items)),
            "stage_counts":dict(Counter(i["current_stage"] for i in items)),
            "review_flag_counts":dict(Counter(f for i in items for f in i["review_flags"])),
            "human_review_required":True}

@router.post("/commit")
def commit_denied(org:UUID=Depends(scope)):
    raise HTTPException(503,"Institutional relationship writes disabled in v9.4.0")
