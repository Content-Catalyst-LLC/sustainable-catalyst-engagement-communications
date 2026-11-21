<?php
/**
 * MEDIA-08.3 isolated tests: in-place editing contract. No WordPress, database or web server.
 * Behaviour (handlers, transactions, rendering) is covered by the staging phase `revise`.
 */
define('ABSPATH', '/media083-ci-test/');
function wp_json_encode($value, $flags=0) { return json_encode($value, $flags); }
require_once dirname(__DIR__) . '/includes/media08-press-room.php';
function ck($ok, $name) { if (!$ok) { fwrite(STDERR, "FAIL: ".$name."\n"); exit(1); } }
$R = 'SC_Media08_Press_Room';
$c = array('title'=>'T','summary'=>'S','body'=>'<p>B</p>','kind'=>'press-release','source_url'=>'','embargo'=>'');
ck($R::sha_of($c) === $R::digest('T','S','<p>B</p>','press-release','',''), 'working revisions use the release fingerprint definition');
ck(array_keys($R::CHANGE_TYPES) === array('editorial','correction'), 'two change types: editorial and factual correction');
$src = file_get_contents(dirname(__DIR__) . '/includes/media08-press-room.php');
ck(strpos($src, "\$wpdb->query('START TRANSACTION')") !== false && strpos($src, "\$wpdb->query('COMMIT')") !== false &&
   strpos($src, "\$wpdb->query('ROLLBACK')") !== false, 'published text replaced in one transaction');
ck(strpos($src, "if (\$type === 'correction' && \$note === '') { self::back('correction_notice_required',\$id); }") !== false, 'factual corrections need a public notice');
ck(strpos($src, "hash_equals((string)\$u['sha256'], (string)(\$_POST['update_sha'] ?? ''))") !== false, 'publishes only the exact working revision shown');
ck(strpos($src, "self::admin_check('scec08_publish_update',\$id,self::CAP_PUBLISH)") !== false &&
   strpos($src, "self::admin_check('scec08_save_update',\$id,self::CAP_AUTHOR)") !== false &&
   strpos($src, "self::admin_check('scec08_restore',\$id,self::CAP_AUTHOR)") !== false &&
   strpos($src, "self::admin_check('scec08_reopen',\$id,self::CAP_AUTHOR)") !== false, 'capability + nonce on every new action');
ck(strpos($src, "wp_verify_nonce((string)(\$_GET['_wpnonce'] ?? ''), 'scec08_preview_' . \$id)") !== false &&
   strpos($src, "add_filter('wp_robots', 'wp_robots_no_robots')") !== false, 'preview needs sign-in + nonce and is noindex');
ck(strpos($src, "add_post_meta(\$id, self::META . 'snapshot'") !== false && strpos($src, "update_post_meta(\$id, self::META . 'snapshot'") === false &&
   strpos($src, "delete_post_meta(\$id, self::META . 'snapshot'") === false, 'snapshots are append-only');
ck(strpos($src, "wp_editor(\$c['body'], 'scec08body'") !== false && strpos($src, "'media_buttons'=>true") !== false, 'WordPress editor with Media Library');
ck(strpos($src, 'wp_mail(') === false && strpos($src, 'wp_remote_') === false && strpos($src, 'wp_insert_user') === false, 'no mail, remote HTTP or user creation');
ck(strpos($src, "'entity_encoding'=>'named'") !== false && strpos($src, '8212,mdash') !== false, 'visual editor keeps named typographic entities');
echo "MEDIA-08.3 in-place editing contract: PASS\n";
