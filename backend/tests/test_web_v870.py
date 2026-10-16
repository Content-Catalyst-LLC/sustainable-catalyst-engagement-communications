"""Release 8.7.0: fail-closed static web surface tests."""
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
ROOT=Path(__file__).resolve().parents[2]
WEB=ROOT/'frontend'

def test_static_assets_present():
    for name in ('index.html','assets/styles.css','assets/app.js','Dockerfile','nginx.conf','compose.yaml'):
        assert (WEB/name).is_file(), name

def test_no_browser_tokens_or_fake_live_records():
    appjs=(WEB/'assets/app.js').read_text()
    html=(WEB/'index.html').read_text()
    assert 'PREVIEW DATA' in html
    assert 'No live records connected' in appjs
    assert 'localStorage' not in appjs
    assert 'fetch(' not in appjs
    assert 'SCEC_IDENTITY_SIGNING_KEY' not in (appjs+html)

def test_private_api_not_exposed_by_web_proxy():
    config=(WEB/'nginx.conf').read_text()
    assert "connect-src 'none'" in config
    assert 'proxy_pass' not in config
    assert '127.0.0.1:8097:80' in (WEB/'compose.yaml').read_text()

def test_service_version():
    assert TestClient(app).get('/health').json()['version']=='10.1.0'

def test_no_web_database_revision():
    revisions=list((ROOT/'backend/alembic/versions').glob('*.py'))
    assert not any(p.name.startswith('870_') for p in revisions)
