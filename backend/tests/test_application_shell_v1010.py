from fastapi.testclient import TestClient
from app.main import app
from app.application_shell_v1010 import ROUTES, PAGES
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parents[2]

def test_staging_disabled(monkeypatch):
    monkeypatch.setenv("SCEC_SHELL_STAGING_ENABLED","0")
    # Service-token authentication may reject first; no data returned in either case.
    response=TestClient(app).get('/v1/application-shell/status')
    assert response.status_code in (401,403,503)

def test_route_contract():
    assert len(ROUTES)==12 and len(set(ROUTES))==12
    assert len(PAGES)==5 and "Feature Suggestions" in PAGES

def test_browser_shell_is_read_only():
    html=(ROOT/'frontend/index.html').read_text()
    js=(ROOT/'frontend/assets/app.js').read_text()
    assert 'READ-ONLY PREVIEW' in html and 'NOT LIVE RECORDS' in html
    assert 'id="navSearch"' in html and 'id="workspacePath"' in html
    for route in ROUTES:assert 'data-route="'+route+'"' in html
    assert 'localStorage' not in js and 'sessionStorage' not in js
    assert 'fetch(' not in js and 'XMLHttpRequest' not in js

def test_all_mutations_are_denied_in_default_mode(monkeypatch):
    monkeypatch.setenv('SCEC_SHELL_STAGING_ENABLED','0')
    client=TestClient(app)
    for path in ('commit','enable-live'):
        assert client.post('/v1/application-shell/'+path).status_code in (401,403,503)

def test_release_state():
    r=TestClient(app).get('/health')
    assert r.status_code==200 and r.json()['version']=='11.9.0'
