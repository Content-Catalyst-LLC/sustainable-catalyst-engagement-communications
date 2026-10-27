"""Shared existing-service gates for bounded offline preview modules; no transport."""
import hashlib
import json
import os
from uuid import UUID
from fastapi import Depends, Header, HTTPException
from .identity import Principal, bound_mode, principal, tenant_for_principal
from .newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
from .production_acceptance_v1090 import GATES

DISABLED = ('publication_authorized','actual_publication_enabled','actual_syndication_enabled',
            'outbound_communications_enabled','scheduled_delivery_enabled','persisted',
            'source_fetch_performed','human_login_enabled','deletion_enabled','federation_enabled',
            'token_exchange_enabled','production_writes_enabled','production_certified')


def scope(flag):
    def require(x_scec_organization_id: str | None = Header(default=None), actor: Principal | None = Depends(principal)):
        if os.getenv(flag,'0')!='1' or any(os.getenv(k,'0')!='0' for k in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS)):
            raise HTTPException(503,'Offline staging disabled')
        if not bound_mode(): raise HTTPException(503,'Bound service identity required')
        tenant=tenant_for_principal(x_scec_organization_id,actor)
        if str(tenant) not in {v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}:
            raise HTTPException(403,'Tenant not allowlisted')
        if 'administrator' not in actor.roles: raise HTTPException(403,'Privileged role required')
        return tenant
    return require


def seal(document, tenant, release):
    if str(UUID(tenant))!=tenant:raise ValueError('Canonical tenant required')
    evidence={k:v for k,v in document.items() if k not in {'sha256','release','organization_id',*DISABLED,'live_acceptance_gates_pending'}}
    evidence.update(release=release,organization_id=tenant,**{key:False for key in DISABLED},live_acceptance_gates_pending=list(GATES))
    raw=json.dumps(evidence,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    return {**evidence,'sha256':hashlib.sha256(raw.encode()).hexdigest()}
