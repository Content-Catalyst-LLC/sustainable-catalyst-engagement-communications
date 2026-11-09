<?php
/**
 * MEDIA-08 isolated tests of immutable-approval release gate.
 * These tests do NOT publish WordPress posts or run a web server.
 */
define('ABSPATH', '/media08-ci-test/');
function wp_json_encode($value, $flags=0) { return json_encode($value, $flags); }
require_once dirname(__DIR__) . '/includes/media08-press-room.php';
function ck($ok, $name) {
    if (!$ok) { fwrite(STDERR, "FAIL: ".$name."\n"); exit(1); }
}
$sha=SC_Media08_Press_Room::digest('Title','Summary','<p>Body</p>','press-release','','');
ck((bool)preg_match('/^[a-f0-9]{64}$/',$sha),'digest shape');
ck($sha === SC_Media08_Press_Room::digest('Title','Summary','<p>Body</p>','press-release','',''),'stable digest');
ck($sha !== SC_Media08_Press_Room::digest('Title 2','Summary','<p>Body</p>','press-release','',''),'edits invalidate sha');
$gate=array('approved', $sha, $sha, 41, 42, '', 1800000000);
ck(!SC_Media08_Press_Room::publication_gate(false, ...$gate),'disabled gate never releases');
ck(SC_Media08_Press_Room::publication_gate(true, ...$gate),'approved distinct reviewer passes');
ck(!SC_Media08_Press_Room::publication_gate(true,'in_review',$sha,$sha,41,42,'',1800000000),'review only blocked');
ck(!SC_Media08_Press_Room::publication_gate(true,'approved',$sha,str_repeat('a',64),41,42,'',1800000000),'changed source blocked');
ck(!SC_Media08_Press_Room::publication_gate(true,'approved',$sha,$sha,41,41,'',1800000000),'self approval blocked');
ck(!SC_Media08_Press_Room::publication_gate(true,'approved',$sha,$sha,41,0,'',1800000000),'missing reviewer blocked');
ck(!SC_Media08_Press_Room::publication_gate(true,'approved',$sha,$sha,41,42,'2028-01-01T00:00',1800000000),'active embargo blocked');
ck(SC_Media08_Press_Room::publication_gate(true,'approved',$sha,$sha,41,42,'2026-01-01T00:00',1800000000),'expired embargo passed');
ck(!SC_Media08_Press_Room::enabled(),'public release off without explicit wp-config flag');
echo "MEDIA-08 independent release gate: PASS\n";
