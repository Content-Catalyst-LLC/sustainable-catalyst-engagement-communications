import pytest
from app.settings import Settings, validate_settings

def test_reject_unauthenticated_production():
    with pytest.raises(RuntimeError):validate_settings(Settings(environment='production',auth_mode='disabled'))

def test_reject_weak_token():
    with pytest.raises(RuntimeError):validate_settings(Settings(environment='production',auth_mode='token',service_token='weak'))

def test_allow_production_with_long_token():
    validate_settings(Settings(environment='production',auth_mode='token',service_token='x'*40))
