from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php"
CSS = PLUGIN.parent / "assets/bridge.css"

def test_plugin_has_required_metadata():
    s = PLUGIN.read_text()
    assert "Plugin Name:" in s and "Version: 8.8.2" in s

def test_plugin_uses_settings_api_and_admin_permission():
    s = PLUGIN.read_text()
    assert "register_setting(" in s and "manage_options" in s

def test_no_private_api_or_secrets_in_plugin():
    s = PLUGIN.read_text()
    for forbidden in ("8816", "127.0.0.1", "SCEC_IDENTITY_SIGNING_KEY", "wp_remote_get(", "wp_remote_post(", "<iframe", "setcookie("):
        assert forbidden not in s

def test_https_validation_and_safe_links():
    s = PLUGIN.read_text()
    assert "!== 'https'" in s and "esc_url($url)" in s
    assert 'rel="noopener noreferrer external"' in s

def test_shortcodes_registered():
    s = PLUGIN.read_text()
    assert "add_shortcode('sc_engagement_communications'" in s
    assert "add_shortcode('sc_engagement_launch'" in s

def test_css_scoped():
    s = CSS.read_text()
    assert ".scec880" in s and not any(t in s for t in ("body{", "html{", "h1{"))

def test_php_lint():
    r = subprocess.run(['php', '-l', str(PLUGIN)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
