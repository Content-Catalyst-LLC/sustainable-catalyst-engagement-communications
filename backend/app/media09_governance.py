"""MEDIA-09.0: offline CRM governance packet validation (no network or writes).

This module evaluates *documentary completeness*, NOT real-world approval or
permission to export contacts. It must never be used as an authorization token.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "sc.media09.owner-decision.v1"
GATES = (
    "owner_provider_choice",
    "controller_and_rights_contact",
    "purpose_and_lawful_basis",
    "notice_and_collection_method",
    "processor_dpa_and_residency",
    "retention_erasure_and_backups",
    "data_mapping_and_minimization",
    "core_workspace_authorization",
    "vendor_security_and_key_management",
    "commercial_terms_and_limits",
    "limited_pilot_scope",
)
PURPOSES = frozenset({
    "press_inquiry_response",
    "institutional_partnership",
    "research_collaboration",
    "funding_opportunity",
    "consulting_inquiry",
})
PROPOSED_FIELD_SETS = {
    "contacts": frozenset({"email", "firstname", "lastname"}),
    "companies": frozenset({"name", "domain"}),
    "deals": frozenset(),
    "tasks": frozenset(),
}
GUARDS = (
    "hubspot_credentials_configured",
    "real_contact_export_enabled",
    "public_intake_enabled",
    "outbound_email_enabled",
    "subscriber_sync_enabled",
    "production_enabled",
)
EVIDENCE_RE = re.compile(r"^MEDIA09-[A-Z0-9][A-Z0-9_-]{3,63}$")


class InvalidPacket(ValueError):
    """No values from untrusted manifests should appear in public error logs."""


def _assert(condition: bool, code: str) -> None:
    if not condition:
        raise InvalidPacket(code)


def template() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "build_id": "MEDIA-09.0",
        "packet_status": "DRAFT_REVIEW_ONLY",
        "provider_choice": "undecided",
        "credential_strategy": "none",
        "webhooks_required": False,
        "purpose_codes": ["press_inquiry_response"],
        "proposed_fields": {
            "contacts": ["email", "firstname", "lastname"],
            "companies": ["name", "domain"],
            "deals": [],
            "tasks": [],
        },
        "reviews": {
            key: {"status": "pending", "evidence_ref": None}
            for key in GATES
        },
        "release_guards": {key: False for key in GUARDS},
    }


def validate_packet(packet: Any) -> dict[str, Any]:
    """Strict, bounded, no-PII manifest parse; no network/DB/secret access."""
    example = template()
    _assert(isinstance(packet, dict), "packet-not-object")
    _assert(set(packet) == set(example), "packet-keys-invalid")
    _assert(packet["schema"] == SCHEMA, "schema-mismatch")
    _assert(packet["build_id"] == "MEDIA-09.0", "build-id-mismatch")
    _assert(packet["packet_status"] == "DRAFT_REVIEW_ONLY", "status-must-stay-draft")

    provider = packet["provider_choice"]
    auth = packet["credential_strategy"]
    webhook = packet["webhooks_required"]
    _assert(type(provider) is str and provider in {"undecided", "hubspot", "no_external_crm"}, "provider-invalid")
    _assert(type(auth) is str and auth in {"none", "service_key", "project_app"}, "credential-strategy-invalid")
    _assert(type(webhook) is bool, "webhooks-not-boolean")
    _assert(provider != "undecided" or auth == "none", "undecided-cannot-pick-auth")
    _assert(provider != "no_external_crm" or (auth == "none" and webhook is False), "no-provider-must-not-connect")
    _assert(not webhook or (provider == "hubspot" and auth == "project_app"), "webhooks-require-project-app")
    _assert(auth == "none" or provider == "hubspot", "provider-auth-mismatch")

    purposes = packet["purpose_codes"]
    _assert(isinstance(purposes, list) and 1 <= len(purposes) <= len(PURPOSES), "purpose-list-invalid")
    _assert(all(type(p) is str and p in PURPOSES for p in purposes), "purpose-not-allowlisted")
    _assert(len(set(purposes)) == len(purposes), "purpose-duplicated")

    fields = packet["proposed_fields"]
    _assert(isinstance(fields, dict) and set(fields) == set(PROPOSED_FIELD_SETS), "field-map-invalid")
    for obj, allowed in PROPOSED_FIELD_SETS.items():
        names = fields[obj]
        _assert(isinstance(names, list) and len(names) <= len(allowed), "field-list-invalid")
        _assert(all(type(x) is str and x in allowed for x in names), "field-not-allowlisted")
        _assert(len(names) == len(set(names)), "field-duplicated")

    guards = packet["release_guards"]
    _assert(isinstance(guards, dict) and set(guards) == set(GUARDS), "release-guard-keys-invalid")
    _assert(all(guards[k] is False for k in GUARDS), "release-guards-must-remain-off")

    reviews = packet["reviews"]
    _assert(isinstance(reviews, dict) and set(reviews) == set(GATES), "review-gates-invalid")
    summary = {}
    for gate in GATES:
        review = reviews[gate]
        _assert(isinstance(review, dict) and set(review) == {"status", "evidence_ref"}, "review-fields-invalid")
        status = review["status"]
        ref = review["evidence_ref"]
        _assert(type(status) is str and status in {"pending", "approved", "rejected"}, "review-status-invalid")
        if status == "approved":
            _assert(type(ref) is str and EVIDENCE_RE.fullmatch(ref) is not None, "approved-needs-opaque-evidence-ref")
        else:
            _assert(ref is None, "unapproved-must-not-have-evidence")
        summary[gate] = status

    return {
        "schema": SCHEMA,
        "build_id": "MEDIA-09.0",
        "provider_choice": provider,
        "review_summary": summary,
        "pending_gates": sorted(k for k, status in summary.items() if status != "approved"),
        "documentary_review_complete": bool(
            provider != "undecided" and auth != "none" if provider == "hubspot" else provider == "no_external_crm"
        ) and all(status == "approved" for status in summary.values()),
        "evidence_verified_external_to_packet": False,
        "owner_authorization_effective": False,
        "hubspot_connected": False,
        "external_personal_data_exported": False,
        "production_activated": False,
        "next_step": "independent-owner-and-privacy-review",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline MEDIA-09.0 documentary gate. Never authorizes deployment.")
    parser.add_argument("packet", type=Path, help="Restricted, non-PII decision manifest JSON")
    args = parser.parse_args()
    try:
        result = validate_packet(json.loads(args.packet.read_text(encoding="utf-8")))
    except (InvalidPacket, OSError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({"valid": False, "error": "invalid-or-unavailable-governance-packet", "owner_authorization_effective": False}))
        return 2
    print(json.dumps({"valid": True, **result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
