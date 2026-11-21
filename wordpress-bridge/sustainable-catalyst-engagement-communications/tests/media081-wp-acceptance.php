<?php
/**
 * MEDIA-08.1 WordPress acceptance, run INSIDE A DISPOSABLE STAGING SITE only:
 *   wp eval-file tests/media081-wp-acceptance.php <phase>
 * Drives the real admin-post handlers (nonces, capabilities, redirects) as an
 * administrator author and a separate `scec_press_reviewer` user. Phases:
 *   private  - flag off, no /press/ page: authoring, review rules, release blocked
 *   gated    - /press/ page published, flag still off: release still blocked
 *   public   - flag on: release, permanent URL, correction, withdrawal, embargo, tamper
 * Writes state for the HTTP checks to the file named by MEDIA081_STATE.
 */
if (!defined('WP_CLI') || (defined('WP_ENVIRONMENT_TYPE') && WP_ENVIRONMENT_TYPE === 'production') ||
    wp_get_environment_type() === 'production') {
    fwrite(STDERR, "refused: staging only\n"); exit(2);
}
$phase = $args[0] ?? '';
$state_file = getenv('MEDIA081_STATE') ?: sys_get_temp_dir() . '/media081-state.json';
$S = file_exists($state_file) ? json_decode(file_get_contents($state_file), true) : array();
$R = 'SC_Media08_Press_Room';
$M = '_scec_media08_';
// wp eval-file runs inside a function scope, so counters live on a class, not in globals.
final class Media081Count { public static $pass = 0; public static $fail = 0; public static $last = ''; }
function ck($ok, $name) {
    if ($ok) { Media081Count::$pass++; echo "PASS $name\n"; }
    else { Media081Count::$fail++; echo "FAIL $name [last action: " . Media081Count::$last . "]\n"; }
}

class Media081Redirect extends Exception {}
add_filter('wp_redirect', function ($loc) { throw new Media081Redirect($loc); }, 1);
add_filter('wp_die_handler', function () { return function ($msg, $title, $a) { throw new Media081Redirect('die:' . (is_string($msg) ? $msg : 'error')); }; });

/** Call one admin-post action as a user; returns the notice (or die:<code>) and id. */
function act($action, $user, $post) {
    wp_set_current_user($user);
    $id = (int)($post['id'] ?? 0);
    $_POST = $post + array('id' => $id);
    $_REQUEST = $_POST;
    $_REQUEST['_wpnonce'] = $_POST['_wpnonce'] = wp_create_nonce('scec08_' . $action . '_' . $id);
    $_SERVER['REQUEST_METHOD'] = 'POST';
    try { do_action('admin_post_scec08_' . $action); }
    catch (Media081Redirect $e) {
        $loc = $e->getMessage();
        if (strpos($loc, 'die:') === 0) { Media081Count::$last = "$action -> $loc"; return array($loc, $id); }
        parse_str((string)parse_url($loc, PHP_URL_QUERY), $q);
        Media081Count::$last = "$action -> " . ($q['notice'] ?? '') . ' id=' . ($q['id'] ?? '');
        return array($q['notice'] ?? '', (int)($q['id'] ?? 0));
    }
    return array('no_redirect', $id);
}
function st($id) { return (string)get_post_meta($id, '_scec_media08_state', true); }
function draft($title, $embargo = '') {
    return array('title' => $title, 'kind' => 'press-release',
        'summary' => 'SYNTHETIC staging summary for ' . $title . '.',
        'body' => '<p>SYNTHETIC staging body. Not a real announcement.</p>',
        'source_url' => '', 'embargo_until' => $embargo);
}

$admin = (int)get_user_by('login', 'staging-admin')->ID;
$reviewer_user = get_user_by('login', 'press-reviewer');
$rev = $reviewer_user ? (int)$reviewer_user->ID : 0;
ck($rev > 0 && in_array('scec_press_reviewer', $reviewer_user->roles, true), 'staging reviewer has the Press reviewer role');
$role = get_role('scec_press_reviewer');
ck($role && array_keys(array_filter($role->capabilities)) === array('read', 'scec_press_review'), 'reviewer role = read + scec_press_review only');
ck(!user_can($rev, 'manage_options') && !user_can($rev, 'edit_posts') && !user_can($rev, 'scec_press_publish') && !user_can($rev, 'scec_press_author'),
    'reviewer cannot administer, edit posts, author or publish');

if ($phase === 'private') {
    ck(!$R::enabled() && !$R::launch_ready(), 'flag off, not launched');
    list($n, $id) = act('save', $admin, draft('SYNTHETIC first release'));
    ck($n === 'saved' && st($id) === 'draft', 'author saves private draft');
    ck(get_post($id)->post_status === 'private', 'record is private');
    list($n) = act('save', $rev, draft('reviewer edit') + array('id' => $id));
    ck($n === 'die:Not authorized', 'reviewer cannot edit drafts (Not authorized)');
    list($n) = act('submit', $admin, array('id' => $id));
    ck($n === 'submitted' && st($id) === 'in_review', 'author submits for review');
    list($n) = act('save', $admin, draft('edit after submit') + array('id' => $id));
    ck($n === 'locked', 'submitted content is locked');
    list($n) = act('approve', $admin, array('id' => $id, 'check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1', 'check_institutional' => '1'));
    ck($n === 'independent_review_required' && st($id) === 'in_review', 'author cannot approve own release');
    list($n) = act('approve', $rev, array('id' => $id, 'check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1'));
    ck($n === 'review_incomplete', 'all four attestations required');
    list($n) = act('return', $rev, array('id' => $id, 'note' => ''));
    ck($n === 'note_required', 'return needs a note');
    list($n) = act('return', $rev, array('id' => $id, 'note' => 'Please tighten the summary.'));
    ck($n === 'returned' && st($id) === 'draft', 'reviewer returns to author');
    list($n) = act('save', $admin, draft('SYNTHETIC first release') + array('id' => $id));
    ck($n === 'saved' && (int)get_post_meta($id, $M . 'revision', true) === 2, 'author revises (revision 2)');
    act('submit', $admin, array('id' => $id));
    $sha = (string)get_post_meta($id, $M . 'submitted_sha', true);
    list($n) = act('approve', $rev, array('id' => $id, 'check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1', 'check_institutional' => '1'));
    ck($n === 'approved' && (int)get_post_meta($id, $M . 'reviewer_id', true) === $rev && get_post_meta($id, $M . 'approved_sha', true) === $sha,
        'independent reviewer approves the exact submitted fingerprint');
    list($n) = act('release', $rev, array('id' => $id));
    ck($n === 'die:Not authorized', 'reviewer cannot release (Not authorized)');
    list($n) = act('release', $admin, array('id' => $id));
    ck($n === 'press_page_missing' && st($id) === 'approved', 'release blocked without a published /press/ page');
    $media = do_shortcode('[sc_media]');
    ck(strpos($media, 'Not yet published') !== false && strpos($media, '/press/') === false, 'Media page Press & News still pending');
    ck(strpos(do_shortcode('[sc_press_room]'), 'No approved public press releases') !== false, 'Press Room projection empty');
    ck(do_shortcode('[sc_press_inquiry]') === '', 'MEDIA-09 inquiry link inert without SCEC_MEDIA09_PRESS_URL');
    $events = array_column($R::history($id), 'action');
    ck($events === array('created','submitted','returned','saved','submitted','approved'), 'append-only history: ' . implode(',', $events));
    $S['first'] = $id;
    // A second approved record with a future embargo, for the public phase.
    list($n, $e2) = act('save', $admin, draft('SYNTHETIC embargoed release', '2099-01-01T00:00'));
    act('submit', $admin, array('id' => $e2));
    act('approve', $rev, array('id' => $e2, 'check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1', 'check_institutional' => '1'));
    ck(st($e2) === 'approved', 'embargoed record approved');
    $S['embargoed'] = $e2;
}

if ($phase === 'gated') {
    ck(!$R::enabled() && (bool)$R::press_page() && !$R::launch_ready(), '/press/ page published but flag off: not launched');
    list($n) = act('release', $admin, array('id' => $S['first']));
    ck($n === 'release_blocked' && st($S['first']) === 'approved', 'release blocked while the flag is off');
    ck(strpos(do_shortcode('[sc_media]'), 'Not yet published') !== false, 'Media card still pending before launch');
}

if ($phase === 'public') {
    ck($R::launch_ready(), 'flag on and /press/ page published: launched');
    $id = $S['first'];
    list($n) = act('release', $admin, array('id' => $id));
    ck($n === 'released' && st($id) === 'released', 'administrator releases the approved record');
    $url = $R::permalink($id);
    ck((bool)preg_match('#/press/\d{4}/synthetic-first-release/$#', $url), 'permanent URL assigned: ' . $url);
    ck(get_post_meta($id, $M . 'reference', true) === 'SC-PR-' . gmdate('Y') . '-001', 'reference assigned');
    list($n) = act('release', $admin, array('id' => $S['embargoed']));
    ck($n === 'release_blocked' && st($S['embargoed']) === 'approved', 'future embargo blocks release');
    // Correction: a new reviewed record; the original's content is never touched.
    $orig_sha = $R::digest(get_post($id)->post_title, get_post_meta($id, $M.'summary', true), get_post_meta($id, $M.'body', true), 'press-release', '', '');
    list($n, $c) = act('correct', $admin, array('id' => $id));
    ck($n === 'correction_draft' && (int)get_post_meta($c, $M . 'corrects', true) === $id && st($c) === 'draft', 'correction starts as a new private draft');
    act('save', $admin, array('title' => 'Correction: SYNTHETIC first release', 'kind' => 'press-release',
        'summary' => 'SYNTHETIC corrected summary.', 'body' => '<p>SYNTHETIC corrected body.</p>', 'source_url' => '', 'embargo_until' => '', 'id' => $c));
    act('submit', $admin, array('id' => $c));
    list($n) = act('approve', $admin, array('id' => $c, 'check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1', 'check_institutional' => '1'));
    ck($n === 'independent_review_required', 'correction also needs the independent reviewer');
    act('approve', $rev, array('id' => $c, 'check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1', 'check_institutional' => '1'));
    list($n) = act('release', $admin, array('id' => $c));
    ck($n === 'released' && (int)get_post_meta($id, $M . 'corrected_by', true) === $c, 'correction released and linked from the original');
    $now_sha = $R::digest(get_post($id)->post_title, get_post_meta($id, $M.'summary', true), get_post_meta($id, $M.'body', true), 'press-release', '', '');
    ck($now_sha === $orig_sha && $R::public_state(get_post($id)) === 'released', 'original content unchanged and still public');
    $S['correction'] = $c;
    $S['correction_url'] = $R::permalink($c);
    $S['first_url'] = $url;
    // Withdrawal of the correction keeps a notice at its URL.
    list($n) = act('withdraw', $rev, array('id' => $c, 'reason' => 'x', 'confirm_withdraw' => '1'));
    ck($n === 'die:Not authorized', 'reviewer cannot withdraw (Not authorized)');
    list($n) = act('withdraw', $admin, array('id' => $c, 'reason' => '', 'confirm_withdraw' => '1'));
    ck($n === 'reason_required' && st($c) === 'released', 'withdrawal needs a public reason');
    list($n) = act('withdraw', $admin, array('id' => $c, 'reason' => 'SYNTHETIC withdrawal reason for staging.', 'confirm_withdraw' => '1'));
    ck($n === 'withdrawn' && $R::public_state(get_post($c)) === 'withdrawn', 'withdrawn with notice state');
    ck($R::structured_data(get_post($c)) === null, 'no NewsArticle data for a withdrawn release');
    $events = array_column($R::history($c), 'action');
    ck(end($events) === 'withdrawn' && in_array('released', $events, true), 'correction history records release then withdrawal');
    $sd = $R::structured_data(get_post($id));
    ck($sd['@type'] === 'NewsArticle' && $sd['url'] === $url && !empty($sd['datePublished']), 'NewsArticle structured data for the original');
    $media = do_shortcode('[sc_media]');
    ck(strpos($media, home_url('/press/')) !== false, 'Media page Press & News links to /press/ after launch');
}

if ($phase === 'tamper') {
    // Editing a released record outside the workflow must take it off public view, not rewrite it.
    $id = $S['first'];
    $body = get_post_meta($id, $M . 'body', true);
    update_post_meta($id, $M . 'body', $body . '<p>Silent edit</p>');
    ck($R::public_state(get_post($id)) === '', 'silently edited release is no longer public');
    update_post_meta($id, $M . 'body', $body);
    ck($R::public_state(get_post($id)) === 'released', 'restoring the approved text restores it');
}

if ($phase === 'killswitch') {
    ck(!$R::launch_ready(), 'flag off again: not launched');
    ck(strpos(do_shortcode('[sc_media]'), 'Not yet published') !== false, 'Media card reverts to pending');
    ck(strpos(do_shortcode('[sc_press_room]'), 'No approved public press releases') !== false, 'archive hidden');
}

file_put_contents($state_file, json_encode($S));
echo 'RESULT phase=' . $phase . ' pass=' . Media081Count::$pass . ' fail=' . Media081Count::$fail . "\n";
if (Media081Count::$fail) { exit(1); }
