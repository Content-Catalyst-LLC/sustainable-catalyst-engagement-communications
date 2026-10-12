# Sustainable Catalyst Engagement & Communications v9.0.0

**Human Authentication, Sessions & Authorization — opt-in staged backend foundation**

- New `backend/app/human_auth.py`: OIDC authorization code + PKCE S256, signed ID-token validation using trusted JWKS, issuer/audience/nonce, state-bound callback and single-use state.
- Random opaque HttpOnly Secure `__Host-` session cookies, hashed server-side session identifiers; CSRF same-origin enforcement, logout and revoke-all operations.
- Server-controlled allowlisted role/organization mapping with explicit authorization-check endpoint, deny-by-default.
- No human session connection to legacy service-principal data-write endpoints; no password database, no public browser service token.
- Disabled by default. DB migration: none; production writes remain disabled.
- Human IdP, cookies through real HTTPS, operational tenant isolation and HA session backing require acceptance before production certification.
- Existing WordPress plugin v8.8.2 and frontend v8.7.0 remain unchanged.
