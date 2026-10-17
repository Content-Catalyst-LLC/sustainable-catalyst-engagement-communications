"""Ephemeral transaction rehearsal only. No production database, files or external transport."""
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from .identity import Principal, bound_mode, principal, tenant_for_principal

router = APIRouter(prefix="/v1/transaction-foundation", tags=["transaction-staging"])
GATES = ("atomic_commit", "rollback_on_error", "tenant_scoped_reads", "tenant_scoped_writes", "idempotency", "optimistic_conflict", "audit_chain", "no_production_connection")
DANGER_FLAGS = ("SCEC_HUMAN_AUTH_ENABLED", "SCEC_PERSISTENCE_ENABLED", "SCEC_OUTBOUND_ENABLED", "SCEC_DELETION_ENABLED", "SCEC_FEDERATION_ENABLED")

@contextmanager
def ephemeral_database():
    """Synthetic in-memory database; must never accept a production DSN."""
    db = sqlite3.connect(":memory:", isolation_level=None)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("CREATE TABLE record (tenant TEXT NOT NULL, key TEXT NOT NULL, revision INTEGER NOT NULL, value TEXT NOT NULL, PRIMARY KEY(tenant,key))")
        db.execute("CREATE TABLE dedupe (tenant TEXT NOT NULL, request_id TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(tenant,request_id))")
        db.execute("CREATE TABLE audit (sequence INTEGER PRIMARY KEY, tenant TEXT NOT NULL, action TEXT NOT NULL, digest TEXT NOT NULL)")
        yield db
    finally:
        db.close()

def _canonical_tenant(value):
    if not isinstance(value,str): raise ValueError("Tenant must be canonical UUID")
    parsed=UUID(value)
    if str(parsed)!=value:raise ValueError("Noncanonical tenant")
    return value

def write_fixture(db, *, tenant, key, value, request_id, expected_revision=None, fail_after_insert=False):
    """Single atomic rehearsal; idempotency key scoped per tenant, never changes production state."""
    tenant=_canonical_tenant(tenant)
    if not all(isinstance(x,str) and 0<len(x)<=128 for x in (key,request_id)):raise ValueError("Invalid key")
    if not isinstance(value,str) or len(value)>4096:raise ValueError("Invalid value")
    payload=json.dumps({"key":key,"value":value,"expected_revision":expected_revision},sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(payload.encode()).hexdigest()
    db.execute("BEGIN IMMEDIATE")
    try:
        previous=db.execute("SELECT digest FROM dedupe WHERE tenant=? AND request_id=?",(tenant,request_id)).fetchone()
        if previous:
            if previous[0]!=digest:raise ValueError("Idempotency conflict")
            row=db.execute("SELECT revision,value FROM record WHERE tenant=? AND key=?",(tenant,key)).fetchone()
            db.execute("COMMIT")
            return {"replayed":True,"revision":row[0] if row else None}
        existing=db.execute("SELECT revision FROM record WHERE tenant=? AND key=?",(tenant,key)).fetchone()
        revision=existing[0] if existing else 0
        if expected_revision is not None and (type(expected_revision) is not int or expected_revision!=revision):raise ValueError("Revision conflict")
        db.execute("INSERT INTO record(tenant,key,revision,value) VALUES(?,?,?,?) ON CONFLICT(tenant,key) DO UPDATE SET revision=excluded.revision,value=excluded.value", (tenant,key,revision+1,value))
        db.execute("INSERT INTO dedupe(tenant,request_id,digest) VALUES(?,?,?)",(tenant,request_id,digest))
        if fail_after_insert:raise RuntimeError("Synthetic failure injected")
        prior=db.execute("SELECT digest FROM audit ORDER BY sequence DESC LIMIT 1").fetchone()
        prior_digest=prior[0] if prior else "0"*64
        audit_hash=hashlib.sha256((prior_digest+tenant+key+digest).encode()).hexdigest()
        db.execute("INSERT INTO audit(tenant,action,digest) VALUES(?,?,?)",(tenant,"fixture_write",audit_hash))
        db.execute("COMMIT")
        return {"replayed":False,"revision":revision+1,"audit_digest":audit_hash}
    except Exception:
        db.execute("ROLLBACK")
        raise

def read_fixture(db, *, tenant,key):
    tenant=_canonical_tenant(tenant)
    return db.execute("SELECT revision,value FROM record WHERE tenant=? AND key=?",(tenant,key)).fetchone()

def safety_state():
    return {flag:os.getenv(flag,"0")=="0" for flag in DANGER_FLAGS}

def status_report(org):
    report={"release":"10.4.0","organization_id":str(org),"mode":"synthetic-ephemeral-transaction-rehearsal", "gates":{gate:"not-live-certified" for gate in GATES},"safety_flags_disabled":safety_state(),"production_certified":False,"production_writes_enabled":False,"external_database_used":False}
    report["sha256"]=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return report

def _scope(x_scec_organization_id: str|None=Header(default=None), actor: Principal|None=Depends(principal)):
    if os.getenv("SCEC_TRANSACTION_STAGING_ENABLED","0")!="1" or not all(safety_state().values()):raise HTTPException(503,"Transaction staging disabled")
    if not bound_mode():raise HTTPException(503,"Bound service identity required")
    tenant=tenant_for_principal(x_scec_organization_id,actor)
    allowed={x.strip() for x in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS","").split(",") if x.strip()}
    if str(tenant) not in allowed:raise HTTPException(403,"Tenant not allowlisted")
    if not actor.roles.intersection({"administrator","service"}):raise HTTPException(403,"Privileged service role required")
    return tenant

@router.get("/status")
def status(org=Depends(_scope)):return status_report(org)

@router.get("/requirements")
def requirements(org=Depends(_scope)):
    return {"release":"10.4.0","organization_id":str(org),"gates":list(GATES),"synthetic_only":True,"live_evidence":False}

@router.post("/commit")
@router.post("/certify")
@router.post("/promote")
@router.post("/enable-writes")
def blocked(org=Depends(_scope)):
    raise HTTPException(503,"Persistent transactions and promotion are disabled")
