"""Operator configuration for owner-approved real intake. Defaults to synthetic staging."""
import json
import os
from pathlib import Path
from fastapi import HTTPException


def real_intake():
    return os.getenv('SCEC_MEDIA09_REAL_INTAKE_ENABLED') == '1'


def approved_notice():
    if not real_intake():
        raise HTTPException(503,'Real Press intake is disabled')
    path=Path(os.getenv('SCEC_MEDIA09_APPROVED_NOTICE_FILE',''))
    try:
        if not path.is_absolute() or path.stat().st_mode & 0o077:
            raise ValueError()
        value=json.loads(path.read_text())
        required=('version','text','privacy_url','privacy_approval_ref','security_approval_ref',
                  'identity_acceptance_ref','cutover_authorization_ref','privacy_controls_acceptance_ref')
        if not isinstance(value,dict) or any(not isinstance(value.get(k),str) or not value[k].strip() for k in required):
            raise ValueError()
        if len(value['version'])>80 or not value['privacy_url'].startswith('https://'):
            raise ValueError()
        from .media09_privacy import enabled as privacy_enabled,policy
        privacy_enabled()
        retention=policy()
        if not retention.enabled or not retention.approval_ref:
            raise HTTPException(503,'Approved operational retention policy required for real intake')
        return value
    except (OSError,ValueError,TypeError):
        raise HTTPException(503,'Owner-approved privacy, security, identity and cutover records required') from None
