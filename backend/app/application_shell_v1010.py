"""v10.1 read-only shell contract. Bound service identity only; no browser access or mutations."""
import os
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from .identity import Principal, principal, bound_mode, tenant_for_principal

router=APIRouter(prefix="/v1/application-shell",tags=["application-shell-staging"])
ROUTES=("overview","contacts","engagement","support","advisory","activity","access","communications","analytics","governance","federation","assurance")
PAGES=("Contact","Feedback","Feature Suggestions","Channel","Support")

def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv("SCEC_SHELL_STAGING_ENABLED","0")!="1":raise HTTPException(503,"Shell staging disabled")
    if not bound_mode():raise HTTPException(503,"Bound identity required")
    org=tenant_for_principal(x_scec_organization_id,actor)
    if str(org) not in {s.strip() for s in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS","").split(",") if s.strip()}:raise HTTPException(403,"Tenant not allowlisted")
    if not actor.roles.intersection({"administrator","service"}):raise HTTPException(403,"Role not authorized")
    return org

@router.get("/status")
def status(org:UUID=Depends(scope)):
    return {"version":"10.1.0","organization_id":str(org),"staging":True,"read_only":True,"live_data_connected":False,"production_certified":False}

@router.get("/navigation")
def navigation(org:UUID=Depends(scope)):
    return {"version":"10.1.0","organization_id":str(org),"routes":[{"id":r,"href":"#"+r} for r in ROUTES],"wordpress_pages":list(PAGES),"read_only":True,"live_data_connected":False}

@router.post("/commit")
@router.post("/enable-live")
def deny(org:UUID=Depends(scope)):
    raise HTTPException(503,"Production shell mutations disabled")
