<?php
/**
 * Plugin Name: Sustainable Catalyst — Media & Communications Bridge
 * Description: Public Media hub for newsletters, video, LinkedIn, social channels and read-only Engagement & Communications bridge.
 * Version: 8.8.9
 * Author: Content Catalyst LLC
 * Text Domain: sc-engagement-bridge
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Engagement_Bridge_882 {
    const OPTION = 'sc_ec880_app_url';
    const VERSION = '8.8.9';
    const MEDIA_OPTION = 'sc_ec_media_settings';
    const REDIRECT_OPTION = 'sc_ec_media_legacy_redirects';

    public static function boot() {
        add_action('admin_init', array(__CLASS__, 'register_settings'));
        add_action('admin_menu', array(__CLASS__, 'menu'));
        add_action('wp_enqueue_scripts', array(__CLASS__, 'enqueue_assets'));
        add_action('template_redirect', array(__CLASS__, 'maybe_legacy_media_redirect'), 1);
        add_shortcode('sc_engagement_communications', array(__CLASS__, 'render'));
        add_shortcode('sc_engagement_launch', array(__CLASS__, 'render_launch'));
        add_shortcode('sc_engagement_public_links', array(__CLASS__, 'render_public_links'));
        add_shortcode('sc_press', array(__CLASS__, 'render_media')); // Existing pages remain functional.
        add_shortcode('sc_media', array(__CLASS__, 'render_media'));
    }

    public static function register_assets() {
        wp_register_style('sc-ec880-bridge', plugins_url('assets/bridge.css', __FILE__), array(), self::VERSION);
        wp_register_script('sc-ec-media', plugins_url('assets/media.js', __FILE__), array(), self::VERSION, true);
    }
    public static function enqueue_assets() {
        self::register_assets();
        wp_enqueue_style('sc-ec880-bridge');
    }
    public static function sanitize_url($value) {
        if (!is_string($value)) { return ''; }
        $value = trim($value);
        if ($value === '') { return ''; }
        $parts = wp_parse_url($value);
        if (!is_array($parts) || strtolower($parts['scheme'] ?? '') !== 'https' || empty($parts['host']) ||
            isset($parts['user']) || isset($parts['pass']) || isset($parts['query']) || isset($parts['fragment']) || isset($parts['port'])) {
            add_settings_error(self::OPTION, 'invalid_url', 'Enter an HTTPS application URL without credentials, query, fragment or port.');
            return get_option(self::OPTION, '');
        }
        $host = strtolower((string)$parts['host']);
        if ($host === 'localhost' || (substr($host, -10) === '.localhost') || filter_var($host, FILTER_VALIDATE_IP) ||
            strpos($host, '..') !== false || !preg_match('/^[a-z0-9.-]+$/D', $host)) {
            add_settings_error(self::OPTION, 'invalid_host', 'Use a public HTTPS DNS hostname, not an IP address or localhost.');
            return get_option(self::OPTION, '');
        }
        $path = $parts['path'] ?? '/';
        if (strpos($path, '//') === 0 || preg_match('/[\r\n]/', $path)) { return get_option(self::OPTION, ''); }
        return esc_url_raw('https://' . $host . rtrim($path, '/') . '/');
    }
    public static function register_settings() {
        register_setting('sc_ec880_settings', self::OPTION, array(
            'type' => 'string', 'default' => '', 'sanitize_callback' => array(__CLASS__, 'sanitize_url')
        ));
        add_settings_section('sc_ec880_main', 'Standalone application', function() {
            echo '<p>Only set a URL after the standalone site is available through HTTPS. This plugin never relays tokens or private records.</p>';
        }, 'sc_ec880');
        add_settings_field(self::OPTION, 'Public application HTTPS URL', array(__CLASS__, 'field'), 'sc_ec880', 'sc_ec880_main');
        register_setting('sc_ec880_settings', self::MEDIA_OPTION, array('type' => 'array', 'default' => self::media_defaults(), 'sanitize_callback' => array(__CLASS__, 'sanitize_media_settings')));
        add_settings_section('sc_ec_media', 'Public Media connections', function() { echo '<p>Configure public channels only. Newsletter subscriptions stay on Substack; videos stay on YouTube. No tokens or subscriber records are stored.</p>'; }, 'sc_ec880');
        add_settings_field('sc_media_substack', 'Substack publication', array(__CLASS__, 'field_media_substack'), 'sc_ec880', 'sc_ec_media');
        add_settings_field('sc_media_youtube', 'YouTube channel', array(__CLASS__, 'field_media_youtube'), 'sc_ec880', 'sc_ec_media');
        add_settings_field('sc_media_linkedin', 'LinkedIn', array(__CLASS__, 'field_media_linkedin'), 'sc_ec880', 'sc_ec_media');
        add_settings_field('sc_media_socials', 'Other social channels', array(__CLASS__, 'field_media_socials'), 'sc_ec880', 'sc_ec_media');
        add_settings_field('sc_media_featured', 'Featured video / playlist', array(__CLASS__, 'field_media_video'), 'sc_ec880', 'sc_ec_media');
        add_settings_field('sc_media_feed', 'Recent newsletter issues', array(__CLASS__, 'field_media_feed'), 'sc_ec880', 'sc_ec_media');
        add_settings_field('sc_media_embed', 'On-page signup form', array(__CLASS__, 'field_media_embed'), 'sc_ec880', 'sc_ec_media');
        add_settings_section('sc_ec_media03', 'MEDIA-03 — Unified Channel Discovery', function() {
            echo '<p>Optional read-only discovery of public Substack and YouTube feeds and selected published WordPress posts. WordPress fetches and caches public metadata. No subscriber data, passwords, tokens, cross-posting or automatic outgoing messages.</p>';
        }, 'sc_ec880');
        add_settings_field('sc_media03_enable', 'Unified public updates', array(__CLASS__, 'field_media_discovery'), 'sc_ec880', 'sc_ec_media03');
        add_settings_field('sc_media03_youtube_id', 'YouTube channel ID', array(__CLASS__, 'field_media_youtube_id'), 'sc_ec880', 'sc_ec_media03');
        add_settings_field('sc_media03_wordpress', 'WordPress updates', array(__CLASS__, 'field_media_wordpress_updates'), 'sc_ec880', 'sc_ec_media03');
        register_setting('sc_ec880_settings', self::REDIRECT_OPTION, array('type' => 'string', 'default' => '0', 'sanitize_callback' => array(__CLASS__, 'sanitize_media_redirect_option')));
        add_settings_section('sc_ec_media02', 'MEDIA-02 — Site activation and legacy URLs', function() { echo '<p>Optional redirects are off by default. Enable only after the Media page is public and the former page slugs no longer serve separate content.</p>'; }, 'sc_ec880');
        add_settings_field('sc_ec_media_redirect', 'Redirect old Press / Channel URLs', array(__CLASS__, 'field_media_redirect'), 'sc_ec880', 'sc_ec_media02');
    }
    public static function field() {
        $value = get_option(self::OPTION, '');
        echo '<input type="url" class="regular-text" name="' . esc_attr(self::OPTION) . '" value="' . esc_attr($value) . '" placeholder="https://engagement.example.org/" autocomplete="off">';
        echo '<p class="description">Leave blank until public HTTPS deployment. Do not enter a private localhost address.</p>';
    }
    public static function menu() {
        add_options_page('Media & Communications', 'Media & Communications', 'manage_options', 'sc_ec880', array(__CLASS__, 'settings_page'));
    }
    public static function settings_page() {
        if (!current_user_can('manage_options')) { return; }
        echo '<div class="wrap"><h1>Media &amp; Communications</h1><form method="post" action="options.php">';
        settings_fields('sc_ec880_settings'); do_settings_sections('sc_ec880'); submit_button('Save settings');
        echo '</form><p>Shortcodes: <code>[sc_engagement_communications]</code> <code>[sc_engagement_launch]</code>, <code>[sc_engagement_public_links]</code>, <code>[sc_press]</code> (compatibility), and <code>[sc_media]</code> (recommended).</p>';
        self::render_media_readiness_admin();
        echo '<p><a class="button button-secondary" href="' . esc_url(admin_url('options-general.php?page=scec-media04')) . '">Open MEDIA-04 Distribution Workspace</a></p>';
        echo '</div>';
    }
    /** Conservative check; an existing source page is never hijacked by a redirect. */
    private static function media_page() {
        $page = get_page_by_path('media', OBJECT, 'page');
        if (!$page || $page->post_status !== 'publish' || post_password_required($page)) { return null; }
        return $page;
    }
    private static function media_page_has_shortcode($page) {
        if (!$page || !is_string($page->post_content ?? null)) { return false; }
        return has_shortcode($page->post_content, 'sc_media') || has_shortcode($page->post_content, 'sc_press');
    }
    public static function sanitize_media_redirect_option($value) {
        return (string)$value === '1' ? '1' : '0';
    }
    public static function field_media_redirect() {
        $enabled = get_option(self::REDIRECT_OPTION, '0');
        echo '<input type="hidden" name="' . esc_attr(self::REDIRECT_OPTION) . '" value="0">';
        echo '<label><input type="checkbox" name="' . esc_attr(self::REDIRECT_OPTION) . '" value="1" ' . checked($enabled, '1', false) . '> Redirect exact public <code>/press/</code> and <code>/channel/</code> requests to <code>/media/</code> with HTTP 301</label>';
        echo '<p class="description">Off by default. Only activates if the Media page is published, publicly accessible and contains [sc_media] or [sc_press]. Never overrides a separate existing Press/Channel WordPress page. Back up first, and avoid duplicate redirects in your host or SEO plugin.</p>';
    }
    /** WordPress installation can live at the root or a subdirectory. */
    private static function media_legacy_slug_for_request($request_uri, $home_url) {
        if (!is_string($request_uri) || !is_string($home_url)) { return ''; }
        $path = wp_parse_url($request_uri, PHP_URL_PATH);
        $query = wp_parse_url($request_uri, PHP_URL_QUERY);
        if (!is_string($path) || ($query !== null && $query !== false)) { return ''; }
        $home_path = (string)wp_parse_url($home_url, PHP_URL_PATH);
        $prefix = rtrim($home_path, '/');
        if ($prefix !== '') {
            if (strpos($path, $prefix . '/') !== 0) { return ''; }
            $path = substr($path, strlen($prefix));
        }
        // Only exact, clean paths; never redirect arbitrary or nested routes.
        if ($path === '/press' || $path === '/press/') { return 'press'; }
        if ($path === '/channel' || $path === '/channel/') { return 'channel'; }
        return '';
    }
    public static function media_readiness_checks() {
        $page = self::media_page();
        $media_page_raw = get_page_by_path('media', OBJECT, 'page');
        $has_shortcode = self::media_page_has_shortcode($page);
        $link = $page ? get_permalink($page) : '';
        $home = home_url('/');
        $same_host = is_string($link) && $link !== ''
            && strtolower((string)wp_parse_url($link, PHP_URL_HOST)) === strtolower((string)wp_parse_url($home, PHP_URL_HOST));
        $safe_link = $same_host && wp_http_validate_url($link);
        $press_collision = (bool)get_page_by_path('press', OBJECT, 'page');
        $channel_collision = (bool)get_page_by_path('channel', OBJECT, 'page');
        $opt_in = get_option(self::REDIRECT_OPTION, '0') === '1';
        return array(
            'media_exists' => (bool)$media_page_raw,
            'media_public' => (bool)$page,
            'shortcode' => $has_shortcode,
            'same_site_url' => (bool)$safe_link,
            'redirect_opt_in' => $opt_in,
            'press_clear' => !$press_collision,
            'channel_clear' => !$channel_collision,
            'media_url' => $safe_link ? $link : '',
        );
    }
    public static function render_media_readiness_admin() {
        $checks = self::media_readiness_checks();
        $items = array(
            array('Media page exists', $checks['media_exists'], 'Create or rename the public page to /media/.'),
            array('Media page is published and not password protected', $checks['media_public'], 'Publish the page without a page password.'),
            array('Media shortcode present', $checks['shortcode'], 'Add [sc_media] in a WordPress Shortcode block.'),
            array('Media permalink is valid for this site', $checks['same_site_url'], 'Check permalinks, WordPress HTTPS and site address.'),
            array('Old Press URL is free to redirect', $checks['press_clear'], 'Review and preserve the separate /press/ page before enabling redirects.'),
            array('Old Channel URL is free to redirect', $checks['channel_clear'], 'Review and preserve the separate /channel/ page before enabling redirects.'),
        );
        echo '<h2>MEDIA-02 — Launch readiness</h2><p>These checks inspect WordPress content and configuration only. They do not prove public HTTP access, navigation, CDN or redirect behavior.</p>';
        echo '<table class="widefat striped" style="max-width:860px"><thead><tr><th>Check</th><th>State</th><th>Action</th></tr></thead><tbody>';
        foreach ($items as $item) {
            echo '<tr><td>' . esc_html($item[0]) . '</td><td>' . ($item[1] ? 'PASS' : 'CHECK') . '</td><td>' . esc_html($item[1] ? 'No action needed' : $item[2]) . '</td></tr>';
        }
        echo '</tbody></table>';
        if ($checks['media_url']) { echo '<p><a href="' . esc_url($checks['media_url']) . '" target="_blank" rel="noopener noreferrer">Open Media page</a> (also test while signed out).</p>'; }
        echo '<p><strong>Legacy redirects:</strong> ' . ($checks['redirect_opt_in'] ? 'Enabled conditionally' : 'Disabled') . '. The plugin does not update WordPress menus or host-level redirects.</p>';
        $options = self::media_settings();
        $enabled = ($options['enable_discovery'] ?? '0') === '1';
        $channel_id = (string)($options['youtube_channel_id'] ?? '');
        echo '<h2>MEDIA-03 — Discovery readiness</h2>';
        echo '<p>Read-only configuration checks only; no live external feed request is made by this dashboard.</p>';
        echo '<table class="widefat striped" style="max-width:860px"><tbody>';
        $states = array(
            'Public discovery' => $enabled ? 'Enabled (read-only)' : 'Disabled (safe default)',
            'Substack source' => self::media_validate_url($options['substack_url'] ?? '', 'substack') !== '' ? 'Configured' : 'Not configured',
            'YouTube discovery ID' => preg_match('/^UC[A-Za-z0-9_-]{22}$/D', $channel_id) ? 'Configured' : 'Not configured; channel link still works',
            'WordPress curated posts' => ($options['show_wp_updates'] ?? '0') === '1' ? 'Enabled — tag media-update' : 'Disabled',
            'PHP XML parser' => function_exists('simplexml_load_string') ? 'Available' : 'Missing — external feed discovery unavailable',
            'Safe HTTP support' => function_exists('wp_safe_remote_get') ? 'Available' : 'Missing — external feed discovery unavailable',
        );
        foreach ($states as $name => $status) {
            echo '<tr><td><strong>' . esc_html($name) . '</strong></td><td>' . esc_html($status) . '</td></tr>';
        }
        echo '</tbody></table><p>Public feeds are cached for 60 minutes (errors: 10 minutes). Source links are displayed only; no content is automatically published to external channels.</p>';
    }
    /** No redirect for admin, preview, API, POST, path collisions or unpublished targets. */
    public static function maybe_legacy_media_redirect() {
        if (get_option(self::REDIRECT_OPTION, '0') !== '1') { return; }
        if (is_admin() || is_preview() || wp_doing_ajax() || (defined('REST_REQUEST') && REST_REQUEST)) { return; }
        $method = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));
        if ($method !== 'GET' && $method !== 'HEAD') { return; }
        $slug = self::media_legacy_slug_for_request((string)($_SERVER['REQUEST_URI'] ?? ''), home_url('/'));
        if ($slug === '') { return; }
        if (get_page_by_path($slug, OBJECT, 'page')) { return; }
        $checks = self::media_readiness_checks();
        if (!$checks['media_public'] || !$checks['shortcode'] || !$checks['same_site_url']) { return; }
        if (!($checks[$slug . '_clear'] ?? false)) { return; }
        if (wp_safe_redirect($checks['media_url'], 301, 'Sustainable Catalyst Media')) { exit; }
    }

    private static function start_assets() {
        if (!wp_style_is('sc-ec880-bridge', 'registered')) { self::register_assets(); }
        wp_enqueue_style('sc-ec880-bridge');
    }
    /** Only published, public WordPress pages are linked; existing pages are never altered. */
    private static function resolve_public_page($slugs) {
        foreach ($slugs as $slug) {
            $page = get_page_by_path($slug, OBJECT, 'page');
            if (!$page || $page->post_status !== 'publish' || post_password_required($page)) { continue; }
            $url = get_permalink($page);
            if ($url && wp_http_validate_url($url)) { return $url; }
        }
        return '';
    }
    public static function render_public_links($attrs = array()) {
        self::start_assets();
        $pages = array(
            array('Contact', 'General inquiries and institutional correspondence', array('contact', 'contact-us')),
            array('Feedback', 'General feedback about the platform and its services', array('feedback')),
            array('Feature Suggestions', 'Propose new tools, capabilities and improvements', array('feature-suggestions')),
            array('Media', 'Newsletter, video, press, and public communications', array('media', 'press', 'channel')),
            array('Support', 'Technical questions and service assistance', array('support')),
        );
        $items = '';
        foreach ($pages as $item) {
            $link = self::resolve_public_page($item[2]);
            if (!$link) { continue; }
            $items .= '<a class="scec881-public-link" href="' . esc_url($link) . '"><strong>' . esc_html($item[0]) . '</strong><span>' . esc_html($item[1]) . '</span><span aria-hidden="true">↗</span></a>';
        }
        if ($items === '') { return ''; }
        return '<nav class="scec881-public" aria-label="Existing Sustainable Catalyst public services"><div class="scec881-public-heading"><strong>Public services</strong><p>Public pages remain independent of the Engagement &amp; Communications administration system. Existing forms and submission workflows are unchanged.</p></div><div class="scec881-public-grid">' . $items . '</div></nav>';
    }
    /** Public Press landing, no backend calls or private records. */
    public static function render_press($attrs = array()) {
        self::start_assets();
        $destinations = array(
            array('Press Releases', 'Official statements and approved releases.', array('press-releases', 'newsroom')),
            array('Institutional Updates', 'Institutional announcements, milestones, and public notices.', array('institutional-updates', 'announcements')),
            array('Media Resources', 'Approved background information and media resources.', array('media-resources', 'press-kit')),
            array('Press Inquiries', 'Contact Sustainable Catalyst regarding media or institutional communications.', array('press-contact', 'contact', 'contact-us')),
        );
        $cards = '';
        foreach ($destinations as $destination) {
            $url = self::resolve_public_page($destination[2]);
            $heading = '<strong>' . esc_html($destination[0]) . '</strong>';
            $description = '<span>' . esc_html($destination[1]) . '</span>';
            if ($url) {
                $cards .= '<a class="scec-press-card" href="' . esc_url($url) . '">' . $heading . $description . '<small>Explore section <span aria-hidden="true">↗</span></small></a>';
            } else {
                $cards .= '<div class="scec-press-card scec-press-card-pending">' . $heading . $description . '<small>Not yet published</small></div>';
            }
        }
        return '<section class="scec-press" aria-labelledby="scec-press-title">'
            . '<div class="scec-press-eyebrow">SUSTAINABLE CATALYST / INSTITUTIONAL COMMUNICATIONS</div>'
            . '<div class="scec-press-intro"><p class="scec-press-label">PRESS &amp; MEDIA</p>'
            . '<h2 id="scec-press-title">Press</h2>'
            . '<p>Official announcements, institutional developments, media releases, and resources for journalists and public-interest partners.</p></div>'
            . '<div class="scec-press-section"><h3>Newsroom &amp; media resources</h3>'
            . '<p>Only publicly approved material is linked here. Private research, internal communications, subscriber records, and unpublished drafts remain outside this page.</p>'
            . '<div class="scec-press-grid">' . $cards . '</div></div>'
            . '<div class="scec-press-footnote"><strong>About this section</strong><p>Press is the public communications surface of Sustainable Catalyst. Publications remains the editorial article and blog section; Research retains responsibility for scientific research and its reviewed outputs.</p></div>'
            . '</section>';
    }
    /** A public Media directory; private Engagement & Communications APIs are never called. */
    public static function media_defaults() {
        return array(
            'substack_url' => 'https://newsletter.sustainablecatalyst.com/',
            'youtube_url' => 'https://www.youtube.com/@SustainableCatalyst',
            'featured_video_url' => '',
            'linkedin_url' => '',
            'social_x_url' => '',
            'social_instagram_url' => '',
            'social_facebook_url' => '',
            'social_threads_url' => '',
            'social_bluesky_url' => '',
            'social_mastodon_url' => '',
            'social_github_url' => '',
            'social_tiktok_url' => '',
            'show_feed' => '1',
            'show_subscribe_embed' => '1',
            'enable_discovery' => '0',
            'youtube_channel_id' => '',
            'show_wp_updates' => '1',
        );
    }
    private static function media_settings() {
        $saved = get_option(self::MEDIA_OPTION, array());
        if (!is_array($saved)) { $saved = array(); }
        return array_merge(self::media_defaults(), $saved);
    }
    /** Validate public HTTPS destinations; do not permit local hosts, IPs, ports or credentials. */
    private static function media_https_base($raw) {
        if (!is_string($raw) || trim($raw) === '') { return ''; }
        $parts = wp_parse_url(trim($raw));
        if (!is_array($parts) || strtolower((string)($parts['scheme'] ?? '')) !== 'https' ||
            empty($parts['host']) || isset($parts['user']) || isset($parts['pass']) ||
            isset($parts['port']) || isset($parts['query']) || isset($parts['fragment'])) { return ''; }
        $host = strtolower((string)$parts['host']);
        if (strlen($host) > 253 || strpos($host, '.') === false || strpos($host, '..') !== false ||
            filter_var($host, FILTER_VALIDATE_IP) || !preg_match('/^[a-z0-9][a-z0-9.-]*[a-z0-9]$/D', $host) ||
            preg_match('/(?:^|\.)(?:localhost|local|internal|test|invalid)$/D', $host)) { return ''; }
        $path = (string)($parts['path'] ?? '/');
        if (strpos($path, '//') === 0 || preg_match('/[\r\n\x00]|%0[ad]/i', $path)) { return ''; }
        return esc_url_raw('https://' . $host . $path);
    }
    private static function media_validate_url($value, $kind) {
        $url = self::media_https_base($value);
        if ($url === '') { return ''; }
        $parts = wp_parse_url($url);
        $host = strtolower((string)($parts['host'] ?? ''));
        $path = (string)($parts['path'] ?? '/');
        if ($kind === 'substack') {
            // Substack can use custom publisher domains: only the publication root is accepted.
            if ($path !== '' && $path !== '/') { return ''; }
            return 'https://' . $host . '/';
        }
        if ($kind === 'youtube') {
            if (!in_array($host, array('youtube.com', 'www.youtube.com', 'm.youtube.com'), true)) { return ''; }
            if (!preg_match('~^/(?:@[A-Za-z0-9._-]+|channel/[A-Za-z0-9_-]+|c/[A-Za-z0-9._-]+|user/[A-Za-z0-9._-]+)/?$~D', $path)) { return ''; }
            return 'https://www.youtube.com' . rtrim($path, '/');
        }
        return '';
    }
    /** A published account/profile link only. No feeds, API keys, private records or server-side fetches. */
    private static function media_social_url($value, $kind) {
        $url = self::media_https_base($value);
        if ($url === '') { return ''; }
        $parts = wp_parse_url($url);
        $host = strtolower((string)($parts['host'] ?? ''));
        $path = (string)($parts['path'] ?? '/');
        $checks = array(
            'linkedin' => array(array('linkedin.com','www.linkedin.com'), '~^/(?:company|showcase|in)/[A-Za-z0-9._-]+/?$~D'),
            'x' => array(array('x.com','www.x.com','twitter.com','www.twitter.com'), '~^/[A-Za-z0-9_]{1,15}/?$~D'),
            'instagram' => array(array('instagram.com','www.instagram.com'), '~^/[A-Za-z0-9._]{1,30}/?$~D'),
            'facebook' => array(array('facebook.com','www.facebook.com'), '~^/[A-Za-z0-9._-]+/?$~D'),
            'threads' => array(array('threads.net','www.threads.net','threads.com','www.threads.com'), '~^/@[A-Za-z0-9._]+/?$~D'),
            'bluesky' => array(array('bsky.app','www.bsky.app'), '~^/profile/[A-Za-z0-9._-]+/?$~D'),
            'github' => array(array('github.com','www.github.com'), '~^/[A-Za-z0-9-]+/?$~D'),
            'tiktok' => array(array('tiktok.com','www.tiktok.com'), '~^/@[A-Za-z0-9._]+/?$~D'),
        );
        if ($kind === 'mastodon') {
            // Mastodon is federated: public profiles may be hosted on different domains.
            // Account owners explicitly configure a public profile; no profile is probed.
            if (!preg_match('~^/@[A-Za-z0-9_]+/?$~D', $path)) { return ''; }
        } elseif (!isset($checks[$kind]) || !in_array($host, $checks[$kind][0], true) ||
            !preg_match($checks[$kind][1], $path)) { return ''; }
        return esc_url_raw('https://' . $host . rtrim($path, '/'));
    }
    private static function media_social_catalog() {
        return array(
            'x' => array('X / Twitter', 'social_x_url'),
            'instagram' => array('Instagram', 'social_instagram_url'),
            'facebook' => array('Facebook', 'social_facebook_url'),
            'threads' => array('Threads', 'social_threads_url'),
            'bluesky' => array('Bluesky', 'social_bluesky_url'),
            'mastodon' => array('Mastodon', 'social_mastodon_url'),
            'github' => array('GitHub', 'social_github_url'),
            'tiktok' => array('TikTok', 'social_tiktok_url'),
        );
    }
    private static function render_social_cards($options) {
        $cards = '';
        foreach (self::media_social_catalog() as $kind => $descriptor) {
            $url = self::media_social_url($options[$descriptor[1]] ?? '', $kind);
            if (!$url) { continue; }
            $cards .= '<a class="scec-media-social-link" href="' . esc_url($url) . '" target="_blank" rel="noopener noreferrer external">'
                . '<strong>' . esc_html($descriptor[0]) . '</strong><span>Visit channel <span aria-hidden="true">↗</span></span></a>';
        }
        return $cards;
    }
    /** Supports one manually selected video or playlist; no private keys or automated YouTube scraping. */
    private static function video_embed_url($input) {
        if (!is_string($input) || trim($input) === '') { return ''; }
        $parts = wp_parse_url(trim($input));
        if (!is_array($parts) || strtolower((string)($parts['scheme'] ?? '')) !== 'https' ||
            empty($parts['host']) || isset($parts['user']) || isset($parts['pass']) || isset($parts['port'])) { return ''; }
        $host = strtolower((string)$parts['host']);
        $path = (string)($parts['path'] ?? '');
        $id = '';
        if (in_array($host, array('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com'), true)) {
            if (preg_match('~^/(?:embed/|shorts/|live/)([A-Za-z0-9_-]{11})/?$~D', $path, $m)) { $id = $m[1]; }
            if ($path === '/watch') {
                parse_str((string)($parts['query'] ?? ''), $query);
                if (is_string($query['v'] ?? null) && preg_match('/^[A-Za-z0-9_-]{11}$/D', $query['v'])) { $id = $query['v']; }
            }
            if ($path === '/playlist') {
                parse_str((string)($parts['query'] ?? ''), $query);
                if (is_string($query['list'] ?? null) && preg_match('/^[A-Za-z0-9_-]{12,64}$/D', $query['list'])) {
                    return 'https://www.youtube-nocookie.com/embed/videoseries?list=' . rawurlencode($query['list']);
                }
            }
        } elseif ($host === 'youtu.be') {
            if (preg_match('~^/([A-Za-z0-9_-]{11})/?$~D', $path, $m)) { $id = $m[1]; }
        }
        return $id !== '' ? 'https://www.youtube-nocookie.com/embed/' . $id : '';
    }
    public static function sanitize_media_settings($input) {
        if (!is_array($input)) { return self::media_defaults(); }
        $substack = self::media_validate_url($input['substack_url'] ?? '', 'substack');
        $youtube = self::media_validate_url($input['youtube_url'] ?? '', 'youtube');
        $featured = is_string($input['featured_video_url'] ?? null) ? trim($input['featured_video_url']) : '';
        if ($featured !== '' && self::video_embed_url($featured) === '') {
            add_settings_error(self::MEDIA_OPTION, 'invalid_featured', 'Featured YouTube URL must be a public video or playlist URL.');
            $featured = '';
        }
        if (!empty($input['substack_url']) && $substack === '') {
            add_settings_error(self::MEDIA_OPTION, 'invalid_substack', 'Use a public HTTPS Substack publication root URL.');
        }
        if (!empty($input['youtube_url']) && $youtube === '') {
            add_settings_error(self::MEDIA_OPTION, 'invalid_youtube', 'Use a public HTTPS YouTube channel URL.');
        }
        $linkedin = self::media_social_url($input['linkedin_url'] ?? '', 'linkedin');
        if (!empty($input['linkedin_url']) && $linkedin === '') {
            add_settings_error(self::MEDIA_OPTION, 'invalid_linkedin', 'LinkedIn must be a public company, showcase or profile URL.');
        }
        $socials = array();
        foreach (self::media_social_catalog() as $kind => $descriptor) {
            $key = $descriptor[1];
            $socials[$key] = self::media_social_url($input[$key] ?? '', $kind);
            if (!empty($input[$key]) && $socials[$key] === '') {
                add_settings_error(self::MEDIA_OPTION, 'invalid_social_' . $kind, 'Invalid public ' . $descriptor[0] . ' profile URL.');
            }
        }
        $channel_id = is_string($input['youtube_channel_id'] ?? null) ? trim($input['youtube_channel_id']) : '';
        if ($channel_id !== '' && !preg_match('/^UC[A-Za-z0-9_-]{22}$/D', $channel_id)) {
            add_settings_error(self::MEDIA_OPTION, 'invalid_youtube_channel_id', 'YouTube discovery requires a public channel ID beginning UC with 24 total characters.');
            $channel_id = '';
        }
        return array_merge(array(
            'substack_url' => $substack,
            'youtube_url' => $youtube,
            'featured_video_url' => $featured,
            'linkedin_url' => $linkedin,
            'show_feed' => !empty($input['show_feed']) ? '1' : '0',
            'show_subscribe_embed' => !empty($input['show_subscribe_embed']) ? '1' : '0',
            'enable_discovery' => !empty($input['enable_discovery']) ? '1' : '0',
            'youtube_channel_id' => $channel_id,
            'show_wp_updates' => !empty($input['show_wp_updates']) ? '1' : '0',
        ), $socials);
    }
    public static function field_media_substack() { self::media_field_url('substack_url', 'Substack publication URL (custom domains supported).'); }
    public static function field_media_youtube() { self::media_field_url('youtube_url', 'YouTube channel URL or @handle.'); }
    public static function field_media_linkedin() { self::media_field_url('linkedin_url', 'Public LinkedIn company/showcase or profile URL. Blank until verified.'); }
    public static function field_media_socials() {
        $options = self::media_settings();
        foreach (self::media_social_catalog() as $kind => $descriptor) {
            $key = $descriptor[1];
            echo '<div class="scec-media-admin-social"><label for="scec-' . esc_attr($key) . '">' . esc_html($descriptor[0]) . '</label> ';
            echo '<input type="url" id="scec-' . esc_attr($key) . '" class="regular-text" name="' . esc_attr(self::MEDIA_OPTION . '[' . $key . ']') . '" value="' . esc_attr((string)($options[$key] ?? '')) . '" autocomplete="off"></div>';
        }
        echo '<p class="description">Enter only official public profile URLs. Empty channels are not linked from the Media page. No content is imported from social platforms.</p>';
    }
    public static function field_media_video() { self::media_field_url('featured_video_url', 'Optional: YouTube video or playlist URL. Embeds only after a visitor clicks play.'); }
    private static function media_field_url($key, $description) {
        $options = self::media_settings();
        echo '<input type="url" class="regular-text" name="' . esc_attr(self::MEDIA_OPTION . '[' . $key . ']') . '" value="' . esc_attr((string)$options[$key]) . '" autocomplete="off">';
        echo '<p class="description">' . esc_html($description) . '</p>';
    }
    public static function field_media_feed() { self::media_field_checkbox('show_feed', 'Show latest public Substack posts from its RSS feed (cached by WordPress).'); }
    public static function field_media_embed() { self::media_field_checkbox('show_subscribe_embed', 'Enable click-to-load native Substack signup form. No third-party requests from a visitor until clicked.'); }
    public static function field_media_discovery() { self::media_field_checkbox('enable_discovery', 'Show a unified chronological list of public source links. Off until explicitly enabled.'); }
    public static function field_media_wordpress_updates() { self::media_field_checkbox('show_wp_updates', 'Include published, non-password-protected WordPress posts tagged media-update.'); }
    public static function field_media_youtube_id() {
        $options = self::media_settings();
        echo '<input type="text" class="regular-text" maxlength="24" pattern="UC[A-Za-z0-9_-]{22}" name="' . esc_attr(self::MEDIA_OPTION . '[youtube_channel_id]') . '" value="' . esc_attr((string)($options['youtube_channel_id'] ?? '')) . '" autocomplete="off">';
        echo '<p class="description">The 24-character UC… channel ID from the public YouTube channel URL (not the @handle). Leave blank to omit automatic video headlines. YouTube feeds are best-effort and may be unavailable.</p>';
    }
    private static function media_field_checkbox($key, $description) {
        $options = self::media_settings();
        echo '<label><input type="checkbox" name="' . esc_attr(self::MEDIA_OPTION . '[' . $key . ']') . '" value="1" ' . checked($options[$key], '1', false) . '> ' . esc_html($description) . '</label>';
    }
    private static function media_public_card($title, $description, $slugs) {
        $url = self::resolve_public_page($slugs);
        $content = '<strong>' . esc_html($title) . '</strong><span>' . esc_html($description) . '</span>';
        if ($url) {
            return '<a class="scec-media-tile" href="' . esc_url($url) . '">' . $content . '<small>Visit section <span aria-hidden="true">↗</span></small></a>';
        }
        return '<div class="scec-media-tile scec-media-pending">' . $content . '<small>Not yet published</small></div>';
    }
    /** Render text-only RSS headlines; WordPress manages feed caching and safe HTTP requests. */
    private static function render_substack_feed($publication_url) {
        if ($publication_url === '') { return ''; }
        if (!function_exists('fetch_feed') && defined('ABSPATH') && defined('WPINC')) {
            $feed_file = ABSPATH . WPINC . '/feed.php';
            if (is_file($feed_file)) { require_once $feed_file; }
        }
        if (!function_exists('fetch_feed')) { return ''; }
        $feed_url = rtrim($publication_url, '/') . '/feed';
        if (!wp_http_validate_url($feed_url)) { return ''; }
        $feed = fetch_feed($feed_url);
        if (is_wp_error($feed)) { return ''; }
        $items = $feed->get_items(0, 3);
        if (!is_array($items) || !$items) { return ''; }
        $host = strtolower((string)wp_parse_url($publication_url, PHP_URL_HOST));
        $rows = '';
        foreach ($items as $item) {
            $url = (string)$item->get_permalink();
            $title = trim(wp_strip_all_tags((string)$item->get_title()));
            if ($title === '' || strtolower((string)wp_parse_url($url, PHP_URL_HOST)) !== $host || !wp_http_validate_url($url)) { continue; }
            $rows .= '<li><a href="' . esc_url($url) . '" rel="noopener noreferrer">' . esc_html($title) . '</a></li>';
        }
        return $rows !== '' ? '<div class="scec-media-issues"><h4>Recent newsletter issues</h4><ul>' . $rows . '</ul></div>' : '';
    }
    /** MEDIA-03 uses safe same-source public feed metadata only, never private backend records. */
    private static function media03_fetch($url, $kind, $source_host = '', $channel_id = '') {
        if (!function_exists('wp_safe_remote_get') || !function_exists('get_transient') || !function_exists('set_transient')) { return array(); }
        if (!wp_http_validate_url($url) || !preg_match('~^https://~i', $url)) { return array(); }
        $key = 'scec_media03_' . md5($kind . '|' . $url . '|v1');
        $cached = get_transient($key);
        if (is_array($cached)) { return $cached; }
        $response = wp_safe_remote_get($url, array(
            'timeout' => 5, 'redirection' => 0, 'limit_response_size' => 262144,
            'headers' => array('Accept' => 'application/rss+xml, application/atom+xml, application/xml'),
            'user-agent' => 'SustainableCatalyst-Media/8.8.7 (public feed metadata)',
        ));
        if (is_wp_error($response) || (int)wp_remote_retrieve_response_code($response) !== 200) {
            set_transient($key, array(), 10 * MINUTE_IN_SECONDS);
            return array();
        }
        $body = wp_remote_retrieve_body($response);
        if (!is_string($body) || strlen($body) > 262144 || stripos($body, '<!DOCTYPE') !== false ||
            stripos($body, '<!ENTITY') !== false || !function_exists('simplexml_load_string')) {
            set_transient($key, array(), 10 * MINUTE_IN_SECONDS);
            return array();
        }
        $prior = libxml_use_internal_errors(true);
        $xml = simplexml_load_string($body, 'SimpleXMLElement', LIBXML_NONET | LIBXML_NOCDATA);
        libxml_clear_errors();
        libxml_use_internal_errors($prior);
        if ($xml === false || !in_array(strtolower($xml->getName()), array('rss', 'feed'), true)) {
            set_transient($key, array(), 10 * MINUTE_IN_SECONDS);
            return array();
        }
        $items = $xml->xpath('//*[local-name()="item" or local-name()="entry"]');
        if (!is_array($items)) { $items = array(); }
        $results = array();
        foreach (array_slice($items, 0, 12) as $item) {
            $titles = $item->xpath('./*[local-name()="title"]');
            $title = trim(wp_strip_all_tags((string)($titles[0] ?? '')));
            if ($title === '') { continue; }
            $title = function_exists('mb_substr') ? mb_substr($title, 0, 180) : substr($title, 0, 180);
            $dates = $item->xpath('./*[local-name()="pubDate" or local-name()="published" or local-name()="updated"]');
            $when = strtotime((string)($dates[0] ?? ''));
            $when = is_int($when) && $when > 0 && $when < time() + DAY_IN_SECONDS ? $when : 0;
            if ($kind === 'youtube') {
                $video_nodes = $item->xpath('./*[local-name()="videoId"]');
                $video_id = trim((string)($video_nodes[0] ?? ''));
                $channel_nodes = $item->xpath('./*[local-name()="channelId"]');
                if ($channel_nodes && trim((string)$channel_nodes[0]) !== $channel_id) { continue; }
                if (!preg_match('/^[A-Za-z0-9_-]{11}$/D', $video_id)) { continue; }
                $link = 'https://www.youtube.com/watch?v=' . $video_id;
                $label = 'YouTube';
            } else {
                $links = $item->xpath('./*[local-name()="link"]');
                $link = '';
                foreach ((array)$links as $node) {
                    $attrs = $node->attributes();
                    $rel = isset($attrs['rel']) ? (string)$attrs['rel'] : '';
                    if ($rel !== '' && $rel !== 'alternate') { continue; }
                    $candidate = isset($attrs['href']) ? (string)$attrs['href'] : trim((string)$node);
                    if ($candidate !== '') { $link = $candidate; break; }
                }
                $parts = wp_parse_url($link);
                if (!is_array($parts) || strtolower((string)($parts['scheme'] ?? '')) !== 'https' ||
                    strtolower((string)($parts['host'] ?? '')) !== $source_host ||
                    isset($parts['user']) || isset($parts['pass']) || isset($parts['port']) ||
                    !wp_http_validate_url($link)) { continue; }
                $label = 'Substack';
            }
            $results[] = array('title' => $title, 'url' => $link, 'date' => $when, 'source' => $label);
            if (count($results) >= 5) { break; }
        }
        set_transient($key, $results, HOUR_IN_SECONDS);
        return $results;
    }
    private static function media03_wp_updates() {
        if (!function_exists('get_posts')) { return array(); }
        $posts = get_posts(array('post_type' => 'post', 'post_status' => 'publish', 'tag' => 'media-update',
            'posts_per_page' => 5, 'ignore_sticky_posts' => true, 'no_found_rows' => true));
        $items = array();
        foreach ((array)$posts as $post) {
            if (!is_object($post) || ($post->post_status ?? '') !== 'publish' || post_password_required($post)) { continue; }
            $link = get_permalink($post);
            if (!$link || !wp_http_validate_url($link) ||
                strtolower((string)wp_parse_url($link, PHP_URL_HOST)) !== strtolower((string)wp_parse_url(home_url('/'), PHP_URL_HOST))) { continue; }
            $title = trim(wp_strip_all_tags((string)get_the_title($post)));
            if ($title === '') { continue; }
            $date = strtotime((string)($post->post_date_gmt ?? ''));
            $items[] = array('title' => $title, 'url' => $link,
                'date' => is_int($date) && $date > 0 ? $date : 0, 'source' => 'Publications');
        }
        return $items;
    }
    private static function media03_updates($options, $substack) {
        if (($options['enable_discovery'] ?? '0') !== '1') { return ''; }
        $items = array();
        if ($substack !== '' && ($options['show_feed'] ?? '0') === '1') {
            $feed_url = rtrim($substack, '/') . '/feed';
            $items = array_merge($items, self::media03_fetch($feed_url, 'substack', strtolower((string)wp_parse_url($substack, PHP_URL_HOST))));
        }
        $channel_id = (string)($options['youtube_channel_id'] ?? '');
        if (preg_match('/^UC[A-Za-z0-9_-]{22}$/D', $channel_id)) {
            $feed_url = 'https://www.youtube.com/feeds/videos.xml?channel_id=' . $channel_id;
            $videos = self::media03_fetch($feed_url, 'youtube', 'www.youtube.com', $channel_id);
            // YouTube occasionally migrates feed paths: only fixed first-party endpoints are tried.
            if (!$videos) { $videos = self::media03_fetch('https://www.youtube.com/xml/feeds/videos.xml?channel_id=' . $channel_id, 'youtube', 'www.youtube.com', $channel_id); }
            $items = array_merge($items, $videos);
        }
        if (($options['show_wp_updates'] ?? '0') === '1') { $items = array_merge($items, self::media03_wp_updates()); }
        $seen = array(); $unique = array();
        foreach ($items as $item) {
            $key = (string)($item['url'] ?? '');
            if ($key === '' || isset($seen[$key])) { continue; }
            $seen[$key] = true;
            $unique[] = $item;
        }
        usort($unique, function($a,$b) { return ((int)$b['date']) <=> ((int)$a['date']); });
        $rows = '';
        foreach (array_slice($unique, 0, 6) as $item) {
            $date = !empty($item['date']) ? wp_date('M j, Y', (int)$item['date']) : '';
            $rows .= '<li class="scec-media03-item"><span class="scec-media03-meta">' . esc_html($item['source'])
                . ($date ? ' &middot; ' . esc_html($date) : '') . '</span><a href="' . esc_url($item['url'])
                . '" target="_blank" rel="noopener noreferrer external">' . esc_html($item['title'])
                . ' <span aria-hidden="true">↗</span></a></li>';
        }
        if ($rows === '') {
            $body = '<p class="scec-media-muted">No public updates are available from the enabled sources right now. Visit the linked channels directly for their latest posts.</p>';
        } else {
            $body = '<ol class="scec-media03-list">' . $rows . '</ol>';
        }
        return '<section class="scec-media-secondary scec-media03" id="scec-media-latest" aria-labelledby="scec-media-latest-heading">'
            . '<span class="scec-media-index">LATEST / PUBLIC CHANNELS</span><h3 id="scec-media-latest-heading">Latest from our channels</h3>'
            . '<p>Recent public items from connected sources, linked to their original publishers. Updates may be delayed by caching or source availability.</p>'
            . $body . '</section>';
    }

    /** Media landing; backwards-compatible alias for the old [sc_press] shortcode. */
    public static function render_media($attrs = array()) {
        self::start_assets();
        wp_enqueue_script('sc-ec-media');
        $options = self::media_settings();
        $substack = self::media_validate_url($options['substack_url'], 'substack');
        $youtube = self::media_validate_url($options['youtube_url'], 'youtube');
        $featured = self::video_embed_url($options['featured_video_url']);
        $linkedin = self::media_social_url($options['linkedin_url'] ?? '', 'linkedin');
        $social_cards = self::render_social_cards($options);
        $subscribe_url = $substack !== '' ? rtrim($substack, '/') . '/subscribe' : '';
        $feed = $substack !== '' && $options['show_feed'] === '1' && ($options['enable_discovery'] ?? '0') !== '1' ? self::render_substack_feed($substack) : '';
        $latest = self::media03_updates($options, $substack);
        $press = self::media_public_card('Press & News', 'Official releases, public statements, and institutional announcements.', array('press-releases', 'newsroom', 'institutional-updates', 'announcements'));
        $events = self::media_public_card('Events & Briefings', 'Public events, webinars, presentations, and briefings.', array('events', 'webinars', 'briefings'));
        $inquiries = self::media_public_card('Media Inquiries', 'Institutional and journalist inquiries.', array('press-contact', 'media-contact', 'contact', 'contact-us'));
        ob_start(); ?>
        <section class="scec-media" aria-labelledby="scec-media-heading">
          <div class="scec-media-masthead"><span>SUSTAINABLE CATALYST / PUBLIC COMMUNICATIONS</span><span>MEDIA</span></div>
          <div class="scec-media-hero"><div class="scec-media-eyebrow">MEDIA &amp; COMMUNICATIONS</div>
            <h2 id="scec-media-heading">Media<span class="scec-media-red">.</span></h2>
            <p>Official news, research communications, newsletters, videos, and public briefings from Sustainable Catalyst.</p></div>
          <nav class="scec-media-nav" aria-label="Media page sections"><?php if ($latest) : ?><a href="#scec-media-latest">Latest</a><?php endif; ?><a href="#scec-media-newsletter">Newsletter</a><a href="#scec-media-video">Video</a><a href="#scec-media-linkedin">LinkedIn</a><a href="#scec-media-socials">Socials</a><a href="#scec-media-news">Press &amp; News</a><a href="#scec-media-contact">Inquiries</a></nav>
          <?php echo $latest; // Public links and text escaped in MEDIA-03. ?>
          <div class="scec-media-main">
            <section class="scec-media-feature" id="scec-media-newsletter" aria-labelledby="scec-media-newsletter-title">
              <div class="scec-media-feature-head"><div><span class="scec-media-index">01 / NEWSLETTER</span><h3 id="scec-media-newsletter-title">Sustainable Catalyst on Substack</h3></div><span class="scec-media-channel">NEWSLETTER</span></div>
              <p>Analysis, research updates, and institutional commentary delivered through our Substack publication.</p>
              <?php if ($substack) : ?><div class="scec-media-actions"><a class="scec-media-primary" href="<?php echo esc_url($subscribe_url); ?>" target="_blank" rel="noopener noreferrer external">Subscribe on Substack <span aria-hidden="true">↗</span></a><a class="scec-media-text-link" href="<?php echo esc_url($substack); ?>" target="_blank" rel="noopener noreferrer external">Newsletter archive <span aria-hidden="true">↗</span></a></div>
                <?php echo $feed; // Escaped and validated per item. ?>
                <?php if ($options['show_subscribe_embed'] === '1') : ?><div class="scec-media-load-wrap"><button type="button" class="scec-media-load" data-scec-embed="<?php echo esc_attr(rtrim($substack, '/') . '/embed'); ?>" data-scec-embed-title="Sustainable Catalyst Substack signup" data-scec-kind="substack">Open subscription form here</button><small>Loads Substack's form only when selected. Subscription data is handled by Substack.</small></div><?php endif; ?>
              <?php else : ?><p class="scec-media-muted">Newsletter connection has not been configured.</p><?php endif; ?>
            </section>
            <section class="scec-media-feature" id="scec-media-video" aria-labelledby="scec-media-video-title">
              <div class="scec-media-feature-head"><div><span class="scec-media-index">02 / VIDEO</span><h3 id="scec-media-video-title">Sustainable Catalyst on YouTube</h3></div><span class="scec-media-channel">VIDEO</span></div>
              <p>Research explainers, presentations, discussions, and other Sustainable Catalyst video programming.</p>
              <?php if ($youtube) : ?><div class="scec-media-actions"><a class="scec-media-primary" href="<?php echo esc_url($youtube); ?>" target="_blank" rel="noopener noreferrer external">View YouTube channel <span aria-hidden="true">↗</span></a></div><?php else : ?><p class="scec-media-muted">YouTube connection has not been configured.</p><?php endif; ?>
              <?php if ($featured) : ?><div class="scec-media-load-wrap scec-media-video-wrap"><button type="button" class="scec-media-load" data-scec-embed="<?php echo esc_attr($featured); ?>" data-scec-embed-title="Featured Sustainable Catalyst video" data-scec-kind="youtube">Play featured video</button><small>Playing a video loads the YouTube privacy-enhanced player.</small></div><?php endif; ?>
            </section>
          </div>
          <section class="scec-media-secondary scec-media-linkedin" id="scec-media-linkedin" aria-labelledby="scec-media-linkedin-heading">
            <div class="scec-media-linkedin-layout">
              <div><span class="scec-media-index">03 / PROFESSIONAL NETWORK</span><h3 id="scec-media-linkedin-heading">LinkedIn</h3><p>Institutional developments, research highlights, professional conversations, and project milestones from Sustainable Catalyst.</p></div>
              <div class="scec-media-linkedin-action">
                <?php if ($linkedin) : ?><a class="scec-media-primary" href="<?php echo esc_url($linkedin); ?>" target="_blank" rel="noopener noreferrer external">Connect on LinkedIn <span aria-hidden="true">↗</span></a>
                <?php else : ?><p class="scec-media-muted">Our official LinkedIn page is not yet connected.</p><?php endif; ?>
              </div>
            </div>
          </section>
          <section class="scec-media-secondary scec-media-socials" id="scec-media-socials" aria-labelledby="scec-media-socials-heading">
            <span class="scec-media-index">04 / SOCIAL CHANNELS</span><h3 id="scec-media-socials-heading">Follow Sustainable Catalyst</h3>
            <p>Find our official public channels. Each connection is managed independently and opens on its original platform.</p>
            <?php if ($social_cards) : ?><div class="scec-media-social-grid"><?php echo $social_cards; // Admin-configured, validated profile URLs. ?></div>
            <?php else : ?><p class="scec-media-muted">Additional social profiles will appear here when connected.</p><?php endif; ?>
          </section>
          <section class="scec-media-secondary" id="scec-media-news" aria-labelledby="scec-media-news-heading"><span class="scec-media-index">05 / INSTITUTIONAL COMMUNICATIONS</span><h3 id="scec-media-news-heading">News, events &amp; resources</h3><div class="scec-media-cards"><?php echo $press . $events; // Sanitized internal WordPress page links. ?></div></section>
          <section class="scec-media-secondary scec-media-secondary-bottom" id="scec-media-contact" aria-labelledby="scec-media-contact-heading"><span class="scec-media-index">06 / CONNECT</span><h3 id="scec-media-contact-heading">Media inquiries</h3><div class="scec-media-cards"><?php echo $inquiries; // Sanitized internal WordPress page link. ?></div></section>
          <footer class="scec-media-footer"><strong>Public communications, with clear source boundaries.</strong><p>Media is the public communications hub. Publications remains the editorial blog; Research maintains authoritative scientific work. LinkedIn, social networks, Substack and YouTube remain independent platforms; no subscriber data or social-account credentials are collected here.</p></footer>
        </section><?php
        return ob_get_clean();
    }

    private static function url() { return self::sanitize_url((string)get_option(self::OPTION, '')); }
    public static function render_launch($attrs = array()) {
        self::start_assets();
        $url = self::url();
        if (!$url) { return '<span class="scec880-unavailable">Standalone application launch pending HTTPS configuration</span>'; }
        return '<a class="scec880-action" href="' . esc_url($url) . '" target="_blank" rel="noopener noreferrer external">Open standalone application <span aria-hidden="true">↗</span></a>';
    }
    public static function render($attrs = array()) {
        self::start_assets();
        $url = self::url();
        ob_start(); ?>
        <section class="scec880" aria-labelledby="scec880-heading">
          <div class="scec880-kicker">SUSTAINABLE CATALYST / INDEPENDENT OPERATING SURFACE <span>8.8.8</span></div>
          <div class="scec880-intro">
            <div><h2 id="scec880-heading">Engagement <span>&amp;</span><br>Communications</h2>
            <p>Institutional relationships, support, advisory workflows, and accountable communication—organized within an independent application.</p></div>
            <div class="scec880-status"><span class="scec880-dot" aria-hidden="true"></span> READ-ONLY PREVIEW<br><small>No customer records exposed through WordPress</small></div>
          </div>
          <div class="scec880-grid">
            <div><b>01 / CONTACTS</b><span>Organization-aware relationship structures</span></div>
            <div><b>02 / ENGAGEMENT</b><span>Interaction and communication lifecycle</span></div>
            <div><b>03 / SUPPORT</b><span>Case and service workflow surfaces</span></div>
            <div><b>04 / ADVISORY</b><span>Institutional review and approval pathways</span></div>
            <div><b>05 / ACTIVITY</b><span>Accountability and audit boundaries</span></div>
            <div><b>06 / PRIVACY</b><span>Role-aware authorization foundations</span></div>
          </div>
          <div class="scec880-footer"><div><strong>Independent by design.</strong><p>WordPress is the entry point—not the system of record, credential broker, or privileged API proxy.</p></div>
          <?php if ($url) : ?><a class="scec880-action" href="<?php echo esc_url($url); ?>" target="_blank" rel="noopener noreferrer external">Open standalone application <span aria-hidden="true">↗</span></a>
          <?php else : ?><span class="scec880-unavailable">Standalone launch available after HTTPS setup</span><?php endif; ?></div>
          <?php echo self::render_public_links(); ?>
        </section><?php
        return ob_get_clean();
    }
}
require_once __DIR__ . '/includes/media04-workflow.php';
require_once __DIR__ . '/includes/media05-bridge.php';
SC_Engagement_Bridge_882::boot();
SC_Media04_Workflow::boot();
SC_Media05_Bridge::boot();
