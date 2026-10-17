import json
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('scec_certification',ROOT/'certification/certify.py')
mod=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

def test_source_checks_pass():
    assert all(mod.check_source().values())

def test_certification_does_not_claim_live_approval():
    source=(ROOT/'certification/certify.py').read_text()
    assert "'production_certified':False" in source
    assert "'production_writes_enabled':False" in source

def test_public_url_not_hardcoded_into_bridge():
    data=(ROOT/'wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php').read_text()
    assert '127.0.0.1:8097' not in data

def test_no_customer_data_in_certification_output():
    source=(ROOT/'certification/certify.py').read_text()
    assert 'v1/engagement/' not in source
    assert 'v1/support/cases' not in source

def test_manifest_declares_versions_without_mislabel():
    m=json.loads((ROOT/'RELEASE-MANIFEST.json').read_text())
    assert m['version'] in ('8.9.0','9.0.0','9.1.0','9.2.0','9.3.0','9.4.0','9.5.0','9.7.0','9.9.0','10.0.0','10.1.0','10.5.0','10.6.0','10.7.0','10.8.0','10.9.0','11.0.0')
    assert m['running_backend_version'] in ('8.6.0','9.0.0-staged')
    assert m['running_frontend_version']=='8.7.0'
    assert m['wordpress_bridge_version']=='8.8.2'

def test_no_database_migration_added():
    files=list((ROOT/'backend/alembic/versions').glob('*.py'))
    assert not any('890_' in f.name for f in files)
