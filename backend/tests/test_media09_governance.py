"""MEDIA-09.0 governance-only negative tests. No HubSpot network I/O."""
import copy
import unittest

from app.media09_governance import (
    GATES, GUARDS, InvalidPacket, template, validate_packet,
)


class TestMedia09Governance(unittest.TestCase):
    def test_default_packet_is_valid_but_unapproved(self):
        result = validate_packet(template())
        self.assertFalse(result["documentary_review_complete"])
        self.assertEqual(set(result["pending_gates"]), set(GATES))
        for key in ("owner_authorization_effective", "hubspot_connected", "external_personal_data_exported", "production_activated"):
            self.assertFalse(result[key])

    def test_review_completeness_does_not_grant_authority(self):
        packet = template()
        packet["provider_choice"] = "hubspot"
        packet["credential_strategy"] = "service_key"
        for gate in GATES:
            packet["reviews"][gate] = {"status": "approved", "evidence_ref": "MEDIA09-REVIEWED-REFERENCE"}
        report = validate_packet(packet)
        self.assertTrue(report["documentary_review_complete"])
        self.assertFalse(report["evidence_verified_external_to_packet"])
        self.assertFalse(report["owner_authorization_effective"])
        self.assertFalse(report["hubspot_connected"])

    def test_no_external_crm_remains_a_valid_choice(self):
        packet = template()
        packet["provider_choice"] = "no_external_crm"
        self.assertFalse(validate_packet(packet)["documentary_review_complete"])

    def test_service_key_cannot_be_used_with_webhooks(self):
        packet = template()
        packet.update(provider_choice="hubspot", credential_strategy="service_key", webhooks_required=True)
        with self.assertRaises(InvalidPacket):
            validate_packet(packet)
        packet["credential_strategy"] = "project_app"
        self.assertFalse(validate_packet(packet)["owner_authorization_effective"])

    def test_unknown_fields_and_private_notes_are_rejected(self):
        for name in ("private_research_document", "notes", "lifecyclestage", "mailing_list"):
            with self.subTest(name=name):
                packet = template()
                packet["proposed_fields"]["contacts"].append(name)
                with self.assertRaises(InvalidPacket):
                    validate_packet(packet)

    def test_non_bounded_extra_key_rejected(self):
        packet = template()
        packet["hubspot_token"] = "never-allowed"
        with self.assertRaises(InvalidPacket):
            validate_packet(packet)

    def test_no_release_guard_can_be_enabled(self):
        for guard in GUARDS:
            packet = template()
            packet["release_guards"][guard] = True
            with self.subTest(guard=guard), self.assertRaises(InvalidPacket):
                validate_packet(packet)
            packet["release_guards"][guard] = "false"
            with self.assertRaises(InvalidPacket):
                validate_packet(packet)

    def test_approved_review_requires_opaque_evidence_not_pii(self):
        for value in (None, "person@example.org", "https://example.com/secret", "MEDIA09-", "MEDIA09-OK\nsecret"):
            packet = template()
            packet["reviews"][GATES[0]] = {"status": "approved", "evidence_ref": value}
            with self.subTest(value=value), self.assertRaises(InvalidPacket):
                validate_packet(packet)

    def test_pending_cannot_carry_fake_approval_evidence(self):
        packet = template()
        packet["reviews"][GATES[0]]["evidence_ref"] = "MEDIA09-UNAPPROVED"
        with self.assertRaises(InvalidPacket):
            validate_packet(packet)

    def test_purpose_duplicate_and_marketing_rejected(self):
        for purposes in (["press_inquiry_response", "press_inquiry_response"], ["marketing_campaign"], []):
            packet = template()
            packet["purpose_codes"] = purposes
            with self.subTest(purposes=purposes), self.assertRaises(InvalidPacket):
                validate_packet(packet)

    def test_review_is_not_boolean(self):
        packet = template()
        packet["reviews"][GATES[0]]["status"] = True
        with self.assertRaises(InvalidPacket):
            validate_packet(packet)

    def test_undeclared_provider_or_unmatched_auth_rejected(self):
        for provider, auth in (("salesforce", "none"), ("undecided", "service_key"), ("no_external_crm", "service_key")):
            packet = template()
            packet["provider_choice"] = provider
            packet["credential_strategy"] = auth
            with self.subTest(provider=provider, auth=auth), self.assertRaises(InvalidPacket):
                validate_packet(packet)

    def test_no_input_mutation(self):
        packet = template()
        before = copy.deepcopy(packet)
        validate_packet(packet)
        self.assertEqual(packet, before)


if __name__ == "__main__":
    unittest.main()
