<?php
/**
 * Plugin Name: Sustainable Catalyst — Engagement & Communications Bridge
 * Description: Public, read-only WordPress launch surface for the independent Engagement & Communications app.
 * Version: 8.8.2
 * Author: Content Catalyst LLC
 * Text Domain: sc-engagement-bridge
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Engagement_Bridge_882 {
    const OPTION = 'sc_ec880_app_url';
    const VERSION = '8.8.2';
    public static function boot() {
        add_action('admin_init', array(__CLASS__, 'register_settings'));
        add_action('admin_menu', array(__CLASS__, 'menu'));
        add_action('wp_enqueue_scripts', array(__CLASS__, 'enqueue_assets'));
        add_shortcode('sc_engagement_communications', array(__CLASS__, 'render'));
        add_shortcode('sc_engagement_launch', array(__CLASS__, 'render_launch'));
        add_shortcode('sc_engagement_public_links', array(__CLASS__, 'render_public_links'));
    }
    public static function register_assets() {
        wp_register_style('sc-ec880-bridge', plugins_url('assets/bridge.css', __FILE__), array(), self::VERSION);
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
        if (strpos($path, '//') === 0 || preg_match('/[\r\n]/', $path)) {
            return get_option(self::OPTION, '');
        }
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
    }
    public static function field() {
        $value = get_option(self::OPTION, '');
        echo '<input type="url" class="regular-text" name="' . esc_attr(self::OPTION) . '" value="' . esc_attr($value) . '" placeholder="https://engagement.example.org/" autocomplete="off">';
        echo '<p class="description">Leave blank until public HTTPS deployment. Do not enter a private localhost address.</p>';
    }
    public static function menu() {
        add_options_page('Engagement Bridge', 'Engagement Bridge', 'manage_options', 'sc_ec880', array(__CLASS__, 'settings_page'));
    }
    public static function settings_page() {
        if (!current_user_can('manage_options')) { return; }
        echo '<div class="wrap"><h1>Engagement &amp; Communications Bridge</h1><form method="post" action="options.php">';
        settings_fields('sc_ec880_settings'); do_settings_sections('sc_ec880'); submit_button('Save application URL');
        echo '</form><p>Shortcodes: <code>[sc_engagement_communications]</code> <code>[sc_engagement_launch]</code>, and <code>[sc_engagement_public_links]</code>.</p></div>';
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
            array('Channel', 'Updates and public communications', array('channel')),
            array('Support', 'Technical questions and service assistance', array('support')),
        );
        $items = '';
        foreach ($pages as $item) {
            $link = self::resolve_public_page($item[2]);
            if (!$link) { continue; }
            $items .= '<a class="scec881-public-link" href="' . esc_url($link) . '"><strong>' . esc_html($item[0]) . '</strong><span>' . esc_html($item[1]) . '</span><span aria-hidden="true">↗</span></a>';
        }
        if ($items === '') { return ''; }
        return '<nav class="scec881-public" aria-label="Existing Sustainable Catalyst public services"><div class="scec881-public-heading"><strong>Public communication channels</strong><p>These existing pages remain independent. The Engagement hub does not replace their forms or submission workflows.</p></div><div class="scec881-public-grid">' . $items . '</div></nav>';
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
          <div class="scec880-kicker">SUSTAINABLE CATALYST / INDEPENDENT OPERATING SURFACE <span>8.8.2</span></div>
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
SC_Engagement_Bridge_882::boot();
