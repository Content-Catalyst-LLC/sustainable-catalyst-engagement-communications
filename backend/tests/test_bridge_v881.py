from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php"
CSS = PLUGIN.parent / "assets/bridge.css"

def test_existing_pages_preserved():
    s = PLUGIN.read_text()
    assert "get_page_by_path(" in s and "post_status !== 'publish'" in s
    assert "post_password_required($page)" in s
    assert "wp_insert_post(" not in s and "wp_delete_post(" not in s and "wp_redirect(" not in s

def test_independent_services_navigation():
    s = PLUGIN.read_text()
    assert "add_shortcode('sc_engagement_public_links'" in s
    for item in ("Contact", "Feedback", "Channel", "Support"):
        assert "array('" + item + "'" in s
    assert ".scec881-public-grid" in CSS.read_text()
