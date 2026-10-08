import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv('SCEC_ENV', 'development')
    auth_mode: str = os.getenv('SCEC_AUTH_MODE', 'disabled')
    service_token: str = os.getenv('SCEC_SERVICE_TOKEN', '')

def validate_settings(settings: Settings) -> None:
    if settings.environment == 'production':
        if settings.auth_mode != 'token' or len(settings.service_token) < 32:
            raise RuntimeError('Production requires token authentication and a token of at least 32 characters')
    if settings.auth_mode not in ('disabled', 'token'):
        raise RuntimeError('Invalid authentication mode')
