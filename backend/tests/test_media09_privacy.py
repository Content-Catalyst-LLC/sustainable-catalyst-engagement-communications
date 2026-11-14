import json
from datetime import datetime,timezone
import pytest
from fastapi import HTTPException
from app import media09_privacy as privacy
from app.media09_press import PressInquiryCreate,RealPressInquiryCreate


def test_calendar_policy_and_default_disabled(monkeypatch):
    monkeypatch.delenv('SCEC_MEDIA09_RETENTION_POLICY_FILE',raising=False)
    assert privacy.policy().enabled is False
    assert privacy.months(datetime(2024,1,31,tzinfo=timezone.utc),1).day==29
    assert privacy.months(datetime(2023,1,31,tzinfo=timezone.utc),1).day==28
    assert privacy.months(datetime(2024,2,29,tzinfo=timezone.utc),12).day==28
    with pytest.raises(HTTPException) as exc:privacy.enabled()
    assert exc.value.status_code==503


def test_ledger_custody_signature_and_no_plain_identifiers(monkeypatch,tmp_path):
    root=tmp_path/'private';root.mkdir(mode=0o700)
    secret=root/'key';secret.write_text('synthetic-privacy-key-only-1234567890');secret.chmod(0o600)
    monkeypatch.setenv('SCEC_MEDIA09_PRIVACY_ENABLED','1')
    monkeypatch.setenv('SCEC_MEDIA09_PRIVACY_KEY_FILE',str(secret))
    monkeypatch.setenv('SCEC_MEDIA09_SUPPRESSION_FILE',str(root/'suppression.json'))
    monkeypatch.setenv('SCEC_MEDIA09_NEW_SYNTHETIC_BASELINE','1')
    monkeypatch.setenv('SCEC_ENV','development')
    privacy.initialize_ledger()
    with privacy.ledger() as value:assert value=={'version':1,'tenants':{}}
    with pytest.raises(HTTPException):privacy.initialize_ledger()
    assert privacy.digest('tenant','contacts','fixture-id')!=privacy.digest('tenant','inquiries','fixture-id')
    path=root/'suppression.json';value=json.loads(path.read_text());value['ledger']['tenants']={'forged':{}};path.write_text(json.dumps(value))
    with pytest.raises(HTTPException) as exc:
        with privacy.ledger():pass
    assert exc.value.status_code==503
    path.unlink()
    with pytest.raises(HTTPException):
        with privacy.ledger():pass


def test_managed_storage_rejects_escape_symlink_and_hardlink(monkeypatch,tmp_path):
    root=tmp_path/'files';root.mkdir(mode=0o700);monkeypatch.setenv('FILES',str(root))
    outside=tmp_path/'outside';outside.write_text('synthetic')
    (root/'link').symlink_to(outside)
    with pytest.raises(HTTPException):privacy.owned_path('FILES','../outside')
    with pytest.raises(HTTPException):privacy.owned_path('FILES','link')
    import os
    os.link(outside,root/'hard')
    with pytest.raises(HTTPException):privacy.owned_path('FILES','hard')
    assert outside.read_text()=='synthetic'


def test_real_contract_does_not_accept_legacy_consent_as_acknowledgment(monkeypatch):
    from app import media09_release
    from pydantic import ValidationError
    from uuid import uuid4
    monkeypatch.setattr(media09_release,'approved_notice',lambda:{'version':'SYNTHETIC-APPROVAL-TEST'})
    values=dict(synthetic=False,idempotency_key=uuid4(),name='Fixture Institution Desk',email='desk@example.org',
        subject='Fixture public methods request',message='Please share the public methods summary.',kind='press',privacy_notice_version='SYNTHETIC-APPROVAL-TEST')
    with pytest.raises(ValidationError):RealPressInquiryCreate(**values,consent_to_reply=True)
    valid=RealPressInquiryCreate(**values,privacy_notice_acknowledged=True)
    assert valid.consent_to_reply is None and valid.privacy_notice_acknowledged is True
