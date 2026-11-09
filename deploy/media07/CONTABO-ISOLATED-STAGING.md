# MEDIA-07 — Contabo isolated listmonk staging operator handoff

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

Inspect the **nonsecret** host bindings and networks without sharing the full environment values. Required: PostgreSQL **no host bind**, listmonk UI **127.0.0.1:18898 only**, Mailpit UI **127.0.0.1:18899 only**, no SMTP port published, network `internal: true`. Do not add an external SMTP URL or mail provider.

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

Only create synthetic `@invalid` addresses; configure Mailpit container as the only testing SMTP target (`mailpit:1025`). With `internal: true`, the staging network must not have external egress. Validate via a test email captured **only** by Mailpit, no real recipients. Test restart, PostgreSQL backup/restore to a disposable DB and no externally published ports.

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
