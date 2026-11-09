"""MEDIA-07.3: explicitly opted-in, synthetic-only listmonk DRAFT creation.

No subscriber mutation, recipient address, test send, scheduling, or status
transition is implemented. The Listmonk target is hard-coded to host loopback.
The only allowed campaign list is a configured private, empty synthetic list.
This is a first staging adapter, not production approval or full idempotency.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .offline_staging import scope

router = APIRouter(prefix="/v1/newsletter-studio/listmonk", tags=["media07-staging-draft-only"])
_scope = scope("SCEC_MEDIA07_STAGING_ENABLED")
LISTMONK_LOOPBACK = "http://127.0.0.1:18898"
STAGING_LIST_NAME = "SCEC MEDIA07 STAGING EMPTY"
REF_RE = re.compile(r"^wp-newsletter:[1-9][0-9]{0,11}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
UNSAFE_HTML = re.compile(
    r"<\s*/?\s*(?:script|iframe|object|embed|form|input|svg|math)\b"
    r"|(?<![a-z])on[a-z]{3,24}\s*="
    r"|javascript\s*:", re.IGNORECASE
)


class DraftCandidate(BaseModel):
    """Source-provided draft input. Fingerprints are integrity checks, NOT signed approvals."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schema_version: Literal["scec.media07.listmonk-draft/1"]
    organization_id: UUID
    newsletter_ref: str = Field(min_length=15, max_length=26)
    studio_revision_sha256: str = Field(min_length=64, max_length=64)
    rendered_html_sha256: str = Field(min_length=64, max_length=64)
    title: str = Field(min_length=1, max_length=140)
    subject: str = Field(min_length=1, max_length=200)
    preheader: str = Field(default="", max_length=180)
    body_html: str = Field(min_length=20, max_length=100000)
    altbody: str = Field(min_length=1, max_length=15000)
    synthetic_only: Literal[True]

    @field_validator("newsletter_ref")
    @classmethod
    def valid_ref(cls, value):
        if not REF_RE.fullmatch(value):
            raise ValueError("Invalid Newsletter Studio reference")
        return value

    @field_validator("studio_revision_sha256", "rendered_html_sha256")
    @classmethod
    def valid_sha(cls, value):
        if not SHA_RE.fullmatch(value):
            raise ValueError("Invalid SHA-256 fingerprint")
        return value

    @model_validator(mode="after")
    def integrity(self):
        rendered = hashlib.sha256(self.body_html.encode("utf-8")).hexdigest()
        if rendered != self.rendered_html_sha256:
            raise ValueError("Rendered HTML does not match declared fingerprint")
        if UNSAFE_HTML.search(self.body_html):
            raise ValueError("Unsafe HTML element or attribute")
        # Template directives are not evaluated by Sustainable Catalyst. Don't
        # let a simulated draft execute listmonk's template expressions.
        if "{{" in self.body_html or "}}" in self.body_html:
            raise ValueError("Template directives are not allowed in staging HTML")
        return self


def _staging_config(tenant):
    """Fail closed until this exact single-organization synthetic draft mode is enabled."""
    if os.getenv("SCEC_ENV") != "staging" or os.getenv("SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED") != "1":
        raise HTTPException(503, "MEDIA-07.3 draft adapter disabled")
    expected = os.getenv("SCEC_MEDIA07_DRAFT_ORGANIZATION_ID", "")
    allowed = {v.strip() for v in os.getenv("SCEC_ALLOWED_ORGANIZATION_IDS", "").split(",") if v.strip()}
    if not expected or str(tenant) != expected or allowed != {expected}:
        raise HTTPException(503, "Isolated single-organization staging required")
    raw_id = os.getenv("SCEC_MEDIA07_EMPTY_LIST_ID", "")
    if not raw_id.isdecimal() or int(raw_id) <= 0 or int(raw_id) > 100000000:
        raise HTTPException(503, "Private synthetic list ID not configured")
    return int(raw_id)


def _credentials():
    """Read staging API token from a regular, owner-restricted file, never source or WordPress."""
    name = os.getenv("SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE", "")
    if not name.startswith("/"):
        raise HTTPException(503, "Private listmonk API credentials not configured")
    p = Path(name)
    try:
        st = p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or st.st_size > 4096:
            raise ValueError()
        values = json.loads(p.read_text(encoding="utf-8"))
        user, token = values["username"], values["token"]
        if not isinstance(user, str) or not (1 <= len(user) <= 128) or not isinstance(token, str) or not (16 <= len(token) <= 512):
            raise ValueError()
        if any(c in user + token for c in "\r\n"):
            raise ValueError()
        return user, token
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "Invalid private listmonk API credential file") from None


def _client():
    """Fixed host, no proxy environment, no redirects; HTTP used only over server loopback."""
    user, token = _credentials()
    return httpx.Client(
        base_url=LISTMONK_LOOPBACK, auth=(user, token),
        timeout=httpx.Timeout(5.0), trust_env=False, follow_redirects=False,
        headers={"Accept": "application/json", "User-Agent": "SCEC-MEDIA07-Canary/1"},
    )


def _api_json(resp):
    # No provider error bodies or credentials are ever echoed to clients.
    if resp.status_code != 200:
        raise HTTPException(502, "listmonk staging API rejected request")
    if len(resp.content) > 512000:
        raise HTTPException(502, "listmonk staging response too large")
    try:
        value = resp.json()
    except (ValueError, UnicodeError):
        raise HTTPException(502, "Invalid listmonk staging response") from None
    if not isinstance(value, dict) or "data" not in value:
        raise HTTPException(502, "Unexpected listmonk staging response")
    return value["data"]


def _verify_empty_private_list(client, list_id):
    info = _api_json(client.get("/api/lists/" + str(list_id)))
    # No list with real subscribers may be targeted—even for creating drafts.
    if not isinstance(info, dict) or info.get("id") != list_id or info.get("name") != STAGING_LIST_NAME or \
            info.get("type") != "private" or info.get("status") != "active" or \
            type(info.get("subscriber_count")) is not int or info["subscriber_count"] != 0:
        raise HTTPException(409, "Configured campaign list is not empty private staging")
    return True


def _fingerprint(tenant, req):
    canonical = {
        "org": str(tenant), "ref": req.newsletter_ref,
        "studio_rev": req.studio_revision_sha256, "rendered": req.rendered_html_sha256,
        "title": req.title, "subject": req.subject,
        "preheader": req.preheader, "altbody": req.altbody,
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _existing_draft(client, name):
    data = _api_json(client.get("/api/campaigns", params={"query": name, "per_page": "all"}))
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise HTTPException(502, "listmonk campaign search unavailable")
    matches = [x for x in data["results"] if isinstance(x, dict) and x.get("name") == name]
    if not matches:
        return None
    if len(matches) != 1 or matches[0].get("status") != "draft":
        raise HTTPException(409, "Existing campaign is not an unmodified staging draft")
    cid = matches[0].get("id")
    if type(cid) is not int or cid <= 0:
        raise HTTPException(502, "Invalid listmonk campaign identifier")
    return cid


@router.get("/status")
def status(tenant=Depends(_scope)):
    # Not a network health check: do not suggest success until the adapter runs.
    configured = os.getenv("SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED") == "1"
    return {
        "release": "MEDIA-07.3", "organization_id": str(tenant),
        "mode": "synthetic-listmonk-draft-only",
        "adapter_gate_configured": configured, "provider_reachability_verified": False,
        "external_sending_enabled": False, "subscriber_import_enabled": False,
        "scheduled_campaigns_enabled": False, "production_certified": False,
        "studio_editor_live_integrated": False,
    }


@router.post("/drafts", status_code=201)
def create_draft(payload: DraftCandidate, tenant=Depends(_scope)):
    list_id = _staging_config(tenant)
    if str(payload.organization_id) != str(tenant):
        raise HTTPException(403, "Newsletter organization mismatch")
    digest = _fingerprint(tenant, payload)
    name = "SCEC MEDIA07 STAGING " + digest
    try:
        with _client() as client:
            _verify_empty_private_list(client, list_id)
            existing = _existing_draft(client, name)
            if existing is not None:
                return {
                    "release": "MEDIA-07.3", "organization_id": str(tenant),
                    "campaign_id": existing, "campaign_status": "draft",
                    "draft_reused": True, "fingerprint": digest,
                    "synthetic_only": True, "sent": False,
                }
            body = {
                "name": name, "subject": "STAGING ONLY — " + payload.subject,
                "type": "regular", "content_type": "html",
                "messenger": "email", "body": payload.body_html,
                "altbody": payload.altbody, "lists": [list_id],
                "tags": ["scec-media07-staging", "synthetic-empty-list"],
            }
            # Never request /test, /status, /archive or /send; POST creates a DRAFT.
            campaign = _api_json(client.post("/api/campaigns", json=body))
            if not isinstance(campaign, dict) or campaign.get("status") != "draft" or campaign.get("name") != name:
                raise HTTPException(502, "Campaign was not confirmed as an unsent draft")
            cid = campaign.get("id")
            if type(cid) is not int or cid <= 0:
                raise HTTPException(502, "Invalid listmonk campaign identifier")
            return {
                "release": "MEDIA-07.3", "organization_id": str(tenant),
                "campaign_id": cid, "campaign_status": "draft",
                "draft_reused": False, "fingerprint": digest,
                "synthetic_only": True, "sent": False,
            }
    except httpx.HTTPError:
        raise HTTPException(502, "listmonk staging service unavailable") from None


@router.post("/send")
@router.post("/schedule")
@router.post("/campaigns/{campaign_id}/status")
@router.post("/subscribers/import")
@router.post("/test-send")
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503, "MEDIA-07.3 does not permit delivery or subscribers")
