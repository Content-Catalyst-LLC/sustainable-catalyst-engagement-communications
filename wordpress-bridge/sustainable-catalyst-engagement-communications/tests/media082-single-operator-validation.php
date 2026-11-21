<?php
/**
 * MEDIA-08.2 isolated tests: single-operator owner self-review rule.
 * No WordPress, database or web server.
 */
define('ABSPATH', '/media082-ci-test/');
function wp_json_encode($value, $flags=0) { return json_encode($value, $flags); }
$GLOBALS['admins'] = array(1);
function user_can($user, $cap) { return $cap === 'manage_options' && in_array((int)$user, $GLOBALS['admins'], true); }
require_once dirname(__DIR__) . '/includes/media08-press-room.php';
function ck($ok, $name) { if (!$ok) { fwrite(STDERR, "FAIL: ".$name."\n"); exit(1); } }
$R = 'SC_Media08_Press_Room'; $SELF = $R::MODE_OWNER_SELF; $IND = $R::MODE_INDEPENDENT;
$sha = hash('sha256', 'x'); $t = 1800000000;

// Mode is off unless configured.
ck($R::single_operator_owner() === 0, 'single-operator mode off by default');
// approval_ok
ck($R::approval_ok(1, 2, $IND, 0), 'independent reviewer accepted');
ck($R::approval_ok(1, 2, '', 0), 'legacy record without a mode is independent');
ck(!$R::approval_ok(1, 1, $IND, 0), 'self approval recorded as independent is rejected');
ck(!$R::approval_ok(1, 1, '', 1), 'self approval without the owner mode is rejected even for the owner');
ck($R::approval_ok(1, 1, $SELF, 1), 'owner self-review by the configured owner accepted');
ck(!$R::approval_ok(1, 1, $SELF, 0), 'owner self-review rejected when no owner is configured');
ck(!$R::approval_ok(3, 3, $SELF, 1), 'self-review by a user other than the owner rejected');
ck(!$R::approval_ok(1, 0, $SELF, 1) && !$R::approval_ok(0, 1, $SELF, 1), 'missing author or reviewer rejected');
// publication_gate keeps every other check in owner mode.
ck($R::publication_gate(true, 'approved', $sha, $sha, 1, 1, '', $t, $SELF, 1), 'owner-approved release passes the gate');
ck(!$R::publication_gate(false, 'approved', $sha, $sha, 1, 1, '', $t, $SELF, 1), 'flag off still blocks');
ck(!$R::publication_gate(true, 'in_review', $sha, $sha, 1, 1, '', $t, $SELF, 1), 'unapproved state still blocks');
ck(!$R::publication_gate(true, 'approved', $sha, hash('sha256','y'), 1, 1, '', $t, $SELF, 1), 'changed fingerprint still blocks');
ck(!$R::publication_gate(true, 'approved', $sha, $sha, 1, 1, '2028-01-01T00:00', $t, $SELF, 1), 'active embargo still blocks');
ck($R::publication_gate(true, 'approved', $sha, $sha, 1, 1, '2026-01-01T00:00', $t, $SELF, 1), 'expired embargo passes');
ck(!$R::publication_gate(true, 'approved', $sha, $sha, 1, 1, '', $t), 'default (independent) gate still rejects self approval');
ck(!$R::publication_gate(true, 'approved', $sha, $sha, 1, 1, '', $t, $SELF, 0), 'owner mode removed: unreleased self-approval cannot be released');

$src = file_get_contents(dirname(__DIR__) . '/includes/media08-press-room.php');
ck(strpos($R::SELF_REVIEW_LABEL, 'not independent review') !== false, 'self-review label states it is not independent review');
ck(strpos($src, "'owner_self_approved'=>self::SELF_REVIEW_LABEL") !== false, 'public history uses the self-review label');
ck(strpos($src, "\$_POST['owner_self_approval'] ?? '') !== '1'") !== false, 'explicit self-review declaration required');
ck(strpos($src, 'check_admin_referer') !== false && strpos($src, "wp_nonce_field('scec08_'.\$handler.'_'.\$id)") !== false, 'CSRF nonce on every form including self-approval');
ck(strpos($src, 'wp_insert_user') === false && strpos($src, 'wp_create_user') === false, 'never creates user accounts');
echo "MEDIA-08.2 single-operator owner self-review: PASS\n";
