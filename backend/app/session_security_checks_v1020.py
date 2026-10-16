"""Pure v10.2 offline identity contract checks for synthetic fixtures only.
No production JWTs or session cookies should be submitted through HTTP.
"""
import hmac
import time
from uuid import UUID
import jwt

ALGORITHMS = ("RS256",)

def verify_oidc_fixture(token: str, public_key: str, issuer: str, audience: str, now: int | None = None) -> dict:
    """Verify asymmetric signature, issuer, audience, exp/iat/nbf using synthetic fixtures."""
    if not token or len(token) > 8192:
        raise ValueError("Invalid fixture")
    opts = {"require": ["iss", "aud", "exp", "iat", "nbf", "sub"]}
    kwargs = {"algorithms": list(ALGORITHMS), "issuer": issuer,
              "audience": audience, "options": opts, "leeway": 0}
    if now is not None:
        # PyJWT uses current time internally; test with genuine present/future fixtures.
        raise ValueError("Clock override is not supported")
    claims = jwt.decode(token, public_key, **kwargs)
    if not isinstance(claims.get("sub"), str) or not (1 <= len(claims["sub"]) <= 200):
        raise ValueError("Invalid subject")
    return {"subject_validated": True, "signature_verified": True,
            "issuer_verified": True, "audience_verified": True}

def verify_boundary(expected_tenant: str, requested_tenant: str, roles: set[str], required_role: str) -> bool:
    try:
        same_tenant = hmac.compare_digest(str(UUID(expected_tenant)), str(UUID(requested_tenant)))
    except (ValueError, AttributeError, TypeError):
        return False
    return same_tenant and required_role in roles

def verify_csrf_fixture(header_token: str, cookie_token: str, request_origin: str, expected_origin: str) -> bool:
    if not (isinstance(header_token, str) and isinstance(cookie_token, str)
            and isinstance(request_origin, str) and isinstance(expected_origin, str)):
        return False
    if len(header_token) < 32 or len(cookie_token) < 32 or len(header_token) > 256:
        return False
    return hmac.compare_digest(header_token, cookie_token) and hmac.compare_digest(request_origin, expected_origin)

def session_valid_fixture(expires: int, revoked: bool, now: int | None = None) -> bool:
    now = int(time.time()) if now is None else now
    return not revoked and isinstance(expires, int) and expires > now
