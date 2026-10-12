"""v9.3 non-persistent product support and case management intelligence.
No database, network I/O, notification, WordPress mutation, or case writes.
Classification, transition advice and escalation are decision SUPPORT only.
"""
import os
import re
from uuid import UUID
from collections import Counter
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .identity import Principal, bound_mode, principal, tenant_for_principal

router = APIRouter(prefix="/v1/support-intelligence", tags=["support-intelligence-staging"])
CATEGORIES=("access","bug","data-quality","billing","integration","documentation","other")
STATES=("new","triaged","in-progress","waiting-on-requester","resolved","closed")
NEXT={"new":("triaged",),"triaged":("in-progress","waiting-on-requester"),"in-progress":("waiting-on-requester","resolved"),"waiting-on-requester":("in-progress","resolved"),"resolved":("closed","in-progress"),"closed":()}
KEYWORDS={"access":("login","sign in","password","permission","account"),"bug":("error","crash","broken","exception","failure"),"data-quality":("dataset","incorrect data","missing data","outdated","provenance"),"billing":("invoice","subscription","billing","charge"),"integration":("api","webhook","connector","integration"),"documentation":("documentation","guide","tutorial","instructions")}

class CasePreview(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    subject:str=Field(min_length=4,max_length=180)
    description:str=Field(min_length=12,max_length=5000)
    source:str=Field(default="staging-test",pattern=r"^(wordpress-support|staging-test)$")
    category:str|None=None
    severity:str=Field(default="unspecified",pattern=r"^(unspecified|low|medium|high|critical)$")
    affected_users:int=Field(default=1,ge=0,le=1000000)
    service_unavailable:bool=False
    security_concern:bool=False
    current_status:str=Field(default="new")
    proposed_status:str|None=None
    @field_validator("category")
    @classmethod
    def valid_category(cls,v):
        if v is not None and v not in CATEGORIES:raise ValueError("Unknown category")
        return v
    @field_validator("current_status","proposed_status")
    @classmethod
    def valid_status(cls,v):
        if v is not None and v not in STATES:raise ValueError("Unknown status")
        return v
    @field_validator("subject","description")
    @classmethod
    def meaningful(cls,v):
        if not v.strip() or any(ord(ch)<32 and ch not in "\n\r\t" for ch in v):raise ValueError("Invalid content")
        return v

class CaseBatch(BaseModel):
    model_config=ConfigDict(extra="forbid")
    cases:list[CasePreview]=Field(min_length=1,max_length=25)

def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv("SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED","0")!="1":raise HTTPException(503,"Support intelligence staging disabled")
    if not bound_mode():raise HTTPException(503,"Bound identity required")
    org=tenant_for_principal(x_scec_organization_id,actor)
    allowed={v.strip() for v in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS","").split(",") if v.strip()}
    if str(org) not in allowed:raise HTTPException(403,"Organization not allowlisted")
    if not actor.roles.intersection({"contact_editor","administrator"}):raise HTTPException(403,"Permission denied")
    return org

def analyze(case:CasePreview)->dict:
    text=(case.subject+" "+case.description).casefold()
    scores={k:sum(1 for word in terms if re.search(r"(?<!\w)"+re.escape(word)+r"(?!\w)",text)) for k,terms in KEYWORDS.items()}
    inferred=max(KEYWORDS,key=lambda k:(scores[k],-list(KEYWORDS).index(k))) if any(scores.values()) else "other"
    category=case.category or inferred
    base={"unspecified":10,"low":10,"medium":35,"high":60,"critical":85}[case.severity]
    score=min(100,base+(20 if case.service_unavailable else 0)+(25 if case.security_concern else 0)+(15 if case.affected_users>=100 else 5 if case.affected_users>=10 else 0))
    band="critical" if score>=85 else "high" if score>=60 else "medium" if score>=35 else "low"
    escalation="human-security-review" if case.security_concern else "urgent-human-triage" if score>=85 else "standard-human-triage"
    allowed=NEXT[case.current_status]
    return {"category":category,"classification":"explicit" if case.category else "rules-based", "severity_score":score,"severity_band":band,"escalation_recommendation":escalation,"status":case.current_status,"allowed_next_statuses":list(allowed),"transition_valid":case.proposed_status in allowed if case.proposed_status is not None else None,"human_review_required":True}

@router.get("/status")
def status(org:UUID=Depends(scope)):
    return {"version":"9.3.0","staging":True,"writes_enabled":False,"wordpress_bridge":"not-connected","organization_id":str(org),"max_batch":25}

@router.post("/case-preview")
def case_preview(case:CasePreview,org:UUID=Depends(scope)):
    return {"version":"9.3.0","organization_id":str(org),"preview_only":True,"persisted":False,"forwarded":False,"analysis":analyze(case)}

@router.post("/summary-preview")
def summary(batch:CaseBatch,org:UUID=Depends(scope)):
    analyses=[analyze(case) for case in batch.cases]
    return {"version":"9.3.0","organization_id":str(org),"preview_only":True,"persisted":False,"forwarded":False,"count":len(analyses),"category_counts":dict(Counter(a["category"] for a in analyses)),"severity_counts":dict(Counter(a["severity_band"] for a in analyses)),"escalation_counts":dict(Counter(a["escalation_recommendation"] for a in analyses)),"human_review_required":True}

@router.post("/commit")
def commit_denied(org:UUID=Depends(scope)):
    raise HTTPException(503,"Case writes disabled in v9.3.0")
