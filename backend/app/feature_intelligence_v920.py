"""v9.2 internal feature suggestion intelligence. No database, network, persistence, WordPress actions or user-text echo."""
import os
import re
from hashlib import sha256
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .identity import Principal, bound_mode, principal, tenant_for_principal

router=APIRouter(prefix="/v1/community-intelligence",tags=["feature-intelligence-staging"])
AREAS=("library","librarian","workspace","workbench","decision-studio","research-lab","site-intelligence","platform","other")
WORDS={
 "library":("library","catalog","citation","archive","document"),
 "librarian":("librarian","retrieval","search assistant"),
 "workspace":("workspace","notebook","dataset"),
 "workbench":("workbench","calculator","equation","solver"),
 "decision-studio":("decision","scenario","canvas"),
 "research-lab":("lab","experiment","bayesian","hypothesis"),
 "site-intelligence":("map","country","geospatial","ocean","satellite"),
}

class Suggestion(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    title:str=Field(min_length=4,max_length=180)
    description:str=Field(min_length=12,max_length=5000)
    source:str=Field(default="staging-test",pattern=r"^(wordpress-feature-suggestions|staging-test)$")
    product_area:str|None=None
    vote_count:int=Field(default=0,ge=0,le=100000)
    impact:str=Field(default="unspecified",pattern=r"^(unspecified|low|medium|high)$")
    @field_validator("title","description")
    @classmethod
    def meaningful(cls,value):
        if not value.strip() or any(ord(ch)<32 and ch not in "\n\r\t" for ch in value):
            raise ValueError("Content missing or contains control characters")
        return value
    @field_validator("product_area")
    @classmethod
    def area(cls,value):
        if value is not None and value not in AREAS:raise ValueError("Unknown product area")
        return value

class CommunityBatch(BaseModel):
    model_config=ConfigDict(extra="forbid")
    suggestions:list[Suggestion]=Field(min_length=1,max_length=25)


def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv("SCEC_COMMUNITY_STAGING_ENABLED","0")!="1":raise HTTPException(503,"Community staging disabled")
    if not bound_mode():raise HTTPException(503,"Bound identity required")
    org=tenant_for_principal(x_scec_organization_id,actor)
    allowed={i.strip() for i in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS","").split(",") if i.strip()}
    if str(org) not in allowed:raise HTTPException(403,"Organization not allowlisted")
    if not actor.roles.intersection({"contact_editor","administrator"}):raise HTTPException(403,"Permission denied")
    return org


def tokens(raw:str)->set[str]:
    # Ephemeral only: normalized strings never leave this process.
    return set(re.findall(r"[a-z0-9]{3,}",raw.casefold()))


def fingerprint(item:Suggestion)->str:
    normalized=" ".join(sorted(tokens(item.title+" "+item.description)))
    return sha256(normalized.encode()).hexdigest()[:16]


def classify(item:Suggestion)->dict:
    text=(item.title+" "+item.description).casefold()
    scores={area:sum(1 for word in words if re.search(r"(?<!\w)"+re.escape(word)+r"(?!\w)",text)) for area,words in WORDS.items()}
    inferred=max(AREAS[:-2],key=lambda a:(scores.get(a,0),-AREAS.index(a))) if any(scores.values()) else "other"
    area=item.product_area or inferred
    priority=min(100, 10+min(item.vote_count,50)+{"unspecified":0,"low":5,"medium":15,"high":30}[item.impact])
    return {"product_area":area,"classification":"explicit" if item.product_area else "rules-based", "priority_score":priority,"priority_band":"high" if priority>=65 else "medium" if priority>=35 else "low","fingerprint":fingerprint(item)}

@router.get("/status")
def status(org:UUID=Depends(scope)):
    return {"version":"9.2.0","staging":True,"writes_enabled":False,"wordpress_bridge":"not-connected","organization_id":str(org),"max_batch":25}

@router.post("/preview")
def preview(item:Suggestion,org:UUID=Depends(scope)):
    return {"version":"9.2.0","organization_id":str(org),"preview_only":True,"persisted":False,"forwarded":False,"analysis":classify(item),"human_review_required":True}

@router.post("/aggregate-preview")
def aggregate(batch:CommunityBatch,org:UUID=Depends(scope)):
    analyzed=[classify(item) for item in batch.suggestions]
    # Similarity is explicitly limited to exact normalized fingerprints WITHIN the submitted request.
    duplicate_groups={}
    for i,row in enumerate(analyzed):duplicate_groups.setdefault(row["fingerprint"],[]).append(i)
    counts={a:sum(1 for row in analyzed if row["product_area"]==a) for a in AREAS}
    return {"version":"9.2.0","organization_id":str(org),"preview_only":True,"persisted":False,"forwarded":False,
            "count":len(analyzed),"product_area_counts":counts,
            "possible_duplicate_index_groups":[v for v in duplicate_groups.values() if len(v)>1],
            "duplicate_method":"exact-normalized-fingerprint-within-request-only",
            "results":analyzed,"human_review_required":True}

@router.post("/commit")
def deny_commit(org:UUID=Depends(scope)):
    raise HTTPException(503,"Community intelligence writes disabled in v9.2.0")
