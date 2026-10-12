import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv('SCEC_ENV', 'development')
    auth_mode: str = os.getenv('SCEC_AUTH_MODE', 'disabled')
    service_token: str = os.getenv('SCEC_SERVICE_TOKEN', '')
    identity_mode: str = os.getenv('SCEC_IDENTITY_MODE', 'legacy')
    identity_signing_key: str = os.getenv('SCEC_IDENTITY_SIGNING_KEY', '')

def validate_settings(settings: Settings) -> None:
    if settings.identity_mode not in ('legacy','bound'):
        raise RuntimeError('Invalid identity mode')
    if settings.identity_mode == 'bound' and len(settings.identity_signing_key) < 32:
        raise RuntimeError('Bound mode requires signing key of at least 32 characters')
    if settings.environment == 'production':
        if settings.identity_mode == 'bound':
            if len(settings.identity_signing_key) < 32:
                raise RuntimeError('Production bound mode requires signing key')
        elif settings.auth_mode != 'token' or len(settings.service_token) < 32:
            raise RuntimeError('Production requires token authentication and a token of at least 32 characters')
    if settings.auth_mode not in ('disabled', 'token'):
        raise RuntimeError('Invalid authentication mode')
