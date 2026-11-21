<?php
/**
 * MEDIA-08.1 WordPress acceptance, run INSIDE A DISPOSABLE STAGING SITE only:
 *   wp eval-file tests/media081-wp-acceptance.php <phase>
 * Drives the real admin-post handlers (nonces, capabilities, redirects) as an
 * administrator author and a separate `scec_press_reviewer` user. Phases:
 *   private  - flag off, no /press/ page: authoring, review rules, release blocked
 *   gated    - /press/ page published, flag still off: release still blocked
 *   public   - flag on: release, permanent URL, correction, withdrawal, embargo, tamper
 *   single   - SCEC_MEDIA08_SINGLE_OPERATOR_OWNER set: owner self-review, positive and negative
 *   single_off - owner constant removed/non-admin: releases kept, new self-approval refused
 *   revise   - in-place editing: working revision, publish, correction notice, restore, reopen
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

if ($phase === 'single') {
    // Single-operator mode: SCEC_MEDIA08_SINGLE_OPERATOR_OWNER = staging-admin.
    $admin2 = (int)get_user_by('login', 'staging-admin2')->ID;
    $all = array('check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1', 'check_institutional' => '1');
    ck($R::single_operator_owner() === $admin, 'single-operator owner configured');
    list($n, $id) = act('save', $admin, draft('SYNTHETIC owner release'));
    act('submit', $admin, array('id' => $id));
    $sha = (string)get_post_meta($id, $M . 'submitted_sha', true);
    list($n) = act('approve', $admin, array('id' => $id) + $all);
    ck($n === 'self_review_declaration_required' && st($id) === 'in_review', 'owner self-approval needs the explicit declaration');
    list($n) = act('approve', $admin, array('id' => $id, 'owner_self_approval' => '1', 'check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1'));
    ck($n === 'review_incomplete' && st($id) === 'in_review', 'owner self-approval still needs all four attestations');
    // Forged request: wrong nonce is refused before any state change.
    wp_set_current_user($admin);
    $_POST = $_REQUEST = array('id' => $id, 'owner_self_approval' => '1', '_wpnonce' => wp_create_nonce('scec08_approve_999999')) + $all;
    try { do_action('admin_post_scec08_approve'); $forged = 'no_redirect'; } catch (Media081Redirect $e) { $forged = $e->getMessage(); }
    ck(strpos($forged, 'die:') === 0 && st($id) === 'in_review', 'self-approval with a forged nonce refused (CSRF)');
    list($n) = act('approve', $rev, array('id' => $id, 'owner_self_approval' => '1') + $all);
    ck($n === 'approved' && get_post_meta($id, $M . 'approval_mode', true) === 'independent', 'a separate reviewer approval stays independent');
    // Reset that record and use a fresh one for the self-review path.
    list($n, $own) = act('save', $admin, draft('SYNTHETIC single operator release'));
    act('submit', $admin, array('id' => $own));
    $sha = (string)get_post_meta($own, $M . 'submitted_sha', true);
    list($n) = act('approve', $admin, array('id' => $own, 'owner_self_approval' => '1') + $all);
    ck($n === 'approved' && st($own) === 'approved', 'owner self-approves with declaration and attestations');
    ck(get_post_meta($own, $M . 'approval_mode', true) === 'owner_self' && (int)get_post_meta($own, $M . 'reviewer_id', true) === $admin &&
        get_post_meta($own, $M . 'approved_sha', true) === $sha && get_post_meta($own, $M . 'approved_at', true) !== '', 'self-approval records mode, identity, time and fingerprint');
    $ev = $R::history($own); $last = end($ev);
    ck($last['action'] === 'owner_self_approved' && (int)$last['user'] === $admin && $last['sha256'] === $sha &&
        strpos($last['note'], 'not independent review') !== false && strpos($last['note'], 'decision: approved') !== false, 'history records the owner decision as self-review');
    // Non-owner administrator cannot self-approve.
    list($n, $o2) = act('save', $admin2, draft('SYNTHETIC second admin release'));
    act('submit', $admin2, array('id' => $o2));
    list($n) = act('approve', $admin2, array('id' => $o2, 'owner_self_approval' => '1') + $all);
    ck($n === 'independent_review_required' && st($o2) === 'in_review', 'non-owner administrator cannot self-approve');
    list($n) = act('approve', $rev, array('id' => $own, 'owner_self_approval' => '1') + $all);
    ck($n === 'invalid_state', 'approved record cannot be re-approved');
    list($n) = act('release', $rev, array('id' => $own));
    ck($n === 'die:Not authorized', 'reviewer role still cannot release');
    list($n) = act('release', $admin, array('id' => $own));
    ck($n === 'released' && $R::public_state(get_post($own)) === 'released', 'owner-approved release goes public');
    $html = $R::single(get_post($own));
    ck(strpos($html, 'single-operator self-review; not independent review') !== false && strpos($html, 'self-reviewed, not independently reviewed') !== false,
        'public page discloses self-review');
    ck(strpos($html, 'Approved by an independent reviewer') === false && strpos($html, 'approved by a reviewer other than its author') === false,
        'public page never calls self-review independent');
    ck(strpos($R::single(get_post($S['first'])), 'Approved by an independent reviewer') !== false, 'independent releases keep their label');
    $body = get_post_meta($own, $M . 'body', true);
    update_post_meta($own, $M . 'body', $body . '<p>Silent edit</p>');
    ck($R::public_state(get_post($own)) === '', 'silently edited owner release leaves public view');
    update_post_meta($own, $M . 'body', $body);
    list($n, $c) = act('correct', $admin, array('id' => $own));
    ck($n === 'correction_draft' && st($c) === 'draft', 'owner release can be corrected through a new record');
    // An owner-approved record left unreleased, for the mode-off phase.
    list($n, $pend) = act('save', $admin, draft('SYNTHETIC pending owner release'));
    act('submit', $admin, array('id' => $pend));
    act('approve', $admin, array('id' => $pend, 'owner_self_approval' => '1') + $all);
    ck(st($pend) === 'approved', 'second owner-approved record pending');
    $S['owner'] = $own; $S['owner_url'] = $R::permalink($own); $S['owner_pending'] = $pend;
}

if ($phase === 'revise') {
    // In-place editing of a released record (owner mode on): working revision, publish, correction, restore.
    $admin2 = (int)get_user_by('login', 'staging-admin2')->ID;
    $all = array('check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1', 'check_institutional' => '1');
    $id = $S['owner'];
    $p0 = get_post($id);
    $url0 = $R::permalink($id); $ref0 = get_post_meta($id, $M.'reference', true); $rel0 = get_post_meta($id, $M.'released_at', true);
    $body0 = get_post_meta($id, $M.'body', true);
    $sha0 = $R::sha_of(array('title'=>$p0->post_title,'summary'=>get_post_meta($id,$M.'summary',true),'body'=>$body0,'kind'=>'press-release','source_url'=>'','embargo'=>''));
    $edit = array('id' => $id, 'title' => 'SYNTHETIC single operator release', 'kind' => 'press-release',
        'summary' => get_post_meta($id, $M.'summary', true), 'source_url' => '',
        'body' => '<h2>Revised heading</h2><p>SYNTHETIC revised body with <a href="https://example.org/a">a link</a> &amp; "quotes".</p><ul><li>one</li></ul>' .
                  '[caption id="attachment_1" align="aligncenter" width="300"]<img src="https://example.org/x.png" alt="Chart" width="300" height="200" /> SYNTHETIC caption[/caption]');
    list($n) = act('save_update', $admin, array('body' => $body0, 'title' => $p0->post_title) + $edit);
    ck($n === 'no_changes', 'saving identical text is a no-op');
    list($n) = act('save_update', $admin, array('body' => str_replace("\n", "\r\n", rtrim($body0)), 'title' => $p0->post_title) + $edit);
    ck($n === 'no_changes' && !$R::pending($id), 'browser CRLF line breaks and trailing whitespace alone are a no-op');
    list($n) = act('save_update', $rev, $edit);
    ck($n === 'die:Not authorized', 'reviewer role cannot edit a release');
    list($n) = act('save_update', $admin, $edit);
    $u = $R::pending($id);
    ck($n === 'update_saved' && $u && $u['by'] === $admin, 'owner saves a working revision of the released record');
    ck(get_post_meta($id, $M.'body', true) === $body0 && $R::public_state(get_post($id)) === 'released' &&
        strpos($R::single(get_post($id)), 'Revised heading') === false, 'published text stays live while the revision is pending');
    $snaps = $R::snapshots($id);
    $last = end($snaps);
    ck(in_array($sha0, array_column($snaps, 'sha256'), true) && $last['origin'] === 'update' && $last['sha256'] === $u['sha256'],
        'published text and the working revision are both snapshotted');
    $base_n = (int)array_search($sha0, array_column($snaps, 'sha256', 'n'), true);
    // A release from before snapshots existed (as in production): the first edit records a baseline.
    $legacy = $S['first'];
    delete_post_meta($legacy, $M.'snapshot');
    $lp = get_post($legacy);
    $lsha = $R::sha_of(array('title'=>$lp->post_title,'summary'=>get_post_meta($legacy,$M.'summary',true),'body'=>get_post_meta($legacy,$M.'body',true),
        'kind'=>get_post_meta($legacy,$M.'kind',true),'source_url'=>'','embargo'=>get_post_meta($legacy,$M.'embargo_until',true)));
    list($n) = act('save_update', $admin, array('id' => $legacy, 'title' => $lp->post_title, 'kind' => 'press-release',
        'summary' => get_post_meta($legacy,$M.'summary',true), 'source_url' => '', 'body' => '<p>SYNTHETIC legacy edit.</p>'));
    $ls = $R::snapshots($legacy);
    ck($n === 'update_saved' && $ls[1]['origin'] === 'baseline' && $ls[1]['sha256'] === $lsha && $ls[2]['origin'] === 'update',
        'release without snapshots gets a baseline of its published text before the first edit');
    act('discard_update', $admin, array('id' => $legacy));
    ck(strpos($u['content']['body'], '"quotes"') !== false && strpos(end($snaps)['body'], '"quotes"') !== false, 'quotes and markup survive storage (slashing)');
    ck(wp_text_diff($R::snapshots($id)[$base_n]['body'], $u['content']['body']) !== '', 'comparison produces a diff');
    // Publish: negative checks first.
    $pub = array('id' => $id, 'update_sha' => $u['sha256'], 'change_type' => 'editorial', 'owner_self_approval' => '1') + $all;
    list($n) = act('publish_update', $rev, $pub);
    ck($n === 'die:Not authorized', 'reviewer role cannot publish an update');
    list($n) = act('publish_update', $admin, array('update_sha' => str_repeat('0', 64)) + $pub);
    ck($n === 'update_changed', 'publishing a different fingerprint than the working revision is refused');
    list($n) = act('publish_update', $admin, array_diff_key($pub, array('owner_self_approval' => 1)));
    ck($n === 'self_review_declaration_required', 'owner publishing own revision needs the self-review declaration');
    list($n) = act('publish_update', $admin, array_diff_key($pub, array('check_privacy' => 1)));
    ck($n === 'review_incomplete', 'all four attestations required for an update');
    list($n) = act('publish_update', $admin, array('change_type' => '') + $pub);
    ck($n === 'change_type_required', 'change type required');
    list($n) = act('publish_update', $admin, array('change_type' => 'correction', 'public_note' => '') + $pub);
    ck($n === 'correction_notice_required', 'a factual correction requires a public notice');
    ck(get_post_meta($id, $M.'body', true) === $body0 && $R::pending($id), 'refused publishes changed nothing');
    list($n) = act('publish_update', $admin, $pub);
    $p1 = get_post($id);
    ck($n === 'update_published' && !$R::pending($id), 'owner publishes the editorial update');
    ck($R::permalink($id) === $url0 && get_post_meta($id, $M.'reference', true) === $ref0 && get_post_meta($id, $M.'released_at', true) === $rel0,
        'permanent URL, reference and publication date unchanged');
    ck($R::public_state($p1) === 'released' && get_post_meta($id, $M.'released_sha', true) === $u['sha256'] &&
        get_post_meta($id, $M.'approval_mode', true) === 'owner_self', 'new text is the public release, approved by recorded owner self-review');
    $html = $R::single($p1);
    ck(strpos($html, 'Revised heading') !== false && strpos($html, '<figure') !== false && strpos($html, 'SYNTHETIC caption') !== false &&
        strpos($html, '[caption') === false, 'public page shows the update with headings and a captioned image');
    ck(strpos($html, 'scec-press-notice-correction') === false && strpos($html, 'Updated <time') !== false,
        'editorial update: no correction notice, dated "Updated" line');
    ck(strpos($html, 'self-reviewed, not independently reviewed') !== false, 'self-review still disclosed after the update');
    $sd = $R::structured_data($p1);
    ck($sd['datePublished'] === $rel0 && $sd['dateModified'] === get_post_meta($id, $M.'updated_at', true) && !isset($sd['correction']),
        'NewsArticle keeps datePublished, sets dateModified, no correction');
    $ev = array_column($R::history($id), 'action');
    ck(in_array('update_saved', $ev, true) && end($ev) === 'update_published', 'history records update_saved and update_published');
    // A non-owner administrator can publish someone else's revision as independent review.
    $edit2 = array('body' => '<h2>Revised heading</h2><p>SYNTHETIC body, figure 12 stated correctly.</p>') + $edit;
    act('save_update', $admin, $edit2);
    $u2 = $R::pending($id);
    list($n) = act('publish_update', $admin2, array('id' => $id, 'update_sha' => $u2['sha256'], 'change_type' => 'correction',
        'public_note' => 'An earlier version stated figure 11; the correct figure is 12.') + $all);
    $p2 = get_post($id);
    ck($n === 'update_published' && get_post_meta($id, $M.'approval_mode', true) === 'independent', 'another publisher publishes it as independent review');
    $html = $R::single($p2);
    ck(strpos($html, 'scec-press-notice-correction') !== false && strpos($html, 'the correct figure is 12') !== false, 'correction notice shown on the same release');
    ck(strpos($html, 'approved by a reviewer other than its author') !== false && strpos($html, 'not independently reviewed') === false,
        'disclosure follows the current approval');
    $sd = $R::structured_data($p2);
    ck(isset($sd['correction']['@type']) && $sd['correction']['@type'] === 'CorrectionComment', 'NewsArticle carries a CorrectionComment');
    $ev = array_column($R::history($id), 'action');
    ck(end($ev) === 'correction_published', 'history records correction_published');
    // Restore the original published text (baseline) as a new working revision, then publish it.
    list($n) = act('restore', $admin, array('id' => $id, 'snapshot' => $base_n));
    $u3 = $R::pending($id);
    ck($n === 'restored' && $u3 && $u3['sha256'] === $sha0 && get_post_meta($id, $M.'body', true) !== $body0, 'restore stages the baseline; public text unchanged until published');
    list($n) = act('discard_update', $admin, array('id' => $id));
    ck($n === 'update_discarded' && !$R::pending($id), 'working revision can be discarded');
    act('restore', $admin, array('id' => $id, 'snapshot' => $base_n));
    list($n) = act('publish_update', $admin, array('id' => $id, 'update_sha' => $sha0, 'change_type' => 'editorial', 'owner_self_approval' => '1') + $all);
    ck($n === 'update_published' && get_post_meta($id, $M.'body', true) === $body0 && $R::public_state(get_post($id)) === 'released', 'rollback to the original text published');
    ck(count($R::snapshots($id)) >= 5 && $R::snapshots($id)[$base_n]['sha256'] === $sha0, 'all snapshots kept (append-only)');
    // Tamper protection still applies after updates.
    update_post_meta($id, $M.'body', $body0 . '<p>Silent edit</p>');
    ck($R::public_state(get_post($id)) === '', 'out-of-workflow edit still removes the release');
    update_post_meta($id, $M.'body', $body0);
    // Unreleased: Edit release from review returns to draft and clears approval; drafts snapshot.
    list($n, $d) = act('save', $admin, draft('SYNTHETIC reopen release'));
    act('submit', $admin, array('id' => $d));
    act('approve', $admin, array('id' => $d, 'owner_self_approval' => '1') + $all);
    list($n) = act('reopen', $rev, array('id' => $d));
    ck($n === 'die:Not authorized', 'reviewer cannot reopen');
    list($n) = act('reopen', $admin, array('id' => $d));
    ck($n === 'reopened' && st($d) === 'draft' && get_post_meta($d, $M.'approved_sha', true) === '' && get_post_meta($d, $M.'approval_mode', true) === '',
        'Edit release on an approved draft returns it to draft and clears approval');
    list($n) = act('release', $admin, array('id' => $d));
    ck($n === 'release_blocked', 'reopened draft cannot be released');
    list($n) = act('save', $admin, draft('SYNTHETIC reopen release v2') + array('id' => $d));
    ck(count($R::snapshots($d)) === 2, 'each draft save is snapshotted');
    list($n) = act('restore', $admin, array('id' => $d, 'snapshot' => 1));
    ck($n === 'restored' && get_post($d)->post_title === 'SYNTHETIC reopen release' && st($d) === 'draft', 'draft restore writes a new revision');
    // Withdrawn releases cannot be edited in place.
    list($n) = act('save_update', $admin, array('id' => $S['correction']) + $edit);
    ck($n === 'invalid_state', 'withdrawn release is not editable in place');
    // Leave a pending revision for the HTTP check: public shows published text.
    act('save_update', $admin, array('body' => '<p>SYNTHETIC pending text not yet public.</p>') + $edit);
    $S['owner_preview_id'] = $id;
}

if ($phase === 'single_off') {
    // SCEC_MEDIA08_SINGLE_OPERATOR_OWNER removed (or pointed at a non-administrator).
    ck($R::single_operator_owner() === 0, 'single-operator mode off');
    ck($R::public_state(get_post($S['owner'])) === 'released', 'already released owner-approved release stays public');
    list($n) = act('release', $admin, array('id' => $S['owner_pending']));
    ck($n === 'release_blocked' && st($S['owner_pending']) === 'approved', 'unreleased self-approval cannot be released once the mode is off');
    list($n, $x) = act('save', $admin, draft('SYNTHETIC mode off release'));
    act('submit', $admin, array('id' => $x));
    list($n) = act('approve', $admin, array('id' => $x, 'owner_self_approval' => '1', 'check_rights' => '1', 'check_source' => '1', 'check_privacy' => '1', 'check_institutional' => '1'));
    ck($n === 'independent_review_required', 'self-approval refused when the mode is off');
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
