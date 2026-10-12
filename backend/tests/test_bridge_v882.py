from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php"

def test_feature_suggestions_separate_from_feedback():
    s = PLUGIN.read_text()
    assert "array('Feedback'," in s
    assert "array('Feature Suggestions'," in s
    assert "array('feature-suggestions')" in s

def test_page_navigation_remains_noninvasive():
    s = PLUGIN.read_text()
    assert "get_page_by_path($slug, OBJECT, 'page')" in s
    for forbidden in ('wp_insert_post(', 'wp_delete_post(', 'wp_redirect(', 'wp_remote_post('):
        assert forbidden not in s
