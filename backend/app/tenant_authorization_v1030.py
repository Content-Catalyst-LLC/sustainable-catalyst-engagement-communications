"""v10.3 staging-only tenant/permission certification; zero persistence and federation."""
import hashlib
import json
import os
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from .identity import Principal, principal, bound_mode, tenant_for_principal, POLICY

router = APIRouter(prefix="/v1/tenant-authorization", tags=["tenant-authorization-staging"])
GATES = ("cross_tenant_read_denial", "cross_tenant_write_denial", "role_least_privilege", "confused_deputy_actor_reference", "tenant_header_integrity", "bound_service_principal", "denied_request_non_disclosure")
DANGER_FLAGS = {"production_writes":"SCEC_PERSISTENCE_ENABLED", "outbound":"SCEC_OUTBOUND_ENABLED", "deletion":"SCEC_DELETION_ENABLED", "federation":"SCEC_FEDERATION_ENABLED", "human_login":"SCEC_HUMAN_AUTH_ENABLED"}

def authorize_fixture(*, principal_org: str, requested_org: str, roles: frozenset[str], permission: str) -> bool:
    """Pure least-privilege policy check for synthetic testing only. Never grants a live authorization."""
    try:
        if not isinstance(principal_org,str) or not isinstance(requested_org,str):return False
        p=UUID(principal_org);q=UUID(requested_org)
        if str(p)!=principal_org or str(q)!=requested_org or p!=q:return False
        if not isinstance(roles,frozenset) or not roles or not all(isinstance(r,str) for r in roles):return False
        if permission not in POLICY:return False
        return bool(roles.intersection(POLICY[permission]))
    except (ValueError,TypeError,AttributeError):
        return False

def actor_reference_fixture(*, principal_subject:str, requested_subject:str)->bool:
    return isinstance(principal_subject,str) and bool(principal_subject) and len(principal_subject)<=120 and principal_subject==requested_subject

def safety_snapshot():
    disabled={name:os.getenv(flag,"0")=="0" for name,flag in DANGER_FLAGS.items()}
    return {"staging_safe":all(disabled.values()),"safety_flags_disabled":disabled}

def report(org:UUID):
    payload={"release":"10.3.0","organization_id":str(org),"source_evidence":"synthetic-fixture-and-static-contract-only","gate_status":{g:"not-live-certified" for g in GATES},"production_certified":False,"production_writes_enabled":False,"actual_federation_enabled":False,**safety_snapshot()}
    payload["report_sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    return payload

# Staging certification only: require bound identity, tenant/header agreement,
# explicit organization allowlist and an administrative role. Passing this
# dependency permits inspection of a synthetic report, not production tenant
# promotion or writes; the mutation-like routes below remain disabled.
def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv("SCEC_TENANT_CERT_STAGING_ENABLED","0")!="1":raise HTTPException(503,"Tenant authorization staging disabled")
    if not bound_mode():raise HTTPException(503,"Bound principal mode required")
    org=tenant_for_principal(x_scec_organization_id,actor)
    allow={x.strip() for x in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS","").split(",") if x.strip()}
    if str(org) not in allow:raise HTTPException(403,"Tenant not allowlisted")
    if not actor.roles.intersection({"administrator","service"}):raise HTTPException(403,"Administrative role required")
    return org

@router.get("/status")
def status(org:UUID=Depends(scope)):return report(org)

@router.get("/matrix")
def matrix(org:UUID=Depends(scope)):
    return {"release":"10.3.0","organization_id":str(org),"policy":{p:sorted(r) for p,r in sorted(POLICY.items())},"live_evidence":False,"gates":list(GATES)}

@router.post("/certify")
@router.post("/promote")
@router.post("/enable-live")
@router.post("/commit")
def blocked(org:UUID=Depends(scope)):
    raise HTTPException(503,"Live authorization certification and writes disabled")
