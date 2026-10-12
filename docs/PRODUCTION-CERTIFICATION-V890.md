# v8.9.0 Production Certification Boundary

**Status: preflight build, not full production certification.** The `certification/certify.py` script verifies source contracts and, optionally, local service connectivity using read-only requests. It cannot prove enterprise readiness.

| Gate | Requirement | Status from package |
| --- | --- | --- |
| Source/version consistency | Pin backend 8.6.0, frontend 8.7.0 and bridge 8.8.2 | Automated |
| WordPress independence | Preserve Contact, Feedback, Feature Suggestions, Channel and Support | Automated static guard |
| Static security headers | Deny frames, no browser API requests | Automated static guard |
| Loopback services | Frontend :8097 / backend :8816 and unauthenticated 401 | Contabo live preflight required |
| DB integrity | Existing `850_001`; pre/post backups already handled in prior release | No migration |
| Public hostname | HTTPS certificate, redirects, headers, DNS | Not certified |
| Auth sessions | Signed-in human identity, cookies, CSRF, revocation | Not implemented/certified |
| Data isolation | Real tenant scope & denied cross-tenant access | Not certified |
| Privacy | Retention/deletion and policy acceptance | Not certified |
| Production data | Reversible and audited data operations | Disabled |

**Do not send personal customer information to the public preview.** Do not embed credentials in WordPress or client JS. The signed service-principal credentials are not browser user authentication.
