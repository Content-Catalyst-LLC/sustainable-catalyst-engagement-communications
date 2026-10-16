"""v10.2 staging-only identity/session certification surface.

No login, JWT ingestion, session mutation, network calls, DB access, or live credentials.
Production sign-off requires independently witnessed tests and explicit approval.
"""
import hashlib
import json
import os
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from .identity import Principal, principal, bound_mode, tenant_for_principal

router = APIRouter(prefix="/v1/identity-certification", tags=["identity-certification-staging"])
GATES = (
    "oidc_signature_issuer_audience",
    "pkce_state_nonce_replay",
    "session_expiry_revocation_logout",
    "csrf_origin_enforcement",
    "tenant_membership_isolation",
    "role_permission_boundaries",
    "public_https_browser_acceptance",
)
CONTROLS = (
    "production_writes", "outbound_messaging", "deletion", "federation",
    "live_human_authentication",
)

def stage_scope(x_scec_organization_id: str | None = Header(default=None),
                actor: Principal | None = Depends(principal)) -> UUID:
    if os.getenv("SCEC_IDENTITY_CERT_STAGING_ENABLED", "0") != "1":
        raise HTTPException(503, "Identity certification staging disabled")
    if not bound_mode():
        raise HTTPException(503, "Bound identity required")
    org = tenant_for_principal(x_scec_organization_id, actor)
    allow = {x.strip() for x in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS", "").split(",") if x.strip()}
    if str(org) not in allow:
        raise HTTPException(403, "Tenant not allowlisted")
    if not actor.roles.intersection({"administrator", "service"}):
        raise HTTPException(403, "Administrator or service role required")
    return org

def safety_snapshot() -> dict:
    """Observe only configured flags; a clean staging posture is not certification."""
    flags = {
        "production_writes": "SCEC_PERSISTENCE_ENABLED",
        "outbound_messaging": "SCEC_OUTBOUND_ENABLED",
        "deletion": "SCEC_DELETION_ENABLED",
        "federation": "SCEC_FEDERATION_ENABLED",
        "live_human_authentication": "SCEC_HUMAN_AUTH_ENABLED",
    }
    disabled = {name: os.getenv(env, "0") == "0" for name, env in flags.items()}
    return {"safety_flags_disabled": disabled, "staging_safe": all(disabled.values()),
            "requires_independent_live_evidence": True}

def report(org: UUID) -> dict:
    snap = safety_snapshot()
    payload = {"release": "10.2.0", "organization_id": str(org),
        "source_verification": "automated-regression-only",
        "gate_status": {gate: "not-live-certified" for gate in GATES},
        "production_certified": False,
        "production_writes_enabled": False,
        "live_authentication_enabled_by_release": False,
        **snap}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["report_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    return payload

@router.get("/status")
def status(org: UUID = Depends(stage_scope)):
    return report(org)

@router.get("/requirements")
def requirements(org: UUID = Depends(stage_scope)):
    return {"release": "10.2.0", "organization_id": str(org),
            "required_evidence": list(GATES), "live_certification": False,
            "test_scope": "offline-regression-and-staging-configuration-only"}

@router.post("/certify")
@router.post("/promote")
@router.post("/enable-login")
@router.post("/enable-writes")
def disabled(org: UUID = Depends(stage_scope)):
    raise HTTPException(503, "Live identity certification and activation disabled")
