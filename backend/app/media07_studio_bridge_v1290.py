"""MEDIA-07.3 server-side WordPress -> Engagement staging bridge.

A separate narrowly scoped HMAC credential authorizes *one* synthetic draft
operation. This is NOT a production publication or delivery API. There are no
subscriber, send, schedule, list-mutation, or arbitrary provider URL routes.
"""
import hashlib
import hmac
import logging
import os
import re
import time

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError

from .media07_listmonk_draft_v1280 import DraftCandidate, _staging_config, create_draft
from .newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS

router = APIRouter(prefix="/v1/newsletter-studio/bridge", tags=["media07-signed-staging-bridge"])
LOG = logging.getLogger("scec.media07.bridge")
SIGNATURE_RE = re.compile(r"^[a-f0-9]{64}$")
TIMESTAMP_RE = re.compile(r"^[0-9]{10}$")
MAX_BODY_BYTES = 130000


def _bridge_key():
    if (os.getenv("SCEC_ENV") != "staging"
            or os.getenv("SCEC_IDENTITY_MODE") != "bound"
            or os.getenv("SCEC_MEDIA07_STAGING_ENABLED") != "1"
            or os.getenv("SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED") != "1"
            or os.getenv("SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED") != "1"
            or any(os.getenv(flag, "0") != "0" for flag in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS))):
        raise HTTPException(503, "Newsletter Studio staging bridge disabled")
    secret = os.getenv("SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY", "")
    if len(secret) < 32 or len(secret) > 512 or "\n" in secret or "\r" in secret:
        raise HTTPException(503, "Newsletter Studio staging bridge key unavailable")
    if secret == os.getenv("SCEC_IDENTITY_SIGNING_KEY", ""):
        raise HTTPException(503, "Staging bridge requires a distinct scoped signing key")
    return secret.encode("utf-8")


@router.post("/drafts", status_code=201)
async def sync_saved_studio_draft(
    request: Request,
    x_scec_media07_timestamp: str | None = Header(default=None),
    x_scec_media07_signature: str | None = Header(default=None),
):
    """Authenticate before parsing JSON or contacting listmonk.

    WordPress must independently verify the saved private post's canonical
    revision and administrator CSRF nonce before signing these exact bytes.
    """
    key = _bridge_key()
    stamp = x_scec_media07_timestamp or ""
    signature = x_scec_media07_signature or ""
    if not TIMESTAMP_RE.fullmatch(stamp) or not SIGNATURE_RE.fullmatch(signature):
        raise HTTPException(401, "Invalid newsletter bridge authorization")
    if abs(int(time.time()) - int(stamp)) > 120:
        raise HTTPException(401, "Expired newsletter bridge authorization")
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        raise HTTPException(415, "JSON content type required")
    if int(request.headers.get("content-length", "0") or 0) > MAX_BODY_BYTES:
        raise HTTPException(413, "Newsletter draft too large")
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(413, "Newsletter draft too large")
    expected = hmac.new(key, stamp.encode("ascii") + b"\n" + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(401, "Invalid newsletter bridge authorization")

    try:
        payload = DraftCandidate.model_validate_json(raw)
    except ValidationError:
        raise HTTPException(422, "Invalid saved newsletter draft") from None
    _staging_config(payload.organization_id)
    response = create_draft(payload, tenant=payload.organization_id)
    LOG.info("synthetic_studio_draft org_hash=%s campaign_id=%s reused=%s",
             hashlib.sha256(str(payload.organization_id).encode()).hexdigest()[:12],
             response["campaign_id"], response["draft_reused"])
    return response
