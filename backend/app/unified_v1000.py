"""Consolidated read-only discovery for v10.0.0. No external calls or mutation."""
import hashlib, json, os
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .identity import Principal, principal, bound_mode, tenant_for_principal
router=APIRouter(prefix="/v1/unified-platform",tags=["unified-platform-staging"])
DOMAINS=("human-auth","intake","community-intelligence","support-intelligence","institutional-intelligence","communications-intelligence","engagement-analytics","privacy-governance","federation-intelligence","release-assurance")
FLAGS=("SCEC_PERSISTENCE_ENABLED","SCEC_OUTBOUND_ENABLED","SCEC_DELETION_ENABLED","SCEC_FEDERATION_ENABLED")
PAGES=("Contact","Feedback","Feature Suggestions","Channel","Support")
GATES=("public_https_dns_tls","wordpress_public_launcher_acceptance","authenticated_human_session","csrf_revocation_session_expiry","live_tenant_isolation_roles","privacy_retention_policy","staged_persistence_write_certification")
class Preview(BaseModel):
    model_config=ConfigDict(extra="forbid")
    domains:list[str]=Field(default_factory=list,max_length=10)
def scope(x_scec_organization_id:str|None=Header(default=None), actor:Principal|None=Depends(principal))->UUID:
    if os.getenv("SCEC_UNIFIED_STAGING_ENABLED","0")!="1":raise HTTPException(503,"Unified staging disabled")
    if not bound_mode():raise HTTPException(503,"Bound identity required")
    org=tenant_for_principal(x_scec_organization_id,actor)
    if str(org) not in {a.strip() for a in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS","").split(",") if a.strip()}:raise HTTPException(403,"Tenant not allowlisted")
    if not actor.roles.intersection({"administrator","service"}):raise HTTPException(403,"Administrator role required")
    return org
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def snapshot():
    enabled=sorted(f for f in FLAGS if os.getenv(f,"0")!="0")
    return {"version":"10.0.0","domains":list(DOMAINS),"wordpress_pages":list(PAGES),"production_certified":False,"writes_enabled":False,"outbound_enabled":False,"deletion_enabled":False,"federation_enabled":False,"live_data_loaded":False,"promotion_allowed":False,"enabled_forbidden_flags":enabled,"config_safe":not enabled,"pending_production_gates":list(GATES)}
@router.get("/status")
def status(org:UUID=Depends(scope)):
    return {"version":"10.0.0","organization_id":str(org),"staging":True,"production_certified":False,"writes_enabled":False,"outbound_enabled":False,"deletion_enabled":False,"federation_enabled":False}
@router.get("/catalog")
def catalog(org:UUID=Depends(scope)):
    return {"organization_id":str(org),"staging":True,"domains":[{"name":d,"prefix":"/v1/"+d,"live_data_connected":False} for d in DOMAINS],"wordpress_pages":list(PAGES)}
@router.get("/readiness")
def readiness(org:UUID=Depends(scope)):
    report=snapshot();return {"organization_id":str(org),"report":report,"sha256":digest(report),"independently_certified":False}
@router.post("/consolidation-preview")
def preview(payload:Preview,org:UUID=Depends(scope)):
    if len(set(payload.domains))!=len(payload.domains) or any(d not in DOMAINS for d in payload.domains):raise HTTPException(422,"Invalid or duplicate domain")
    report={"selected_domains":payload.domains or list(DOMAINS),"preview_only":True,"writes_enabled":False,"outbound_enabled":False,"deletion_enabled":False,"federation_enabled":False,"human_approval_required":True}
    return {"organization_id":str(org),"report":report,"sha256":digest(report),"persisted":False}
@router.post("/commit")
@router.post("/promote")
@router.post("/enable-live")
def deny(org:UUID=Depends(scope)):raise HTTPException(503,"Unified production operations disabled")
