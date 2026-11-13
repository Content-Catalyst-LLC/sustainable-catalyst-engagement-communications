<?php
/**
 * Isolated CLI regression for MEDIA-07's private JSON ingestion contract.
 * No actual WordPress, external network, or subscriber records.
 */
define('ABSPATH', '/unused-test-root/');
require_once dirname(__DIR__) . '/includes/media07-studio.php';

function verify($ok, $name) {
    if (!$ok) { fwrite(STDERR, "FAILED: $name\n"); exit(1); }
}
$valid = '{"pages":[{"component":"<mjml><mj-body><mj-section><mj-column><mj-text>Hi</mj-text></mj-column></mj-section></mj-body></mjml>"}]}';
verify(is_array(SC_Media07_Studio::validate_project($valid)), 'valid one-page editor JSON');
verify(SC_Media07_Studio::validate_project('') === false, 'empty JSON rejected');
verify(SC_Media07_Studio::validate_project('{}') === false, 'missing pages rejected');
verify(SC_Media07_Studio::validate_project('{"pages":[]}') === false, 'zero pages rejected');
verify(SC_Media07_Studio::validate_project('{"pages":[{},{}]}') === false, 'multiple pages rejected');
verify(SC_Media07_Studio::validate_project('{"pages":[') === false, 'malformed JSON rejected');
verify(SC_Media07_Studio::validate_project(str_repeat('A', 262145)) === false, 'oversized body rejected');
verify(SC_Media07_Studio::TYPE === 'scec_newsletter', 'private post type');
echo "MEDIA-07 PHP validation: PASS\n";
