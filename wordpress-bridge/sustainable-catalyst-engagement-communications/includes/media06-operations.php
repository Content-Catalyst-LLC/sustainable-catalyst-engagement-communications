<?php
/**
 * MEDIA-06: manual, privileged editorial operations only.
 * Uses a locally stored RSA private key to sign a fresh, 90-second, request-bound
 * assertion. The key never leaves Bluehost; no token is saved to wp_options.
 * Backend independently verifies only site service identity, not WordPress humans.
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Media06_Operations {
    const PAGE = 'scec-media06';
    const META_ID = '_scec_media06_backend_id';
    const META_SHA = '_scec_media06_backend_sha';

    public static function boot() {
        add_action('admin_menu', array(__CLASS__, 'menu'));
        add_action('admin_post_scec_media06', array(__CLASS__, 'handle'));
    }
    public static function menu() {
        add_submenu_page('options-general.php', 'Media Operations', 'Media Operations (MEDIA-06)',
            'manage_options', self::PAGE, array(__CLASS__, 'screen'));
    }
    private static function value($name) {
        return defined($name) && is_string(constant($name)) ? trim(constant($name)) : '';
    }
    private static function organization() {
        return self::value('SCEC_MEDIA05_ORGANIZATION_ID');
    }
    private static function origin() {
        return SC_Media05_Bridge::approved_origin(self::value('SCEC_MEDIA05_API_ORIGIN'));
    }
    private static function key_path() {
        $path = self::value('SCEC_MEDIA06_PRIVATE_KEY_PATH');
        if ($path === '' || $path[0] !== '/' || !is_file($path) || !is_readable($path)) { return ''; }
        $perms = @fileperms($path);
        $actual = realpath($path);
        $webroot = realpath(ABSPATH);
        if ($perms === false || ($perms & 0077) !== 0 || !$actual || !$webroot ||
            strpos($actual, rtrim($webroot, DIRECTORY_SEPARATOR).DIRECTORY_SEPARATOR) === 0) { return ''; }
        return $actual;
    }
    public static function readiness() {
        return array(
            'enabled' => defined('SCEC_MEDIA06_ENABLED') && SCEC_MEDIA06_ENABLED === true,
            'https_origin' => self::origin() !== '',
            'organization' => preg_match('/^[a-f0-9-]{36}$/D', self::organization()) === 1,
            'private_signing_key' => self::key_path() !== '',
            'key_identifier' => preg_match('/^[A-Za-z0-9_-]{3,60}$/D', self::value('SCEC_MEDIA06_KEY_ID')) === 1,
        );
    }
    private static function active() {
        foreach (self::readiness() as $ok) { if (!$ok) { return false; } }
        return true;
    }
    private static function b64($str) {
        return rtrim(strtr(base64_encode($str), '+/', '-_'), '=');
    }
    private static function assertion($method, $path, $body) {
        $pem = @file_get_contents(self::key_path());
        if (!is_string($pem) || $pem === '' || strlen($pem) > 16384) { return ''; }
        $key = openssl_pkey_get_private($pem);
        unset($pem);
        if (!$key) { return ''; }
        $meta = openssl_pkey_get_details($key);
        if (!is_array($meta) || ($meta['type'] ?? -1) !== OPENSSL_KEYTYPE_RSA ||
            ($meta['bits'] ?? 0) < 3072) { return ''; }
        $now = time();
        $claims = array(
            'iss' => home_url(''),
            'aud' => 'scec-media06',
            'sub' => 'wordpress:media-ops',
            'org' => self::organization(),
            'iat' => $now, 'nbf' => $now-1, 'exp' => $now+90,
            'jti' => wp_generate_uuid4(),
            'method' => $method, 'path' => $path,
            'body_sha256' => hash('sha256', $body),
        );
        $header = array('alg'=>'RS256', 'typ'=>'JWT', 'kid'=>self::value('SCEC_MEDIA06_KEY_ID'));
        $signing = self::b64(wp_json_encode($header, JSON_UNESCAPED_SLASHES)) . '.' .
                   self::b64(wp_json_encode($claims, JSON_UNESCAPED_SLASHES));
        $signature = '';
        if (!openssl_sign($signing, $signature, $key, OPENSSL_ALGO_SHA256)) { return ''; }
        return $signing . '.' . self::b64($signature);
    }
    private static function call($method, $path, $payload = null) {
        if (!self::active() || !in_array($method, array('GET','POST'), true) ||
            strpos($path, '/v1/media-ops/') !== 0) {
            return array('ok'=>false,'reason'=>'not_configured');
        }
        $body = $payload === null ? '' : wp_json_encode($payload, JSON_UNESCAPED_SLASHES);
        if (!is_string($body) || strlen($body) > 8192) {
            return array('ok'=>false,'reason'=>'invalid_request');
        }
        $token = self::assertion($method, $path, $body);
        if ($token === '') { return array('ok'=>false,'reason'=>'signing_failure'); }
        $args = array('headers'=>array(
            'Authorization'=>'Bearer '.$token,
            'X-SCEC-Organization-ID'=>self::organization(),
            'Accept'=>'application/json',
        ),'sslverify'=>true,'reject_unsafe_urls'=>true,'redirection'=>0,
           'timeout'=>8,'limit_response_size'=>32768);
        if ($method === 'POST') {
            $args['headers']['Content-Type'] = 'application/json';
            $args['body'] = $body;
            $response = wp_safe_remote_post(self::origin().$path, $args);
        } else {
            $response = wp_safe_remote_get(self::origin().$path, $args);
        }
        unset($token);
        if (is_wp_error($response)) { return array('ok'=>false,'reason'=>'network_error'); }
        $code = (int)wp_remote_retrieve_response_code($response);
        if ($code < 200 || $code >= 300) { return array('ok'=>false,'reason'=>'backend_http_'.$code); }
        $data = json_decode(wp_remote_retrieve_body($response), true);
        if (!is_array($data) || ($data['release'] ?? '') !== 'MEDIA-06' ||
            ($data['organization_id'] ?? '') !== self::organization() ||
            ($data['publishing_enabled'] ?? false) !== false ||
            ($data['sending_enabled'] ?? false) !== false) {
            return array('ok'=>false,'reason'=>'unsafe_reply');
        }
        return array('ok'=>true,'data'=>$data);
    }
    private static function back($reason) {
        wp_safe_redirect(add_query_arg(array('page'=>self::PAGE,'scec_notice'=>$reason),
            admin_url('options-general.php')));
        exit;
    }
    public static function handle() {
        if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' || !current_user_can('manage_options')) {
            wp_die('Forbidden', '', 403);
        }
        $op = sanitize_key((string)($_POST['scec_operation'] ?? ''));
        $id = absint($_POST['package_id'] ?? 0);
        if (!in_array($op, array('status','register','reconcile','approve','reject','audit'), true)) {
            wp_die('Unsupported operation', '', 400);
        }
        check_admin_referer('scec_media06_'.$op.'_'.$id);
        if (!self::active()) { self::back('not_configured'); }
        if ($op === 'status') {
            if ($id !== 0) { self::back('invalid'); }
            $out = self::call('GET','/v1/media-ops/status');
            self::back($out['ok'] ? 'status_verified' : $out['reason']);
        }
        $package = SC_Media04_Workflow::get_package($id);
        if (!$package || !SC_Media04_Workflow::approved($package)) { self::back('approval_invalid'); }
        $envelope = SC_Media05_Bridge::envelope($package);
        if (!$envelope) { self::back('approval_invalid'); }
        $sha = $envelope['approved_package_sha256'];
        if ($op === 'register') {
            $user = get_current_user_id();
            $payload = array(
                'package'=>$envelope,
                'submitted_by'=>'wp:user:'.$user,
                'idempotency_key'=>hash('sha256',self::organization()."\n".$envelope['package_ref']."\n".$sha."\n".$user),
            );
            $out = self::call('POST','/v1/media-ops/packages',$payload);
            if ($out['ok'] && !empty($out['data']['package_id']) &&
                preg_match('/^[a-f0-9-]{36}$/D',$out['data']['package_id']) === 1) {
                update_post_meta($id,self::META_ID,$out['data']['package_id']);
                update_post_meta($id,self::META_SHA,$sha);
            }
        } else {
            $backend_id = (string)get_post_meta($id,self::META_ID,true);
            $stored_sha = (string)get_post_meta($id,self::META_SHA,true);
            if ($stored_sha !== $sha || preg_match('/^[a-f0-9-]{36}$/D',$backend_id) !== 1) {
                self::back('revision_changed');
            }
            $path = '/v1/media-ops/packages/'.$backend_id;
            if ($op === 'reconcile') {
                $out = self::call('GET',$path.'/reconcile?approved_sha256='.$sha);
            } elseif ($op === 'audit') {
                $out = self::call('GET',$path.'/audit');
            } else {
                $payload = array('actor_ref'=>'wp:user:'.get_current_user_id(),
                    'decision'=>$op === 'approve' ? 'approve' : 'reject',
                    'approved_package_sha256'=>$sha);
                $out = self::call('POST',$path.'/reviews',$payload);
            }
        }
        if (!$out['ok']) { self::back($out['reason']); }
        // Store only non-secret, bounded receipt metadata, not body, key or bearer.
        $receipt = array('checked_utc'=>gmdate('c'),'operation'=>$op);
        if (isset($out['data']['state'])) { $receipt['state'] = $out['data']['state']; }
        if (isset($out['data']['fingerprint_matches'])) {
            $receipt['fingerprint_matches'] = $out['data']['fingerprint_matches'] === true;
        }
        update_post_meta($id,'_scec_media06_last_receipt',$receipt);
        self::back('operation_accepted');
    }
    private static function form($op, $id, $label) {
        echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
        echo '<input type="hidden" name="action" value="scec_media06">';
        echo '<input type="hidden" name="scec_operation" value="'.esc_attr($op).'">';
        echo '<input type="hidden" name="package_id" value="'.(int)$id.'">';
        wp_nonce_field('scec_media06_'.$op.'_'.$id);
        echo '<button type="submit" class="button button-secondary">'.esc_html($label).'</button></form>';
    }
    public static function screen() {
        if (!current_user_can('manage_options')) { wp_die('Forbidden','',403); }
        echo '<div class="wrap"><h1>MEDIA-06 · Editorial Operations</h1>';
        echo '<p>Staging-only signed service requests. Two distinct reviewer attestations required. No federated human identity, automatic delivery, subscriptions, or external posting.</p>';
        echo '<h2>Configuration readiness</h2><ul>';
        foreach (self::readiness() as $name=>$ok) {
            echo '<li>'.esc_html(str_replace('_',' ',$name)).': <strong>'.
                ($ok ? 'Ready' : 'Not configured').'</strong></li>';
        }
        echo '</ul>';
        $notice=sanitize_key((string)($_GET['scec_notice'] ?? ''));
        if ($notice !== '') { echo '<div class="notice notice-info"><p>MEDIA-06: '.esc_html($notice).'</p></div>'; }
        if (self::active()) { self::form('status',0,'Check signed backend status'); }
        echo '<h2>Approved Media distribution packages</h2>';
        $items = get_posts(array('post_type'=>SC_Media04_Workflow::POST_TYPE,
            'post_status'=>'private','posts_per_page'=>30));
        $count=0;
        foreach ($items as $p) {
            if (!SC_Media04_Workflow::approved($p)) { continue; }
            $count++;
            $id=(int)$p->ID;
            echo '<div style="background:#fff;padding:12px;margin:12px 0;border:1px solid #ddd">';
            echo '<strong>'.esc_html($p->post_title).'</strong> (package #'.$id.')';
            $receipt=get_post_meta($id,'_scec_media06_last_receipt',true);
            if (is_array($receipt)) {
                echo '<p>Last accepted operation: '.esc_html((string)($receipt['operation'] ?? '')).
                    ' · '.esc_html((string)($receipt['state'] ?? 'pending')).'</p>';
            }
            if (self::active()) {
                self::form('register',$id,'Register approved revision');
                if (get_post_meta($id,self::META_ID,true)) {
                    self::form('reconcile',$id,'Reconcile fingerprint');
                    self::form('approve',$id,'Record reviewer approval');
                    self::form('reject',$id,'Reject revision');
                    self::form('audit',$id,'Check audit trail');
                }
            }
            echo '</div>';
        }
        if (!$count) { echo '<p>No approved, source-valid MEDIA-04 distribution package yet.</p>'; }
        echo '<p>Approval actors are WordPress assertions, not independently verified federated identities. MEDIA-06 remains non-production until identity and database acceptance.</p></div>';
    }
}
