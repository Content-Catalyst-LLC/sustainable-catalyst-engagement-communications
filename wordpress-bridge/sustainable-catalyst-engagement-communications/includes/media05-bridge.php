<?php
/**
 * MEDIA-05 — admin-initiated, metadata-only server-to-server preview bridge.
 * Never reads subscriber data, stores bearer credentials, posts to external social
 * accounts, or exposes privileged routes through public WordPress shortcodes.
 * All connection configuration is read from protected wp-config.php constants.
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Media05_Bridge {
    const PAGE = 'scec-media05';
    const RECEIPT_META = '_scec_media05_preview_receipt';
    const STATUS_OPTION = 'scec_media05_status_receipt';

    public static function boot() {
        add_action('admin_menu', array(__CLASS__, 'menu'));
        add_action('admin_post_scec_media05', array(__CLASS__, 'handle_action'));
    }

    public static function menu() {
        add_submenu_page('options-general.php', 'Media Backend Bridge', 'Media Backend Bridge',
            'manage_options', self::PAGE, array(__CLASS__, 'render_admin'));
    }

    private static function config($name) {
        return defined($name) && is_string(constant($name)) ? trim(constant($name)) : '';
    }

    /** Exact HTTPS origin only. Prevent accidental localhost, IP or redirect routing. */
    public static function approved_origin($input) {
        if (!is_string($input) || strlen($input) > 255) { return ''; }
        $p = wp_parse_url($input);
        if (!is_array($p) || strtolower((string)($p['scheme'] ?? '')) !== 'https' ||
            empty($p['host']) || isset($p['user']) || isset($p['pass']) || isset($p['port']) ||
            isset($p['query']) || isset($p['fragment']) || !in_array((string)($p['path'] ?? ''), array('', '/'), true)) { return ''; }
        $host = strtolower((string)$p['host']);
        if (strpos($host, '.') === false || strpos($host, '..') !== false ||
            !preg_match('/^[a-z0-9.-]+$/D', $host) ||
            preg_match('/(?:^|\.)(?:local|localhost|internal|invalid|test)$/D', $host) ||
            filter_var($host, FILTER_VALIDATE_IP)) { return ''; }
        $origin = 'https://' . $host;
        return wp_http_validate_url($origin . '/') ? $origin : '';
    }

    public static function readiness() {
        $origin = self::approved_origin(self::config('SCEC_MEDIA05_API_ORIGIN'));
        $org = self::config('SCEC_MEDIA05_ORGANIZATION_ID');
        $token = self::config('SCEC_MEDIA05_SERVICE_BEARER');
        $uuid = preg_match('/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/D', $org) === 1 && $org !== '00000000-0000-0000-0000-000000000000';
        $valid_token = strlen($token) >= 32 && strlen($token) <= 8192 && preg_match('/^[A-Za-z0-9._~-]+$/D', $token) === 1;
        return array(
            'enabled' => defined('SCEC_MEDIA05_ENABLED') && SCEC_MEDIA05_ENABLED === true,
            'https_origin_valid' => $origin !== '',
            'organization_configured' => $uuid,
            'service_identity_configured' => $valid_token,
        );
    }

    private static function active() {
        foreach (self::readiness() as $ok) { if (!$ok) { return false; } }
        return true;
    }

    public static function envelope($package) {
        if (!$package || !SC_Media04_Workflow::approved($package)) { return null; }
        $id = (int)$package->ID;
        $url = (string)get_post_meta($id, '_scec_media04_source_url', true);
        $source = SC_Media04_Workflow::source_post($url);
        if (!$source) { return null; }
        $channels = SC_Media04_Workflow::channels(get_post_meta($id, '_scec_media04_channels', true));
        $approved_hash = (string)get_post_meta($id, '_scec_media04_approved_hash', true);
        $approved_at = (string)get_post_meta($id, '_scec_media04_approved_utc', true);
        if (!preg_match('/^[a-f0-9]{64}$/D', $approved_hash) || !$approved_at || !$channels) { return null; }
        $source_hash = hash('sha256', (string)$source->ID . "\n" . (string)$source->post_title . "\n" .
            (string)$source->post_content . "\n" . (string)$source->post_modified_gmt);
        return array(
            'schema_version' => 'scec.media-bridge/1',
            'organization_id' => self::config('SCEC_MEDIA05_ORGANIZATION_ID'),
            'package_ref' => 'wp-media:' . $id,
            'source_url' => $url,
            'source_content_sha256' => $source_hash,
            'approved_package_sha256' => $approved_hash,
            'approved_at_utc' => $approved_at,
            'channels' => $channels,
            'source_published_attested' => true,
            'rights_review_attested' => true,
            'embargo_review_attested' => true,
            'export_mode' => 'metadata_preview_only',
        );
    }

    /** No automatic requests on page load: only an authorized admin-post action calls this. */
    public static function request_backend($operation, $envelope = null) {
        if (!self::active() || !in_array($operation, array('status', 'preview'), true)) {
            return array('ok' => false, 'reason' => 'disabled_or_unconfigured');
        }
        if ($operation === 'preview' && (!is_array($envelope) || ($envelope['export_mode'] ?? '') !== 'metadata_preview_only')) {
            return array('ok' => false, 'reason' => 'invalid_envelope');
        }
        $origin = self::approved_origin(self::config('SCEC_MEDIA05_API_ORIGIN'));
        if (!$origin) { return array('ok' => false, 'reason' => 'invalid_origin'); }
        $headers = array(
            'Authorization' => 'Bearer ' . self::config('SCEC_MEDIA05_SERVICE_BEARER'),
            'X-SCEC-Organization-ID' => self::config('SCEC_MEDIA05_ORGANIZATION_ID'),
            'Accept' => 'application/json',
        );
        $args = array('headers' => $headers, 'sslverify' => true,
            'reject_unsafe_urls' => true, 'redirection' => 0, 'timeout' => 8, 'limit_response_size' => 32768);
        $url = $origin . '/v1/media-bridge/' . $operation;
        if ($operation === 'preview') {
            $args['headers']['Content-Type'] = 'application/json';
            $args['body'] = wp_json_encode($envelope);
            $response = wp_safe_remote_post($url, $args);
        } else { $response = wp_safe_remote_get($url, $args); }
        if (is_wp_error($response)) { return array('ok' => false, 'reason' => 'network_unavailable'); }
        if ((int)wp_remote_retrieve_response_code($response) !== 200) {
            return array('ok' => false, 'reason' => 'backend_rejected');
        }
        $body = wp_remote_retrieve_body($response);
        if (!is_string($body) || strlen($body) > 32768) { return array('ok' => false, 'reason' => 'bad_reply'); }
        $result = json_decode($body, true);
        if (!is_array($result) || ($result['release'] ?? '') !== 'MEDIA-05' ||
            ($result['organization_id'] ?? '') !== self::config('SCEC_MEDIA05_ORGANIZATION_ID')) {
            return array('ok' => false, 'reason' => 'bad_reply');
        }
        if ($operation === 'status') {
            if (($result['publishing_enabled'] ?? null) !== false || ($result['sending_enabled'] ?? null) !== false ||
                ($result['persistence_enabled'] ?? null) !== false || ($result['production_certified'] ?? null) !== false) {
                return array('ok' => false, 'reason' => 'unsafe_backend_state');
            }
        } else {
            if (($result['package_ref'] ?? '') !== $envelope['package_ref'] ||
                ($result['approved_package_sha256'] ?? '') !== $envelope['approved_package_sha256'] ||
                ($result['delivery_enabled'] ?? null) !== false || ($result['auto_post_enabled'] ?? null) !== false ||
                ($result['persistence_enabled'] ?? null) !== false || ($result['preview_only'] ?? null) !== true ||
                !is_string($result['receipt_sha256'] ?? null) ||
                preg_match('/^[a-f0-9]{64}$/D', $result['receipt_sha256']) !== 1) {
                return array('ok' => false, 'reason' => 'unsafe_backend_state');
            }
        }
        return array('ok' => true, 'receipt' => $result);
    }

    private static function redirect_with_notice($reason, $id) {
        $url = add_query_arg(array('page' => self::PAGE, 'scec_notice' => $reason,
            'package' => (int)$id), admin_url('options-general.php'));
        wp_safe_redirect($url);
        exit;
    }

    public static function handle_action() {
        if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' || !current_user_can('manage_options')) {
            wp_die('Not authorized.', '', 403);
        }
        $op = sanitize_key((string)($_POST['scec_operation'] ?? ''));
        $id = absint($_POST['package_id'] ?? 0);
        if (!in_array($op, array('status','preview'), true)) { wp_die('Invalid action.', '', 400); }
        check_admin_referer('scec_media05_' . $op . '_' . $id);
        if (!self::active()) { self::redirect_with_notice('disabled', $id); }
        if ($op === 'status') {
            if ($id !== 0) { self::redirect_with_notice('invalid', $id); }
            $out = self::request_backend('status');
            if ($out['ok']) {
                update_option(self::STATUS_OPTION, array('checked_utc' => gmdate('c'), 'mode' => 'private-metadata-preview'), false);
            }
            self::redirect_with_notice($out['ok'] ? 'connected' : $out['reason'], 0);
        }
        $package = SC_Media04_Workflow::get_package($id);
        $envelope = self::envelope($package);
        if (!$envelope) { self::redirect_with_notice('approval_invalid', $id); }
        $out = self::request_backend('preview', $envelope);
        if ($out['ok']) {
            update_post_meta($id, self::RECEIPT_META, array(
                'approval_sha256' => $envelope['approved_package_sha256'],
                'receipt_sha256' => $out['receipt']['receipt_sha256'],
                'checked_utc' => gmdate('c'), 'mode' => 'backend_preview_only',
            ));
        }
        self::redirect_with_notice($out['ok'] ? 'previewed' : $out['reason'], $id);
    }

    private static function form($operation, $id, $label) {
        echo '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
        echo '<input type="hidden" name="action" value="scec_media05">';
        echo '<input type="hidden" name="scec_operation" value="' . esc_attr($operation) . '">';
        echo '<input type="hidden" name="package_id" value="' . (int)$id . '">';
        wp_nonce_field('scec_media05_' . $operation . '_' . $id);
        echo '<button type="submit" class="button button-secondary">' . esc_html($label) . '</button></form>';
    }

    public static function render_admin() {
        if (!current_user_can('manage_options')) { wp_die('Not authorized.', '', 403); }
        echo '<div class="wrap"><h1>MEDIA-05 · Engagement &amp; Communications Bridge</h1>';
        echo '<p>Private, manually initiated preview of approved public Media package metadata. No outbound publishing, subscriber transfer, account federation, or production activation.</p>';
        $checks = self::readiness();
        echo '<h2>Connection readiness</h2><ul>';
        foreach ($checks as $key => $valid) {
            echo '<li>' . esc_html(str_replace('_', ' ', $key)) . ': <strong>' . ($valid ? 'Ready' : 'Not configured') . '</strong></li>';
        }
        echo '</ul>';
        $notice = sanitize_key((string)($_GET['scec_notice'] ?? ''));
        $messages = array('connected' => 'Authenticated backend status accepted. Preview-only.',
            'previewed' => 'Backend preview receipt recorded. No content was sent to any external channel.',
            'disabled' => 'Bridge disabled or not configured.', 'network_unavailable' => 'Backend connection unavailable.',
            'backend_rejected' => 'Backend rejected the request. Check server-side authorization and tenant gates.',
            'unsafe_backend_state' => 'Backend response did not meet fail-closed safety checks.',
            'bad_reply' => 'Backend response was not valid.', 'approval_invalid' => 'Package approval is missing or invalidated.',
            'invalid' => 'Invalid request.', 'invalid_envelope' => 'Invalid envelope.', 'invalid_origin' => 'Invalid HTTPS origin.');
        if (isset($messages[$notice])) {
            echo '<div class="notice notice-info"><p>' . esc_html($messages[$notice]) . '</p></div>';
        }
        if (self::active()) { self::form('status', 0, 'Check authenticated backend status'); }
        echo '<h2>Approved WordPress Media packages</h2>';
        $items = get_posts(array('post_type' => SC_Media04_Workflow::POST_TYPE, 'post_status' => 'private',
            'posts_per_page' => 30, 'orderby' => 'date', 'order' => 'DESC', 'suppress_filters' => false));
        $printed = 0;
        foreach ($items as $p) {
            if (!SC_Media04_Workflow::approved($p)) { continue; }
            $printed++;
            echo '<div style="background:#fff;border:1px solid #ddd;padding:14px;margin:12px 0;max-width:850px">';
            echo '<strong>' . esc_html($p->post_title) . '</strong> <span>(package #' . (int)$p->ID . ')</span>';
            $receipt = get_post_meta((int)$p->ID, self::RECEIPT_META, true);
            $approved = get_post_meta((int)$p->ID, '_scec_media04_approved_hash', true);
            if (is_array($receipt) && ($receipt['approval_sha256'] ?? '') === $approved) {
                echo '<p>Last backend preview receipt: <code>' . esc_html(substr((string)$receipt['receipt_sha256'], 0, 16)) . '…</code> (not publishing authorization)</p>';
            }
            if (self::active()) { self::form('preview', (int)$p->ID, 'Review package with backend'); }
            echo '</div>';
        }
        if (!$printed) { echo '<p>No currently approved, source-valid Media distribution packages.</p>'; }
        echo '<p><strong>Configuration:</strong> set the four MEDIA-05 constants in the protected WordPress configuration and independently configure the backend tenant/identity allowlists. Never paste bearer tokens into this screen.</p>';
        echo '</div>';
    }
}
