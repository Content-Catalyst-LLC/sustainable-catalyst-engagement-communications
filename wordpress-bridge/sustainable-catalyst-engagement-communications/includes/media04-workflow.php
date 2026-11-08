<?php
/**
 * MEDIA-04 — WordPress-authoritative editorial/distribution package workflow.
 * This module NEVER sends or posts to Substack, YouTube, LinkedIn, or social APIs.
 * Only site administrators can create, review, approve, or export packages.
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Media04_Workflow {
    const POST_TYPE = 'scec_media_package';
    const PAGE = 'scec-media04';
    const META = '_scec_media04_';
    const SCHEMA_VERSION = 'media-distribution-package/1.0';
    const CHANNELS = array(
        'substack' => 'Substack newsletter',
        'youtube' => 'YouTube community / description',
        'linkedin' => 'LinkedIn',
        'x' => 'X / Twitter',
        'facebook' => 'Facebook',
        'instagram' => 'Instagram',
        'threads' => 'Threads',
        'bluesky' => 'Bluesky',
        'mastodon' => 'Mastodon',
    );
    public static function boot() {
        add_action('init', array(__CLASS__, 'register_type'));
        add_action('admin_menu', array(__CLASS__, 'menu'));
        add_action('admin_enqueue_scripts', array(__CLASS__, 'enqueue_admin'));
        add_action('admin_post_scec_media04', array(__CLASS__, 'handle_action'));
    }
    public static function register_type() {
        // Not public, not queryable, no API route, no normal post editor.
        // All capabilities map to manage_options; admin-post checks it again.
        $caps = array(
            'edit_post' => 'manage_options', 'read_post' => 'manage_options',
            'delete_post' => 'manage_options', 'edit_posts' => 'manage_options',
            'edit_others_posts' => 'manage_options', 'publish_posts' => 'manage_options',
            'read_private_posts' => 'manage_options', 'delete_posts' => 'manage_options',
            'delete_private_posts' => 'manage_options', 'delete_published_posts' => 'manage_options',
            'delete_others_posts' => 'manage_options', 'edit_private_posts' => 'manage_options',
            'edit_published_posts' => 'manage_options', 'create_posts' => 'manage_options',
        );
        register_post_type(self::POST_TYPE, array(
            'label' => 'Media distribution packages', 'public' => false, 'publicly_queryable' => false,
            'show_ui' => false, 'show_in_rest' => false, 'exclude_from_search' => true,
            'rewrite' => false, 'has_archive' => false, 'supports' => array('title', 'author', 'revisions'),
            'capability_type' => 'post', 'capabilities' => $caps, 'map_meta_cap' => false,
        ));
    }
    public static function menu() {
        add_submenu_page('options-general.php', 'Media Distribution', 'Media Distribution', 'manage_options', self::PAGE, array(__CLASS__, 'render_admin'));
    }
    public static function enqueue_admin($hook) {
        if ($hook !== 'settings_page_' . self::PAGE) { return; }
        wp_enqueue_style('scec-media04-admin', plugins_url('assets/media04-admin.css', dirname(__DIR__) . '/sustainable-catalyst-engagement-communications.php'), array(), SC_Engagement_Bridge_882::VERSION);
        wp_enqueue_script('scec-media04-admin', plugins_url('assets/media04-admin.js', dirname(__DIR__) . '/sustainable-catalyst-engagement-communications.php'), array(), SC_Engagement_Bridge_882::VERSION, true);
    }
    public static function channels($raw) {
        $allowed = array_keys(self::CHANNELS);
        if (!is_array($raw)) { return array(); }
        $selected = array_values(array_unique(array_filter($raw, function($value) use ($allowed) {
            return is_string($value) && in_array($value, $allowed, true);
        })));
        return array_values(array_filter($allowed, function($channel) use ($selected) { return in_array($channel, $selected, true); }));
    }
    /** Source authority is an already published, unprotected local WordPress post/page. */
    public static function source_post($raw) {
        if (!is_string($raw) || strlen($raw) > 2048) { return null; }
        $url = trim($raw);
        $p = wp_parse_url($url);
        $home = wp_parse_url(home_url('/'));
        if (!is_array($p) || !is_array($home) || strtolower((string)($p['scheme'] ?? '')) !== 'https' ||
            strtolower((string)($p['host'] ?? '')) !== strtolower((string)($home['host'] ?? '')) ||
            isset($p['port']) || isset($p['user']) || isset($p['pass']) || isset($p['query']) || isset($p['fragment'])) { return null; }
        $id = (int)url_to_postid($url);
        if ($id <= 0) { return null; }
        $post = get_post($id);
        if (!$post || !in_array($post->post_type, array('post', 'page'), true) ||
            $post->post_status !== 'publish' || post_password_required($post)) { return null; }
        $canonical = get_permalink($post);
        if (!is_string($canonical) || rtrim($canonical, '/') !== rtrim($url, '/')) { return null; }
        return $post;
    }
    private static function mget($post_id, $key, $fallback = '') {
        $value = get_post_meta($post_id, self::META . $key, true);
        return $value === '' ? $fallback : $value;
    }
    private static function mset($post_id, $key, $value) {
        update_post_meta($post_id, self::META . $key, $value);
    }
    public static function get_package($id) {
        $post = get_post((int)$id);
        if (!$post || $post->post_type !== self::POST_TYPE || $post->post_status !== 'private') { return null; }
        return $post;
    }
    private static function source_fingerprint($source) {
        return hash('sha256', (string)$source->ID . "\n" . (string)$source->post_title . "\n" .
            (string)$source->post_content . "\n" . (string)$source->post_modified_gmt);
    }
    public static function fingerprint($package, $source = null) {
        if (!$package) { return ''; }
        if (!$source) { $source = self::source_post((string)self::mget($package->ID, 'source_url')); }
        if (!$source) { return ''; }
        $fields = array(
            'schema' => self::SCHEMA_VERSION,
            'title' => $package->post_title,
            'summary' => (string)self::mget($package->ID, 'summary'),
            'source' => get_permalink($source),
            'source_sha256' => self::source_fingerprint($source),
            'channels' => self::channels(self::mget($package->ID, 'channels', array())),
        );
        return hash('sha256', wp_json_encode($fields));
    }
    public static function approved($package) {
        if (!$package || self::mget($package->ID, 'stage', 'draft') !== 'approved') { return false; }
        $saved = (string)self::mget($package->ID, 'approved_hash');
        return $saved !== '' && hash_equals($saved, self::fingerprint($package));
    }
    private static function admin_url_page($notice = '', $id = 0) {
        $args = array('page' => self::PAGE);
        if ($notice !== '') { $args['scec_notice'] = $notice; }
        if ($id > 0) { $args['package'] = $id; }
        return add_query_arg($args, admin_url('options-general.php'));
    }
    private static function back($notice, $id = 0) {
        wp_safe_redirect(self::admin_url_page($notice, $id));
        exit;
    }
    private static function char_length($str) {
        if (function_exists('mb_strlen')) { return mb_strlen($str, 'UTF-8'); }
        $n = preg_match_all('/./us', $str);
        return $n === false ? strlen($str) : $n;
    }
    private static function char_prefix($str, $length) {
        if (function_exists('mb_substr')) { return mb_substr($str, 0, max(0,$length), 'UTF-8'); }
        return implode('', array_slice(preg_split('//u', $str, -1, PREG_SPLIT_NO_EMPTY) ?: array(), 0, max(0,$length)));
    }
    private static function normalized_fields($raw) {
        $title = sanitize_text_field((string)($raw['title'] ?? ''));
        $summary = sanitize_textarea_field((string)($raw['summary'] ?? ''));
        $url = esc_url_raw(trim((string)($raw['source_url'] ?? '')));
        $channels = self::channels($raw['channels'] ?? array());
        if ($title === '' || self::char_length($title) > 140 || $summary === '' || self::char_length($summary) > 1800 ||
            !$channels || !self::source_post($url)) { return null; }
        return array('title' => $title, 'summary' => $summary, 'source_url' => $url, 'channels' => $channels);
    }
    /** Works only through an explicit privileged POST with a per-package nonce. */
    public static function handle_action() {
        if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' || !current_user_can('manage_options')) { wp_die('Not authorized.', '', 403); }
        $action = sanitize_key((string)($_POST['scec_operation'] ?? ''));
        $id = absint($_POST['package_id'] ?? 0);
        if (!in_array($action, array('create','update','submit','return','approve','generate_draft','record_external','export'), true)) {
            wp_die('Invalid action.', '', 400);
        }
        check_admin_referer('scec_media04_' . $action . '_' . $id);
        $package = $id ? self::get_package($id) : null;
        if ($action !== 'create' && !$package) { self::back('not_found'); }
        if ($action === 'create' || $action === 'update') {
            if ($action === 'update' && self::mget($id, 'stage', 'draft') !== 'draft') { self::back('locked', $id); }
            $fields = self::normalized_fields(wp_unslash($_POST));
            if (!$fields) { self::back('invalid', $id); }
            if ($action === 'create') {
                $new_id = wp_insert_post(array('post_type' => self::POST_TYPE, 'post_status' => 'private',
                    'post_title' => $fields['title'], 'post_author' => get_current_user_id()), true);
                if (is_wp_error($new_id) || !$new_id) { self::back('save_failed'); }
                $id = (int)$new_id;
                self::mset($id, 'stage', 'draft');
            } else {
                $updated = wp_update_post(array('ID' => $id, 'post_title' => $fields['title']), true);
                if (is_wp_error($updated) || !$updated) { self::back('save_failed', $id); }
            }
            self::mset($id, 'summary', $fields['summary']);
            self::mset($id, 'source_url', $fields['source_url']);
            self::mset($id, 'channels', $fields['channels']);
            self::audit($id, $action);
            self::back('saved', $id);
        }
        $stage = (string)self::mget($id, 'stage', 'draft');
        if ($action === 'return') {
            if ($stage !== 'in_review') { self::back('bad_stage', $id); }
            self::mset($id, 'stage', 'draft');
            self::mset($id, 'approved_hash', '');
            self::audit($id, 'returned_for_revision');
            self::back('returned', $id);
        }
        if ($action === 'submit') {
            if ($stage !== 'draft' || !self::fingerprint($package)) { self::back('bad_stage', $id); }
            self::mset($id, 'stage', 'in_review');
            self::audit($id, 'submitted_for_review');
            self::back('submitted', $id);
        }
        if ($action === 'approve') {
            if ($stage !== 'in_review' || (string)($_POST['rights_confirmed'] ?? '') !== '1' ||
                (string)($_POST['embargo_confirmed'] ?? '') !== '1') { self::back('review_required', $id); }
            $hash = self::fingerprint($package);
            if ($hash === '') { self::back('source_changed', $id); }
            self::mset($id, 'approved_hash', $hash);
            self::mset($id, 'reviewer', get_current_user_id());
            self::mset($id, 'approved_utc', gmdate('c'));
            self::mset($id, 'stage', 'approved');
            self::audit($id, 'approved');
            self::back('approved', $id);
        }
        if (!self::approved($package)) { self::back('source_changed', $id); }
        if ($action === 'generate_draft') {
            if ((int)self::mget($id, 'wp_draft_id') > 0) { self::back('already_generated', $id); }
            $summary = (string)self::mget($id, 'summary');
            $src = (string)self::mget($id, 'source_url');
            $html = '<p>' . esc_html($summary) . '</p><p><a href="' . esc_url($src) . '">Read the original publication</a></p>';
            $draft_id = wp_insert_post(array('post_type' => 'post', 'post_status' => 'draft',
                'post_title' => $package->post_title, 'post_content' => $html,
                'post_excerpt' => $summary, 'post_author' => get_current_user_id()), true);
            if (is_wp_error($draft_id) || !$draft_id) { self::back('save_failed', $id); }
            self::mset($id, 'wp_draft_id', (int)$draft_id);
            update_post_meta((int)$draft_id, '_scec_media04_package_id', $id);
            wp_set_post_tags((int)$draft_id, array('media-update'), true);
            self::audit($id, 'wordpress_draft_created');
            self::back('draft_created', $id);
        }
        if ($action === 'record_external') {
            $channel = sanitize_key((string)($_POST['channel'] ?? ''));
            $url = trim((string)($_POST['external_url'] ?? ''));
            if (!in_array($channel, self::channels(self::mget($id, 'channels', array())), true) ||
                !self::external_url($url, $channel)) { self::back('invalid_external', $id); }
            $records = self::mget($id, 'external_records', array());
            if (!is_array($records)) { $records = array(); }
            $records[$channel] = array('url' => $url, 'recorded_utc' => gmdate('c'),
                'recorded_by' => get_current_user_id(), 'verification' => 'operator_attested_not_api_verified');
            self::mset($id, 'external_records', $records);
            self::audit($id, 'external_recorded_' . $channel);
            self::back('recorded', $id);
        }
        if ($action === 'export') { self::export($package); }
        self::back('bad_stage', $id);
    }
    /** Strict per-platform host rules; no URL is fetched or automatically posted. */
    public static function external_url($url, $channel) {
        if (!is_string($url) || strlen($url) > 2048) { return false; }
        $p = wp_parse_url($url);
        if (!is_array($p) || strtolower((string)($p['scheme'] ?? '')) !== 'https' ||
            empty($p['host']) || isset($p['port']) || isset($p['user']) || isset($p['pass']) || isset($p['fragment'])) { return false; }
        $host = strtolower((string)$p['host']);
        if (filter_var($host, FILTER_VALIDATE_IP) || strpos($host, '..') !== false ||
            !preg_match('/^[a-z0-9.-]+$/D', $host)) { return false; }
        $hosts = array(
            'youtube' => array('youtube.com', 'www.youtube.com', 'youtu.be'),
            'linkedin' => array('www.linkedin.com', 'linkedin.com'),
            'x' => array('x.com', 'www.x.com', 'twitter.com', 'www.twitter.com'),
            'facebook' => array('www.facebook.com', 'facebook.com'),
            'instagram' => array('www.instagram.com', 'instagram.com'),
            'threads' => array('www.threads.net', 'threads.net', 'www.threads.com', 'threads.com'),
            'bluesky' => array('bsky.app'),
        );
        if ($channel === 'substack') {
            $options = get_option(SC_Engagement_Bridge_882::MEDIA_OPTION, array());
            $base = is_array($options) ? (string)($options['substack_url'] ?? '') : '';
            $parts = wp_parse_url($base);
            $base_host = is_array($parts) ? strtolower((string)($parts['host'] ?? '')) : '';
            if ($base_host === '' || $host !== $base_host) { return false; }
        } elseif ($channel === 'mastodon') {
            // Federation is not bound to one host, but disallow non-public/local hosts.
            if (strpos($host, '.') === false || preg_match('/(?:^|\.)(?:local|localhost|internal|test|invalid)$/D', $host)) { return false; }
        } elseif (!isset($hosts[$channel]) || !in_array($host, $hosts[$channel], true)) { return false; }
        $path = (string)($p['path'] ?? '');
        return $path !== '' && $path !== '/' && !preg_match('/[\r\n\x00]|%0[ad]/i', $path);
    }
    public static function messages($package) {
        if (!$package) { return array(); }
        $title = trim((string)$package->post_title);
        $summary = trim((string)self::mget($package->ID, 'summary'));
        $source = trim((string)self::mget($package->ID, 'source_url'));
        $channels = self::channels(self::mget($package->ID, 'channels', array()));
        $out = array();
        foreach ($channels as $channel) {
            if ($channel === 'substack') { $out[$channel] = $title . "\n\n" . $summary . "\n\nRead the source: " . $source; }
            elseif ($channel === 'youtube') { $out[$channel] = $title . "\n" . $summary . "\nMore: " . $source; }
            elseif (in_array($channel, array('x', 'bluesky'), true)) {
                // Character count is conservative; WordPress uses mb_* in core installations.
                $prefix = $title . ' — ';
                $available = max(0, 265 - self::char_length($prefix) - self::char_length($source) - 1);
                $out[$channel] = $prefix . self::char_prefix($summary, $available) . "\n" . $source;
            } else { $out[$channel] = $title . "\n\n" . $summary . "\n\n" . $source; }
        }
        return $out;
    }
    private static function audit($id, $event) {
        $entries = self::mget($id, 'audit', array());
        if (!is_array($entries)) { $entries = array(); }
        $entries[] = array('event' => $event, 'actor' => get_current_user_id(), 'at_utc' => gmdate('c'));
        self::mset($id, 'audit', array_slice($entries, -100));
    }
    private static function export($package) {
        $id = (int)$package->ID;
        $manifest = array(
            'schema_version' => self::SCHEMA_VERSION,
            'source_system' => 'WordPress Media', 'distribution_mode' => 'manual_only',
            'package_id' => $id,
            'title' => $package->post_title,
            'source_url' => (string)self::mget($id, 'source_url'),
            'source_content_sha256' => self::source_fingerprint(self::source_post((string)self::mget($id, 'source_url'))),
            'approved_package_sha256' => (string)self::mget($id, 'approved_hash'),
            'approval_utc' => (string)self::mget($id, 'approved_utc'),
            'channels' => self::channels(self::mget($id, 'channels', array())),
            'copy_ready_messages' => self::messages($package),
            'wordpress_draft_id' => (int)self::mget($id, 'wp_draft_id', 0),
            'manual_external_records' => self::mget($id, 'external_records', array()),
            'assurance' => array('source_published' => true, 'no_automated_external_distribution' => true,
                'external_records_are_operator_attested' => true),
        );
        self::audit($id, 'package_exported');
        nocache_headers();
        header('Content-Type: application/json; charset=utf-8');
        header('Content-Disposition: attachment; filename="media-package-' . $id . '.json"');
        header('X-Content-Type-Options: nosniff');
        echo wp_json_encode($manifest, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
        exit;
    }
    private static function form_begin($operation, $id = 0) {
        echo '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
        echo '<input type="hidden" name="action" value="scec_media04">';
        echo '<input type="hidden" name="scec_operation" value="' . esc_attr($operation) . '">';
        echo '<input type="hidden" name="package_id" value="' . (int)$id . '">';
        wp_nonce_field('scec_media04_' . $operation . '_' . $id);
    }
    private static function form_end($label, $class = 'button button-secondary') {
        echo '<button type="submit" class="' . esc_attr($class) . '">' . esc_html($label) . '</button></form>';
    }
    private static function render_editor($package = null) {
        $id = $package ? (int)$package->ID : 0;
        $stage = $package ? (string)self::mget($id, 'stage', 'draft') : 'draft';
        echo '<section class="scec-media04-box"><h2>' . ($id ? 'Package #' . $id : 'New distribution package') . '</h2>';
        if (!$package || $stage === 'draft') {
            self::form_begin($id ? 'update' : 'create', $id);
            echo '<label for="scec-title">Title</label><input id="scec-title" type="text" name="title" maxlength="140" required value="' . esc_attr($package ? $package->post_title : '') . '">';
            echo '<label for="scec-summary">Public-facing summary</label><textarea id="scec-summary" name="summary" rows="5" maxlength="1800" required>' . esc_textarea($id ? self::mget($id,'summary') : '') . '</textarea>';
            echo '<label for="scec-source">Approved public WordPress article/page URL</label><input id="scec-source" type="url" name="source_url" required value="' . esc_attr($id ? self::mget($id,'source_url') : '') . '" placeholder="' . esc_attr(home_url('/example-article/')) . '">';
            echo '<fieldset><legend>Distribution channels (manual packages; no auto-posting)</legend>';
            $chosen = $id ? self::channels(self::mget($id,'channels',array())) : array();
            foreach (self::CHANNELS as $key => $label) {
                echo '<label class="scec-media04-choice"><input type="checkbox" name="channels[]" value="' . esc_attr($key) . '" ' . checked(in_array($key,$chosen,true),true,false) . '> ' . esc_html($label) . '</label>';
            }
            echo '</fieldset>';
            self::form_end($id ? 'Save changes' : 'Create private draft', 'button button-primary');
        } else {
            echo '<p><strong>' . esc_html($package->post_title) . '</strong></p><p>' . esc_html((string)self::mget($id, 'summary')) . '</p>';
            echo '<p>Source: <a href="' . esc_url((string)self::mget($id,'source_url')) . '" target="_blank" rel="noopener noreferrer">' . esc_html((string)self::mget($id,'source_url')) . '</a></p>';
        }
        if ($package) {
            echo '<p class="scec-media04-stage">Stage: <strong>' . esc_html($stage) . '</strong> ' . (self::approved($package) ? '· Source and approval fingerprint valid' : ($stage === 'approved' ? '· Source changed; approval invalidated' : '')) . '</p>';
            if ($stage === 'draft') {
                self::form_begin('submit', $id); self::form_end('Submit for review');
            } elseif ($stage === 'in_review') {
                echo '<div class="scec-media04-actions">';
                self::form_begin('return', $id); self::form_end('Return for revision');
                self::form_begin('approve', $id);
                echo '<label><input required type="checkbox" name="rights_confirmed" value="1"> I verified source rights and attribution</label>';
                echo '<label><input required type="checkbox" name="embargo_confirmed" value="1"> I verified there is no active embargo or restricted information</label>';
                self::form_end('Approve distribution package', 'button button-primary');
                echo '</div>';
            } elseif ($stage === 'approved' && self::approved($package)) {
                self::render_approved($package);
            }
            $audit = self::mget($id, 'audit', array());
            if (is_array($audit) && $audit) {
                echo '<details class="scec-media04-audit"><summary>Audit history (' . count($audit) . ')</summary><ol>';
                foreach (array_reverse($audit) as $entry) { echo '<li>' . esc_html((string)($entry['event'] ?? '')) . ' · user #' . (int)($entry['actor'] ?? 0) . ' · ' . esc_html((string)($entry['at_utc'] ?? '')) . '</li>'; }
                echo '</ol></details>';
            }
        }
        echo '</section>';
    }
    private static function render_approved($package) {
        $id = (int)$package->ID;
        echo '<div class="scec-media04-actions">';
        if (!(int)self::mget($id,'wp_draft_id',0)) {
            self::form_begin('generate_draft',$id); self::form_end('Create WordPress editorial draft', 'button button-primary');
        } else {
            $draft_id = (int)self::mget($id,'wp_draft_id');
            echo '<p>WordPress editorial post #' . $draft_id . ': <a href="' . esc_url(get_edit_post_link($draft_id)) . '">Open in WordPress editor</a>. WordPress publishing remains a separate explicit action.</p>';
        }
        self::form_begin('export',$id); self::form_end('Download approved JSON distribution package');
        echo '</div><h3>Copy-ready channel text</h3><p>Post manually using the linked platform. No platform has been contacted and no messages were sent.</p>';
        $records = self::mget($id,'external_records',array());
        if (!is_array($records)) { $records=array(); }
        foreach (self::messages($package) as $channel => $message) {
            echo '<div class="scec-media04-channel"><h4>' . esc_html(self::CHANNELS[$channel]) . '</h4>';
            echo '<textarea readonly rows="5" id="scec-copy-' . esc_attr((string)$id . '-' . $channel) . '">' . esc_textarea($message) . '</textarea>';
            echo '<button type="button" class="button" data-scec-copy="#scec-copy-' . esc_attr((string)$id . '-' . $channel) . '">Copy text</button>';
            if (isset($records[$channel])) { echo '<p>Recorded external publication (not API-verified): <a href="' . esc_url($records[$channel]['url']) . '" target="_blank" rel="noopener noreferrer">' . esc_html($records[$channel]['url']) . '</a></p>'; }
            self::form_begin('record_external',$id);
            echo '<input type="hidden" name="channel" value="' . esc_attr($channel) . '">';
            echo '<label>External publication URL (manual record, not verified)<input type="url" name="external_url" placeholder="https://..." required></label>';
            self::form_end('Record public URL');
            echo '</div>';
        }
    }
    public static function render_admin() {
        if (!current_user_can('manage_options')) { wp_die('Not authorized.', '', 403); }
        $selected = absint($_GET['package'] ?? 0);
        $package = $selected ? self::get_package($selected) : null;
        $notices = array('saved'=>'Package saved.','submitted'=>'Submitted for review.','approved'=>'Approved and fingerprinted.','draft_created'=>'WordPress draft created; not published.',
            'recorded'=>'External URL recorded from operator input; not API verified.','returned'=>'Returned to draft.','not_found'=>'Package not found.','invalid'=>'A required field is invalid or the source is not published publicly.','locked'=>'Submitted/approved packages cannot be edited; make a new package for revisions.',
            'review_required'=>'Approval requires both rights and embargo confirmations.','source_changed'=>'Source is unavailable or changed since approval; distribution is blocked.','bad_stage'=>'This action is not permitted in the current stage.','already_generated'=>'This package already created a WordPress draft.','invalid_external'=>'External URL does not match the declared channel.','save_failed'=>'WordPress could not save the record.');
        $notice = sanitize_key((string)($_GET['scec_notice'] ?? ''));
        echo '<div class="wrap scec-media04"><h1>Media Distribution · MEDIA-04</h1><p>Create private, reviewable distribution packages from published WordPress content. Exports and copy-ready messages are manual. This plugin never signs in to or posts on Substack, YouTube, LinkedIn, or other social platforms.</p>';
        if (isset($notices[$notice])) { echo '<div class="notice notice-info"><p>' . esc_html($notices[$notice]) . '</p></div>'; }
        echo '<div class="scec-media04-layout"><main>';
        self::render_editor($package);
        echo '</main><aside class="scec-media04-box"><h2>Recent packages</h2>';
        $posts = get_posts(array('post_type'=>self::POST_TYPE,'post_status'=>'private','posts_per_page'=>30,'orderby'=>'date','order'=>'DESC','suppress_filters'=>false));
        if ($posts) {
            echo '<ol class="scec-media04-packages">';
            foreach ($posts as $p) {
                $s = self::mget($p->ID,'stage','draft');
                echo '<li><a href="' . esc_url(self::admin_url_page('',(int)$p->ID)) . '">' . esc_html($p->post_title) . '</a><small>#' . (int)$p->ID . ' · ' . esc_html($s) . '</small></li>';
            }
            echo '</ol>';
        } else { echo '<p>No distribution packages yet.</p>'; }
        echo '<hr><h3>Control boundaries</h3><p>Private packages are not publicly queryable. Approval is recorded but never sends content externally. Generated WordPress content remains a draft until a publisher separately publishes it.</p>';
        echo '<p><strong>Current integration:</strong> WordPress editorial workflow. Existing Engagement &amp; Communications, Research, Workspace, and external-channel API integration remain separate, future authorization-gated work.</p>';
        echo '</aside></div></div>';
    }
}
