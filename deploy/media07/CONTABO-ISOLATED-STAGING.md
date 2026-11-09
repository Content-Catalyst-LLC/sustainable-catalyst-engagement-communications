# MEDIA-07 — Contabo isolated listmonk staging operator handoff

## Preferred deployment: guarded first-time installer

The reviewed first-time operator script is [deploy-contabo-staging.sh](deploy-contabo-staging.sh). It checks available disk/RAM, occupied ports and preexisting MEDIA-07 containers/volumes; generates unique staging credentials in a protected file outside the Git checkout; enforces Compose's internal network and loopback-only admin proxy; deploys; tests listmonk, Mailpit, a synthetic invalid-recipient message and negative external egress; backs up and restores PostgreSQL in a disposable test DB; and writes a redacted acceptance receipt. **Do not run against an existing MEDIA-07 installation.**

Run this from your **Mac terminal** with already-authorized Contabo SSH access:

```bash
ssh catalystadmin@94.72.113.77 'bash -se' <<'CONTABO'
set -euo pipefail
target="$HOME/media0708-staging-candidate"
if [ -e "$target" ]; then
  echo "Candidate directory already exists; inspect before proceeding." >&2
  exit 1
fi
git clone --single-branch \
  --branch feature/media-08-press-room-and-media07-staging-20261108 \
  https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git \
  "$target"
cd "$target"
bash deploy/media07/deploy-contabo-staging.sh
CONTABO
```

The source repository is publicly readable, so this clone should not require GitHub credentials. Do not paste private SSH keys, env contents or raw Compose config (which may include passwords). On success the script prints the **private acceptance receipt path** under `$HOME/media07-private/receipts/`, and `docker compose ps` shows the four containers. The file is held only on the Contabo server, not uploaded to GitHub or this chat.

**If this chat has no authenticated SSH terminal, this command MUST be run by the authorized operator on their machine; a committed script or GitHub Actions test is not proof of actual Contabo deployment.** Script aborts on low capacity, missing dependencies, existing volumes/ports, nonclean checkout or failed synthetic/backup acceptance. On failure it deliberately retains private volumes for inspection; it never automatically prunes or deletes other services.

Use the rest of this runbook for manual review, recovery, and SSH-tunnel access. Do not independently run the manual startup sequence after the installer succeeds, and never set a real SMTP provider in staging.


**Status:** Source and disposable CI staging candidate. **Not verified deployed on Contabo.** No actual SMTP provider, real subscribers, production migration, or external sends authorized.

## Preconditions (read-only)

Before running any Docker change on the Contabo host, verify host memory/disk capacity and existing binds. Recorded historical observations were approximately 83% disk use and 79% memory use; **fresh observations required**.

```bash
ssh catalystadmin@94.72.113.77
df -h /
free -h
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep -E '(^|:)(18898|18899)(:|->)' || true
docker system df
```

**Do not prune** Docker volumes/images as part of this operation. Existing workloads require independent backup/rollback verification. If disk/RAM headroom or backup path is inadequate, stop.

## Source and secrets (operator-authorized, never paste keys in chat)

Use a separate checked-out *candidate* clone; never replace the production Engagement checkout:

```bash
git clone --branch feature/media-08-press-room-and-media07-staging-20261108 --single-branch \
  https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git \
  "$HOME/media0708-staging-candidate"
cd "$HOME/media0708-staging-candidate"
git rev-parse HEAD
```

Create `$HOME/media07-private/staging.env` with mode `600` in a restricted directory, outside the checkout. It needs **only** `MEDIA07_DB_PASSWORD`, `MEDIA07_ADMIN_USER`, and `MEDIA07_ADMIN_PASSWORD` set to unique staging values. Never put these in GitHub, public URLs, shell commands/history, screenshots, or pasted logs.

## Validate Compose before launching

```bash
cd "$HOME/media0708-staging-candidate"
docker compose --env-file "$HOME/media07-private/staging.env" \
  -f deploy/media07/compose.staging.yml config --quiet
docker compose --env-file "$HOME/media07-private/staging.env" \
  -f deploy/media07/compose.staging.yml config --format json > /tmp/media07-compose-review.json
```

Inspect the **nonsecret** host bindings and networks without sharing the full environment values. Required: PostgreSQL, listmonk, and Mailpit **no direct host bind**, one fixed-purpose `admin_proxy` published at **127.0.0.1:18898** and **127.0.0.1:18899**, no SMTP port published. Private network `internal: true` has no external egress; proxy alone joins a separate admin bridge. Do not add an external SMTP URL or mail provider.

## Authorized isolated staging launch (not run by this handoff)

```bash
docker compose --env-file "$HOME/media07-private/staging.env" \
  -f deploy/media07/compose.staging.yml up -d
docker compose --env-file "$HOME/media07-private/staging.env" \
  -f deploy/media07/compose.staging.yml ps
curl --max-time 5 -I http://127.0.0.1:18898/
curl --max-time 5 -I http://127.0.0.1:18899/
```

For browser inspection from an authorized Mac, use an **SSH tunnel** `ssh -N -L 18898:127.0.0.1:18898 -L 18899:127.0.0.1:18899 catalystadmin@94.72.113.77`, then access localhost ports. Do not route these through public Caddy or WordPress.

Only create synthetic `@invalid` addresses; configure Mailpit container as the only testing SMTP target (`mailpit:1025`). With `internal: true`, the three private services must have no external egress. The loopback-only Caddy proxy is the sole dual-network container, with fixed reverse-proxy upstreams. Validate via a test email captured **only** by Mailpit, no real recipients. Test restart, PostgreSQL backup/restore to a disposable DB and no externally published ports.

## Safe stop and recovery

```bash
docker compose --env-file "$HOME/media07-private/staging.env" \
  -f deploy/media07/compose.staging.yml down
```

The above retains volumes; **never use `down -v` on persistent Contabo staging data without a separately verified backup and explicit destruction approval**. Keep all MEDIA-05, MEDIA-06, Workspace, Research and WordPress services untouched.

## Acceptance receipt

Record: exact source commit, image digests, DB/volume identifiers, capacity before/after, reachable loopback ports, synthetic Mailpit captured message, negative external egress check, tenant/credential access tests, backup+restore proof, stop/rollback. Mark each item PASS / FAIL / BLOCKED / NOT PERFORMED. CI-only ephemeral capture **does not** satisfy Contabo acceptance.

## Next development handoff

Build Python listmonk **draft-only** campaign adapter with authenticated service identity and scoped credentials on Contabo. No editor-provided sender list, scheduling, subscription data export or direct send rights. Substack manual export remains supported.
