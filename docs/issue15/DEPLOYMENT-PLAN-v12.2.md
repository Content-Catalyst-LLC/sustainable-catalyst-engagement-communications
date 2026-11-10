# Version-pinned deployment and phased activation proposal

2026-10-28 — **PREPARATION ONLY. NO-GO for production.** Read with the seven-gate assessment, security review, backup/rollback plan and owner-review privacy/OIDC drafts. No commands in this document have been executed against production unless explicitly identified as read-only evidence elsewhere.

## Identities and architecture

Owner-selected integrated baseline: `baf31877c01e525b610a87830bb0165376ab16e3` (v12.2.0). Proposed bootstrap correction is a separate review commit on `codex/issue15-postgres-bootstrap-fix`; it is not the merged baseline. Owner must select a reviewed replacement SHA before any future migration. No automatic merge or substitution.

Existing production backend: `/opt/scec-v860/repository/backend`, systemd `scec-v860`, loopback 8816, source `280c6b9516f9a9cafca0682f7656964077367d7d`, reports v8.6.0. Keep all earlier SCEC units untouched. Static frontend `scec-engagement-web-v870`, loopback 8097, source `35b5ac363fdebd471f94d8092e943722bc7267e3`, immutable image `sha256:04e8fe6b7cc4701fb4cba71cb6a2891fa095dc54df17dd6a7bfbc7012f199652`. Public `engagement.sustainablecatalyst.com` currently proxies to that frontend, with no API mapping. Homepage/WordPress resides on a different host; its Contact and Engagement Release Console entry has not been mapped to SCEC runtime identity.

Preserve backend systemd + venv and frontend Docker architecture. Candidate frontend Compose reuses the production name and port; never run `docker compose up` from that checkout against production. No backend-container rewrite or moving unrelated services.

## Stage 0: preparation, no exposure

Prerequisites: seven gates closed, protected-page destination resolved, approved exact SHA, reviewed session/principal/CSRF integration, explicit bound/read-only configuration, limits and route allowlist, verified backup/independent restore/rollback, administrator execution access, approved maintenance/change window and rollback operator. These are currently missing. No production directory, account, unit, credential, proxy or DNS change is authorized by this draft.

Future installation commands, **only after separate approval**, using the existing account and a new unused directory:

```bash
# Root operator first confirms /opt/scec-v1220 does not exist and capacity is adequate.
sudo install -d -m 0750 -o catalystadmin -g catalystadmin /opt/scec-v1220
# As catalystadmin, choose the OWNER-APPROVED immutable SHA, not an evolving branch.
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1220/repository
git -C /opt/scec-v1220/repository checkout --detach "$APPROVED_SHA"
test "$(git -C /opt/scec-v1220/repository rev-parse HEAD)" = "$APPROVED_SHA"
test -z "$(git -C /opt/scec-v1220/repository status --porcelain)"
python3.12 -m venv /opt/scec-v1220/repository/backend/.venv
/opt/scec-v1220/repository/backend/.venv/bin/python -m pip install -r /opt/scec-v1220/repository/backend/requirements-lock-v1130.txt
/opt/scec-v1220/repository/backend/.venv/bin/python -m pip check
```

OS interpreter and platform-wheel hashes must be recorded, not assumed from the dependency pin list. Verify source manifest and original protected files, explicitly documenting the one proposed migration correction. Never copy production secrets into staging. Production unit configuration must be created by its authorized operator in a new restricted file; do not source secret env into a logged shell.

Proposed **new** `scec-v1220.service` keeps working directory `/opt/scec-v1220/repository/backend`, `User=catalystadmin`, new `EnvironmentFile=/etc/sustainable-catalyst/engagement/v1220.env`, `PYTHONPATH=.`, uvicorn `--host 127.0.0.1 --port 18822`. Port 18822 is a **proposal, not a verified reservation**; abort if occupied. Preserve old unit and all its files. New environment requires `SCEC_ENV=production`, `SCEC_IDENTITY_MODE=bound`, and production secrets provisioned outside Git. Keep persistence/human login/outbound/subscriptions/scheduling/deletion/federation and every staging feature flag 0. Omit any database URL while persistence is disabled. Configure no legacy auth fallback. Current source does not itself enforce every proposed deployment safeguard; review and test the complete profile before installation.

Installing/enabling/starting that unit (`sudo systemctl daemon-reload`, `sudo systemctl start scec-v1220`) requires separate explicit approval. Do not enable it at boot before approved verification. No migration command belongs in Stage 0. A health-only new process is not production certification or authorization for any preview.

## Stage 1: authenticated read-only research previews

Requires **all seven gates**, reviewed user-session-to-principal integration and explicit owner go/no-go. Existing cookie login does not authorize service-Bearer routes. Never embed a service key in the browser. Research/newsroom/citation/feed previews currently consume synthetic contracts; their certification is not permission to publish real research or accept private data.

Before a proxy change, produce an exact narrow Caddy diff for the approved route allowlist and same-origin browser integration, validate it, and compare expected running configuration hash against the signed approval. Current whole-config baseline is `d967dbb094a392cdf8f94e17881f2b3ac029f3c4e3295bc7d84d6fcaeb296f2b`. If another project changes Caddy, stop and rebase the narrow diff; never overwrite its work. Frontend CSP currently forbids API connections, so no invented ready-to-run cutover command is supplied while the integration is unimplemented. Keep WordPress forms/shortcodes/pages unchanged unless their exact diff receives separate approval.

After approved change, verify public certificate/hostname, authenticated API content type/version, server-side SHA/image identity, unauthorized rejection, role and tenant negatives, CSRF/session expiry/revocation, five destination flows, no write/transport activity, and rollback trigger metrics. `/v1/contracts/canonical` returning HTML 200 is a failure. Record approvals and observations with timestamps. On failure, execute only the approved SCEC rollback diff, not a wholesale restore of a concurrently edited proxy.

## Stages 2 and 3 remain separate

Stage 2 real subscriptions/outbound requires privacy/operator approval, verified consent/withdrawal/unsubscribe/suppression, sender/domain/deliverability/bounce/rate/retry/queue tests and separate explicit authorization for recipients and external sending. No mail transport, scheduler, real subscriber or outbound API is enabled by this plan.

Stage 3 other persistent interactions, partners, events, analytics, deletion or federation require their specific data, security, recovery and owner approvals. No production PostgreSQL migration until fresh initialization and existing-schema upgrade compatibility plus backup restoration have passed on the chosen SHA. No live automatic deletion or destructive downgrade.

## Concrete approval boundary

**No production approval is requested now: mandatory gates remain open.** A future scoped request must list the final source/runtime identities, exact unit/config/proxy diff hashes, backup destination and key custodian, backup/restore commands and evidence, free port, start/reload operations, allowed feature flags/routes, test accounts, rollback commands/operator and maintenance impact. Backup permission does not imply writer pause, deployment, publication or sending permission. Do not reuse earlier WXR approvals for SCEC.
