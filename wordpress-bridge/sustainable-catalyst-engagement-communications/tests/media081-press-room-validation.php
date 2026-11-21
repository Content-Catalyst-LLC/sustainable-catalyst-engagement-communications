<?php
/**
 * MEDIA-08.1 isolated tests: permanent paths, references and the unchanged
 * content fingerprint. No WordPress, database or web server.
 */
define('ABSPATH', '/media081-ci-test/');
function wp_json_encode($value, $flags=0) { return json_encode($value, $flags); }
function remove_accents($s) { return strtr($s, array('é'=>'e','ü'=>'u','Ü'=>'U','ç'=>'c')); }
require_once dirname(__DIR__) . '/includes/media08-press-room.php';
function ck($ok, $name) {
    if (!$ok) { fwrite(STDERR, "FAIL: ".$name."\n"); exit(1); }
}
$R = 'SC_Media08_Press_Room';
// The fingerprint is the MEDIA-08 definition, unchanged: existing approvals stay valid.
ck($R::digest('Title','Summary','<p>Body</p>','press-release','','') ===
   hash('sha256', json_encode(array('title'=>'Title','summary'=>'Summary','body'=>'<p>Body</p>','kind'=>'press-release','source_url'=>'','embargo'=>''),
   JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)), 'fingerprint definition unchanged');
$t = 'Sustainable Catalyst connects computational analysis to manuscripts with traceable, versioned scientific outputs';
$p = $R::path_for('2026', $t, array());
ck((bool)preg_match('#^2026/[a-z0-9-]{1,80}$#', $p), 'path shape matches the route');
ck(strpos($p, '2026/sustainable-catalyst-connects-computational') === 0, 'path derived from headline');
ck(substr($p, -1) !== '-', 'no trailing hyphen after truncation');
ck($p === '2026/sustainable-catalyst-connects-computational-analysis-to-manuscripts-with', 'long headline cut at a word boundary: ' . $p);
ck(strlen(substr($p, 5)) <= 80, 'slug at most 80 characters');
ck($R::path_for('2026', $t, array($p)) === $p . '-2', 'collision gets a suffix, never reuses a path');
ck($R::path_for('2026', $t, array($p, $p . '-2')) === $p . '-3', 'second collision');
ck($R::path_for('2026', 'Café Über ç!', array()) === '2026/cafe-uber-c', 'accents and punctuation');
ck($R::path_for('2026', '!!!', array()) === '2026/release', 'empty slug fallback');
ck($R::reference_for('2026', array()) === 'SC-PR-2026-001', 'first reference');
ck($R::reference_for('2026', array('SC-PR-2026-001','SC-PR-2026-007','SC-PR-2025-009')) === 'SC-PR-2026-008', 'sequential within year');
ck($R::reference_for('2027', array('SC-PR-2026-004')) === 'SC-PR-2027-001', 'resets per year');
ck(!$R::enabled() && !defined('SCEC_MEDIA08_PUBLIC_RELEASE'), 'public release off by default');
$src = file_get_contents(dirname(__DIR__) . '/includes/media08-press-room.php');
ck(strpos($src, "add_role(self::ROLE, 'Press reviewer', array('read' => true, self::CAP_REVIEW => true))") !== false, 'reviewer role is read + review only');
ck(strpos($src, 'wp_insert_user') === false && strpos($src, 'wp_create_user') === false, 'never creates user accounts');
ck(strpos($src, "add_post_meta(\$id, self::META . 'event'") !== false, 'history is append-only rows');
ck(strpos($src, 'wp_mail(') === false && strpos($src, 'wp_remote_') === false, 'no outbound mail or HTTP');
// The press sitemap must reach WordPress on hosts whose server rules pass only *sitemap*.xml, and
// must not be captured by Rank Math's root-level ([^/]+?)-sitemap([0-9]+)?.xml rule.
ck(strpos($src, "add_rewrite_rule('^press/sitemap\\.xml$'") !== false && strpos($src, "home_url('/press/sitemap.xml')") !== false, 'press sitemap at /press/sitemap.xml');
ck((bool)preg_match('#(robots\.txt|[a-z0-9_\-]*sitemap[a-z0-9_\.\-]*\.(xml|xsl|html)(\.gz)?)#', '/press/sitemap.xml'), 'path passes the host static-file exception');
ck(!preg_match('#^([^/]+?)-sitemap([0-9]+)?\.xml$#', 'press/sitemap.xml'), 'path not captured by Rank Math');
echo "MEDIA-08.1 permanent URLs, references and fingerprint: PASS\n";
