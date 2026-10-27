import pytest
from uuid import UUID
from fastapi.testclient import TestClient
from app.main import app
from app.tenant_authorization_v1030 import authorize_fixture,actor_reference_fixture,report,safety_snapshot,GATES
ORG="00000000-0000-0000-0000-000000000001"
OTHER="00000000-0000-0000-0000-000000000002"
@pytest.mark.parametrize("permission,roles,expected",[("contracts:read",frozenset({"viewer"}),True),("support:read",frozenset({"viewer"}),False),("support:read",frozenset({"support_agent"}),True),("support:write",frozenset({"advisor"}),False),("advisory:approve",frozenset({"approver"}),True),("advisory:write",frozenset({"approver"}),False),("engagement:write",frozenset({"administrator"}),True),("bogus",frozenset({"administrator"}),False),("support:read",frozenset(),False)])
def test_least_privilege(permission,roles,expected):assert authorize_fixture(principal_org=ORG,requested_org=ORG,roles=roles,permission=permission) is expected
@pytest.mark.parametrize("requested",[OTHER,"bad-tenant","","00000000-0000-0000-0000-00000000000A","00000000-0000-0000-0000-000000000000"])
def test_cross_tenant_and_noncanonical_denied(requested):assert not authorize_fixture(principal_org=ORG,requested_org=requested,roles=frozenset({"administrator"}),permission="support:read")
def test_bad_identity_denied():
 assert not authorize_fixture(principal_org="invalid",requested_org=ORG,roles=frozenset({"administrator"}),permission="support:read")
 assert not authorize_fixture(principal_org=ORG,requested_org=ORG,roles={"administrator"},permission="support:read")
def test_actor_spoof_rejected():
 assert actor_reference_fixture(principal_subject="trusted",requested_subject="trusted")
 assert not actor_reference_fixture(principal_subject="trusted",requested_subject="other")
 assert not actor_reference_fixture(principal_subject="",requested_subject="")
def test_deterministic_noncertifying_report():
 a=report(UUID(ORG));assert a==report(UUID(ORG));assert len(GATES)==7
 assert a["production_certified"] is False and all(x=="not-live-certified" for x in a["gate_status"].values())
def test_dangerous_flags_not_certified(monkeypatch):
 for flag in ("SCEC_PERSISTENCE_ENABLED","SCEC_OUTBOUND_ENABLED","SCEC_DELETION_ENABLED","SCEC_FEDERATION_ENABLED","SCEC_HUMAN_AUTH_ENABLED"):monkeypatch.setenv(flag,"1")
 assert safety_snapshot()["staging_safe"] is False
 assert report(UUID(ORG))["production_certified"] is False
@pytest.mark.parametrize("path,method",[("status","get"),("matrix","get"),("certify","post"),("promote","post"),("enable-live","post"),("commit","post")])
def test_staging_default_closed(monkeypatch,path,method):
 monkeypatch.setenv("SCEC_TENANT_CERT_STAGING_ENABLED","0")
 resp=getattr(TestClient(app),method)("/v1/tenant-authorization/"+path)
 assert resp.status_code in (401,403,503)
def test_health_version():assert TestClient(app).get("/health").json()["version"]=="11.5.0"
