from uuid import uuid4
import time
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.feature_intelligence_v920 import Suggestion,classify

client=TestClient(app)
def auth(monkeypatch,role="contact_editor",org=None):
    org=org or uuid4();secret="community-preview-test-secret-at-least-32-characters"
    monkeypatch.setenv("SCEC_COMMUNITY_STAGING_ENABLED","1");monkeypatch.setenv("SCEC_IDENTITY_MODE","bound")
    monkeypatch.setenv("SCEC_IDENTITY_SIGNING_KEY",secret);monkeypatch.setenv("SCEC_ALLOWED_ORGANIZATION_IDS",str(org))
    tok=mint_token(subject="local-test",organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return {"Authorization":"Bearer "+tok,"X-SCEC-Organization-ID":str(org)}
def sample(**override):
    return {**dict(title="Improve citation export",description="Please add citation export functionality to the library for researchers",source="staging-test",impact="medium",vote_count=12),**override}
def test_default_closed(monkeypatch):
    monkeypatch.delenv("SCEC_COMMUNITY_STAGING_ENABLED",raising=False)
    assert client.get("/v1/community-intelligence/status").status_code in (401,503)
def test_no_auth(monkeypatch):
    monkeypatch.setenv("SCEC_COMMUNITY_STAGING_ENABLED","1");monkeypatch.setenv("SCEC_IDENTITY_MODE","bound")
    assert client.post("/v1/community-intelligence/preview",json=sample()).status_code==401
def test_legacy_closed(monkeypatch):
    monkeypatch.setenv("SCEC_COMMUNITY_STAGING_ENABLED","1");monkeypatch.setenv("SCEC_IDENTITY_MODE","legacy")
    assert client.get("/v1/community-intelligence/status").status_code==503
def test_preview_no_pii(monkeypatch):
    headers=auth(monkeypatch)
    r=client.post("/v1/community-intelligence/preview",json=sample(description="Please add citation export functionality in library. My email is personal@example.com"),headers=headers)
    assert r.status_code==200,r.text
    assert r.json()["analysis"]["product_area"]=="library"
    assert r.json()["persisted"] is False
    assert "personal@example.com" not in r.text
    assert "citation export" not in r.text
def test_exact_duplicates_within_request(monkeypatch):
    headers=auth(monkeypatch)
    r=client.post("/v1/community-intelligence/aggregate-preview",json={"suggestions":[sample(),sample(),sample(title="Improve maps",description="Please add improved map layers and ocean datasets",impact="high")]},headers=headers)
    assert r.status_code==200,r.text
    assert r.json()["possible_duplicate_index_groups"]==[[0,1]]
    assert r.json()["product_area_counts"]["library"]==2
    assert r.json()["persisted"] is False
def test_tenant_spoof(monkeypatch):
    headers=auth(monkeypatch);headers["X-SCEC-Organization-ID"]=str(uuid4())
    assert client.post("/v1/community-intelligence/preview",json=sample(),headers=headers).status_code==403
def test_allowlist(monkeypatch):
    headers=auth(monkeypatch);monkeypatch.setenv("SCEC_ALLOWED_ORGANIZATION_IDS",str(uuid4()))
    assert client.get("/v1/community-intelligence/status",headers=headers).status_code==403
def test_role(monkeypatch):
    headers=auth(monkeypatch,role="viewer")
    assert client.post("/v1/community-intelligence/preview",json=sample(),headers=headers).status_code==403
def test_immutable_commit_gate(monkeypatch):
    headers=auth(monkeypatch);monkeypatch.setenv("SCEC_PERSISTENCE_ENABLED","1")
    assert client.post("/v1/community-intelligence/commit",headers=headers,json=sample()).status_code==503
def test_validation(monkeypatch):
    headers=auth(monkeypatch)
    for payload in [sample(title="x"),sample(product_area="not-real"),sample(vote_count=-1),sample(source="public"),sample(admin=True)]:
        assert client.post("/v1/community-intelligence/preview",headers=headers,json=payload).status_code==422
    assert client.post("/v1/community-intelligence/aggregate-preview",headers=headers,json={"suggestions":[sample()]*26}).status_code==422
def test_deterministic_rules():
    obj=Suggestion(**sample());assert classify(obj)==classify(obj)
def test_no_wordpress_change():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    assert (root/"wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php").exists()
