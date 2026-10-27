import os
import time
from uuid import UUID
from pathlib import Path
import jwt
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from app.main import app
from app.identity_certification_v1020 import GATES, report, safety_snapshot
from app.session_security_checks_v1020 import verify_oidc_fixture, verify_boundary, verify_csrf_fixture, session_valid_fixture

ORG = UUID("00000000-0000-0000-0000-000000000001")
ROOT = Path(__file__).resolve().parents[2]

@pytest.fixture(scope="module")
def keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return private, public

def token(key, **changes):
    now = int(time.time())
    payload = dict(iss="https://example.test/oidc", aud="synthetic-client", exp=now+120,
                   iat=now-2, nbf=now-2, sub="synthetic-subject")
    payload.update(changes)
    return jwt.encode(payload, key, algorithm="RS256")

def check(tok, public):
    return verify_oidc_fixture(tok, public, "https://example.test/oidc", "synthetic-client")

def test_good_signed_fixture(keys):
    assert check(token(keys[0]), keys[1])["signature_verified"]

def test_invalid_signature(keys):
    other = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    p = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    with pytest.raises(jwt.PyJWTError):check(token(p), keys[1])

def test_wrong_issuer(keys):
    with pytest.raises(jwt.PyJWTError):check(token(keys[0],iss="https://evil.test"),keys[1])

def test_wrong_audience(keys):
    with pytest.raises(jwt.PyJWTError):check(token(keys[0],aud="other"),keys[1])

def test_expired(keys):
    with pytest.raises(jwt.PyJWTError):check(token(keys[0],exp=int(time.time())-20),keys[1])

def test_future_nbf(keys):
    with pytest.raises(jwt.PyJWTError):check(token(keys[0],nbf=int(time.time())+600),keys[1])

def test_alg_none_rejected(keys):
    fake=jwt.encode(dict(iss="https://example.test/oidc",aud="synthetic-client",exp=int(time.time())+120,iat=int(time.time()),nbf=int(time.time()),sub="x"), key="",algorithm="none")
    with pytest.raises(jwt.PyJWTError):check(fake,keys[1])

def test_missing_iat(keys):
    now=int(time.time()); bare=dict(iss="https://example.test/oidc",aud="synthetic-client",exp=now+120,nbf=now,sub="x")
    with pytest.raises(jwt.PyJWTError):check(jwt.encode(bare,keys[0],algorithm="RS256"),keys[1])

def test_tenant_role_boundary():
    assert verify_boundary(str(ORG),str(ORG),{"administrator"},"administrator")
    assert not verify_boundary(str(ORG),"00000000-0000-0000-0000-000000000002",{"administrator"},"administrator")
    assert not verify_boundary(str(ORG),str(ORG),{"viewer"},"administrator")
    assert not verify_boundary(str(ORG),"not-a-uuid",{"administrator"},"administrator")

def test_csrf_fixture():
    csrf="s"*48
    assert verify_csrf_fixture(csrf,csrf,"https://example.test","https://example.test")
    assert not verify_csrf_fixture(csrf,"z"*48,"https://example.test","https://example.test")
    assert not verify_csrf_fixture(csrf,csrf,"https://malicious.test","https://example.test")
    assert not verify_csrf_fixture("short","short","https://example.test","https://example.test")

def test_revocation_expiration():
    now=int(time.time())
    assert session_valid_fixture(now+60,False,now)
    assert not session_valid_fixture(now+60,True,now)
    assert not session_valid_fixture(now,False,now)
    assert not session_valid_fixture(now-1,False,now)

def test_report_never_certifies():
    a=report(ORG); b=report(ORG)
    assert a==b and a["production_certified"] is False
    assert len(GATES)==7 and all(x=="not-live-certified" for x in a["gate_status"].values())

def test_configuration_flags_fail_closed(monkeypatch):
    for k in ("SCEC_PERSISTENCE_ENABLED","SCEC_OUTBOUND_ENABLED","SCEC_DELETION_ENABLED","SCEC_FEDERATION_ENABLED","SCEC_HUMAN_AUTH_ENABLED"):
        monkeypatch.setenv(k,"1")
    r=report(ORG)
    assert not r["staging_safe"] and not r["production_certified"]
    assert not any(r["safety_flags_disabled"].values())

def test_endpoint_default_gate(monkeypatch):
    monkeypatch.setenv("SCEC_IDENTITY_CERT_STAGING_ENABLED","0")
    c=TestClient(app)
    for method,path in [("get","status"),("get","requirements"),("post","certify"),("post","promote"),("post","enable-login"),("post","enable-writes")]:
        assert getattr(c,method)("/v1/identity-certification/"+path).status_code in (401,403,503)

def test_existing_auth_is_not_auto_enabled():
    source=(ROOT/"backend/app/human_auth.py").read_text()
    assert "SCEC_HUMAN_AUTH_ENABLED" in source and "SESSION_COOKIE" in source
    assert "require_csrf" in source and "DELETE FROM sessions" in source

def test_release_and_wordpress_untouched():
    assert TestClient(app).get("/health").json()["version"]=="11.3.0"
    manifest=(ROOT/"RELEASE-MANIFEST.json").read_text()
    assert '"actual_federation_enabled": false' in manifest
    assert '"production_writes_enabled": false' in manifest
