#!/usr/bin/env bash
# MEDIA-07 first-time staging installer. Run as catalystadmin ON Contabo.
# Fail closed: never touches an existing MEDIA-07 stack or other deployments.
set -Eeuo pipefail
umask 077

fail() { printf 'MEDIA07 BLOCKED: %s\n' "$*" >&2; exit 1; }
info() { printf 'MEDIA07: %s\n' "$*"; }
trap 'printf "MEDIA07 FAILED at line %s. Partial staging, if any, remains private for inspection; no automatic volume deletion.\n" "$LINENO" >&2' ERR

[[ "$(id -u)" -ne 0 ]] || fail "Run as the ordinary Contabo staging operator, not root."
for dep in docker git python3 openssl curl ss awk df; do
  command -v "$dep" >/dev/null 2>&1 || fail "Missing executable: $dep"
done
docker info >/dev/null 2>&1 || fail "Cannot access Docker daemon."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required."
repo="$(cd -- "$(dirname -- "$0")/../.." && pwd -P)"
cd "$repo"
[[ "$(git branch --show-current)" == "feature/media-08-press-room-and-media07-staging-20261108" ]] ||
  fail "Use the reviewed MEDIA-07/08 staging branch; do not deploy main or another working tree."
[[ -z "$(git status --porcelain)" ]] ||
  fail "Working tree is not clean: keep credentials and generated files outside the checkout."
src_sha="$(git rev-parse HEAD)"
compose="$repo/deploy/media07/compose.staging.yml"
[[ -f "$compose" && -f "$repo/deploy/media07/Caddyfile.staging" ]] ||
  fail "Missing validated Compose or local proxy configuration."

# Preflight capacity and port/volume collisions before creating any credentials.
free_disk_kib="$(df -Pk / | awk 'NR == 2 {print $4}')"
avail_mem_kib="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
[[ "$free_disk_kib" =~ ^[0-9]+$ && "$free_disk_kib" -ge 15728640 ]] ||
  fail "Less than 15 GiB free on /. Review capacity without pruning active services."
[[ "$avail_mem_kib" =~ ^[0-9]+$ && "$avail_mem_kib" -ge 1572864 ]] ||
  fail "Less than 1.5 GiB memory currently available."
[[ -z "$(ss -H -ltn '( sport = :18898 or sport = :18899 )')" ]] ||
  fail "Ports 18898 or 18899 are occupied. Do not replace existing listeners."
[[ -z "$(docker ps -aq --filter label=com.docker.compose.project=sc-media07-staging)" ]] ||
  fail "An existing MEDIA-07 Compose project was detected. Do not overwrite it with first-time installer."
for volume in sc-media07-staging_media07_pg_data sc-media07-staging_media07_uploads sc-media07-staging_media07_mailpit_data; do
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    fail "Existing MEDIA-07 volume $volume: require independent backup/reconcile, not first-time installer."
  fi
done
info "Capacity and collision preflight PASS; disk available (KiB): $free_disk_kib, MemAvailable (KiB): $avail_mem_kib."

private="$HOME/media07-private"
envfile="$private/staging.env"
mkdir -p "$private/backups" "$private/receipts"
chmod 700 "$private" "$private/backups" "$private/receipts"
if [[ ! -e "$envfile" ]]; then
  [[ -x "$(command -v openssl)" ]] || fail "OpenSSL unavailable."
  {
    printf 'MEDIA07_DB_PASSWORD=%s\n' "$(openssl rand -hex 32)"
    printf 'MEDIA07_ADMIN_USER=sc_media07_staging\n'
    printf 'MEDIA07_ADMIN_PASSWORD=%s\n' "$(openssl rand -hex 32)"
  } > "$envfile"
  chmod 600 "$envfile"
  info "Generated unique staging-only credentials in protected env file; values withheld."
fi
[[ -f "$envfile" && "$(stat -c %a "$envfile")" == 600 ]] ||
  fail "Env file must be mode 600. Do not paste its values into logs or chat."
for key in MEDIA07_DB_PASSWORD MEDIA07_ADMIN_USER MEDIA07_ADMIN_PASSWORD; do
  grep -q "^$key=[^[:space:]]" "$envfile" || fail "Required staging env key missing: $key"
done

# Parse rendered Compose privately in memory; never persist resolved secrets to disk/logs.
python3 - "$envfile" "$compose" <<'PY'
import json, subprocess, sys
envfile, path = sys.argv[1:]
cfg = json.loads(subprocess.check_output([
    "docker", "compose", "--env-file", envfile, "-f", path,
    "config", "--format", "json"], stderr=subprocess.DEVNULL))
services = cfg["services"]
assert set(services) == {"db", "listmonk", "mailpit", "admin_proxy"}
assert cfg["networks"]["media07_private"]["internal"] is True
for name in ("db", "listmonk", "mailpit"):
    assert not services[name].get("ports"), name
    nets = services[name]["networks"]
    assert set(nets) == {"media07_private"}, name
proxy = services["admin_proxy"]
assert set(proxy["networks"]) == {"media07_private", "media07_admin"}
assert sorted((p["published"],p.get("host_ip"),p["target"])
              for p in proxy["ports"]) == [
                 ("18898","127.0.0.1",9000),
                 ("18899","127.0.0.1",8025)]
assert not any("smtp" in str(k).lower() and "password" in str(k).lower()
               for k in services["listmonk"].get("environment", {}))
print("MEDIA07: Compose isolation, credentials and localhost-only ports PASS.")
PY

run_compose() {
  docker compose --env-file "$envfile" -f "$compose" "$@"
}
info "Pulling only MEDIA-07 staging images."
run_compose pull --quiet
info "Starting isolated staging; public Caddy, WordPress, MEDIA-05/06 and other containers untouched."
run_compose up -d

# Wait until listmonk's fixed internal upstream is reachable through localhost-only proxy.
ready=0
for attempt in $(seq 1 60); do
  status="$(curl --noproxy '*' -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:18898/ 2>/dev/null || true)"
  if [[ "$status" == 200 || "$status" == 302 || "$status" == 303 || "$status" == 401 ]]; then
    ready=1
    break
  fi
  sleep 3
done
[[ "$ready" -eq 1 ]] || fail "listmonk local readiness failed. Do NOT enable public routes. Inspect containers privately."
curl --noproxy '*' -fsS --max-time 10 http://127.0.0.1:18899/api/v1/messages >/dev/null ||
  fail "Mailpit local HTTP readiness failed."
info "listmonk admin and Mailpit local HTTP PASS."

# The test container joins ONLY the internal no-egress network. Addresses under
# .invalid are synthetic fixtures and cannot be delivered to a real subscriber.
docker pull python:3.12-alpine >/dev/null
docker run -i --rm --network sc-media07-staging_media07_private python:3.12-alpine python - <<'PY'
from email.message import EmailMessage
from smtplib import SMTP
msg=EmailMessage()
msg["From"]="fixture@sender.invalid"
msg["To"]="fixture@recipient.invalid"
msg["Subject"]="MEDIA07 Contabo synthetic staging validation"
msg.set_content("Mailpit capture only; never an external mail transport.")
with SMTP("mailpit", 1025, timeout=10) as smtp:
    smtp.send_message(msg)
print("MEDIA07: synthetic-only internal SMTP submission PASS.")
PY
curl --noproxy '*' -fsS --max-time 10 http://127.0.0.1:18899/api/v1/messages |
python3 -c 'import sys,json
m=json.load(sys.stdin)
assert m.get("total", 0)>=1
assert any("MEDIA07 Contabo synthetic staging validation" in x.get("Subject","") for x in m.get("messages",[]))
print("MEDIA07: Mailpit synthetic message captured PASS.")'

# Negative external-egress check: direct TCP attempt by an internal-network
# container must fail. It does not send any message or use subscriber data.
docker run -i --rm --network sc-media07-staging_media07_private python:3.12-alpine python - <<'PY'
import socket
s = socket.socket()
s.settimeout(3)
try:
    s.connect(("1.1.1.1", 443))
except OSError:
    print("MEDIA07: private network external TCP attempt blocked PASS.")
else:
    raise SystemExit("FAIL: isolated staging network unexpectedly has external egress")
finally:
    s.close()
PY

# Back up the new, synthetic-only database; restore to a disposable DB to
# prove the backup is usable. This never overwrites the running primary DB.
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump="$private/backups/listmonk-initial-$stamp.sql"
run_compose exec -T db pg_dump -U listmonk -d listmonk > "$dump"
[[ -s "$dump" ]] || fail "Synthetic PostgreSQL backup empty."
restore_db="media07_restore_smoke"
run_compose exec -T db createdb -U listmonk "$restore_db"
run_compose exec -T db psql -U listmonk -d "$restore_db" -v ON_ERROR_STOP=1 < "$dump" >/dev/null
restored_tables="$(run_compose exec -T db psql -U listmonk -d "$restore_db" -Atc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d '\r')"
[[ "$restored_tables" =~ ^[0-9]+$ && "$restored_tables" -gt 0 ]] ||
  fail "Restored disposable database has no tables."
run_compose exec -T db dropdb -U listmonk "$restore_db"
info "Synthetic PostgreSQL backup+disposable restore PASS ($restored_tables tables)."

receipt="$private/receipts/media07-contabo-$stamp.json"
python3 - "$receipt" "$src_sha" "$compose" "$dump" <<'PY'
import hashlib, json, pathlib, sys, datetime
dest, source_sha, compose, backup = sys.argv[1:]
p=pathlib.Path(compose)
data={
  "build":"MEDIA-07 isolated listmonk staging",
  "scope":"Contabo local-only synthetic staging, no real subscribers",
  "status":"PASS",
  "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "source_commit":source_sha,
  "compose_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
  "listmonk_admin":"127.0.0.1:18898",
  "mailpit_admin":"127.0.0.1:18899",
  "database_host_port":None,
  "smtp_host_port":None,
  "public_route_enabled":False,
  "real_smtp_connected":False,
  "real_subscribers_imported":False,
  "synthetic_mailpit_capture":"PASS",
  "private_egress_block":"PASS",
  "backup_restore":"PASS",
  "backup_file":backup,
  "bluehost_editor_acceptance":"NOT_PERFORMED"
}
pathlib.Path(dest).write_text(json.dumps(data,indent=2)+"\n")
print("MEDIA07: staging acceptance receipt "+dest)
PY
chmod 600 "$receipt" "$dump"
run_compose ps
info "DEPLOYED: isolated Contabo staging PASS. Do not open external ports or send real email."
