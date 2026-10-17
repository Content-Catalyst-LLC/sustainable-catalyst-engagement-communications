import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.transaction_foundation_v1040 import ephemeral_database,write_fixture,read_fixture,status_report,safety_state

TENANT_A=str(uuid4())
TENANT_B=str(uuid4())

def test_atomic_commit():
    with ephemeral_database() as db:
        result=write_fixture(db,tenant=TENANT_A,key="record",value="v1",request_id="req1",expected_revision=0)
        assert result["revision"]==1
        assert len(result["audit_digest"])==64
        assert read_fixture(db,tenant=TENANT_A,key="record")== (1,"v1")

def test_rollback_is_atomic():
    with ephemeral_database() as db:
        with pytest.raises(RuntimeError):write_fixture(db,tenant=TENANT_A,key="record",value="v1",request_id="req1",fail_after_insert=True)
        assert read_fixture(db,tenant=TENANT_A,key="record") is None
        assert db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM dedupe").fetchone()[0]==0

def test_cross_tenant_read_and_write_are_isolated():
    with ephemeral_database() as db:
        write_fixture(db,tenant=TENANT_A,key="shared",value="secret-a",request_id="id1")
        assert read_fixture(db,tenant=TENANT_B,key="shared") is None
        write_fixture(db,tenant=TENANT_B,key="shared",value="secret-b",request_id="id1")
        assert read_fixture(db,tenant=TENANT_A,key="shared")== (1,"secret-a")
        assert read_fixture(db,tenant=TENANT_B,key="shared")== (1,"secret-b")

def test_idempotent_replay_no_duplicate_audit():
    with ephemeral_database() as db:
        first=write_fixture(db,tenant=TENANT_A,key="k",value="v",request_id="key")
        second=write_fixture(db,tenant=TENANT_A,key="k",value="v",request_id="key")
        assert first["replayed"] is False and second=={"replayed":True,"revision":1}
        assert db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]==1

def test_idempotency_key_reuse_conflict_rolls_back():
    with ephemeral_database() as db:
        write_fixture(db,tenant=TENANT_A,key="k",value="v",request_id="key")
        with pytest.raises(ValueError,match="Idempotency conflict"):
            write_fixture(db,tenant=TENANT_A,key="k",value="changed",request_id="key")
        assert read_fixture(db,tenant=TENANT_A,key="k")== (1,"v")

def test_revision_conflicts():
    with ephemeral_database() as db:
        write_fixture(db,tenant=TENANT_A,key="k",value="v",request_id="1",expected_revision=0)
        with pytest.raises(ValueError,match="Revision conflict"):
            write_fixture(db,tenant=TENANT_A,key="k",value="v2",request_id="2",expected_revision=0)
        assert read_fixture(db,tenant=TENANT_A,key="k")== (1,"v")

def test_revision_increment():
    with ephemeral_database() as db:
        write_fixture(db,tenant=TENANT_A,key="k",value="v",request_id="1",expected_revision=0)
        assert write_fixture(db,tenant=TENANT_A,key="k",value="v2",request_id="2",expected_revision=1)["revision"]==2

def test_noncanonical_and_invalid_tenants():
    with ephemeral_database() as db:
        for bad in ["invalid", TENANT_A.upper(),"",None]:
            if bad==TENANT_A:continue
            with pytest.raises((ValueError,TypeError,AttributeError)):
                write_fixture(db,tenant=bad,key="k",value="v",request_id="1")

def test_bad_fields_rejected():
    with ephemeral_database() as db:
        for key,request_id,value in [("","1","v"),("k","","v"),("k","1",None),("k","1","x"*4097)]:
            with pytest.raises(ValueError):write_fixture(db,tenant=TENANT_A,key=key,value=value,request_id=request_id)

def test_invalid_expected_revision_rejected():
    with ephemeral_database() as db:
        with pytest.raises(ValueError):write_fixture(db,tenant=TENANT_A,key="k",value="v",request_id="1",expected_revision=True)

def test_audit_chain_changes_deterministically():
    with ephemeral_database() as db:
        a=write_fixture(db,tenant=TENANT_A,key="a",value="v",request_id="1")
        b=write_fixture(db,tenant=TENANT_A,key="b",value="v",request_id="2")
        assert a["audit_digest"]!=b["audit_digest"]
        assert db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]==2

def test_status_never_claims_live_certification():
    obj=status_report(TENANT_A)
    assert obj["production_certified"] is False and obj["production_writes_enabled"] is False
    assert obj["external_database_used"] is False
    assert len(obj["sha256"])==64

def test_disabled_endpoint():
    os.environ.pop("SCEC_TRANSACTION_STAGING_ENABLED",None)
    res=TestClient(app).get("/v1/transaction-foundation/status")
    assert res.status_code in (401,503)

def test_disabled_commit_endpoint():
    os.environ.pop("SCEC_TRANSACTION_STAGING_ENABLED",None)
    res=TestClient(app).post("/v1/transaction-foundation/commit")
    assert res.status_code in (401,503)

def test_gates_default_to_disabled(monkeypatch):
    for key in ("SCEC_HUMAN_AUTH_ENABLED","SCEC_PERSISTENCE_ENABLED","SCEC_OUTBOUND_ENABLED","SCEC_DELETION_ENABLED","SCEC_FEDERATION_ENABLED"):
        monkeypatch.delenv(key,raising=False)
    assert all(safety_state().values())

def test_rehearsal_does_not_touch_production(monkeypatch):
    monkeypatch.setenv("DATABASE_URL","postgresql://invalid/not-a-db")
    with ephemeral_database() as db:
        write_fixture(db,tenant=TENANT_A,key="k",value="v",request_id="1")
        assert read_fixture(db,tenant=TENANT_A,key="k")== (1,"v")
