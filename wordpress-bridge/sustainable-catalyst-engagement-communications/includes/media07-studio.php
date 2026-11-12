<?php
/**
 * MEDIA-07 — Private WordPress Newsletter Studio (Substack-first).
 *
 * Editor revisions are private WP metadata, never posts or public REST output.
 * The browser compiles and downloads email HTML; this endpoint never sends.
 * No Substack credentials, subscriber lists, SMTP, or provider API integration.
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Media07_Studio {
    const PAGE = 'scec-media07';
    const TYPE = 'scec_newsletter';
    const META = '_scec_media07_';
    const MAX_JSON_BYTES = 262144;

    public static function boot() {
        add_action('init', array(__CLASS__, 'register_type'));
        add_action('admin_menu', array(__CLASS__, 'menu'));
        add_action('admin_enqueue_scripts', array(__CLASS__, 'assets'));
        add_action('wp_ajax_scec07_save', array(__CLASS__, 'save'));
        add_action('wp_ajax_scec07_load', array(__CLASS__, 'load'));
        add_action('wp_ajax_scec07_sync_staging', array(__CLASS__, 'sync_staging_draft'));
    }

    public static function register_type() {
        register_post_type(self::TYPE, array(
            'label' => 'Private newsletters',
            'public' => false, 'publicly_queryable' => false,
            'show_ui' => false, 'show_in_rest' => false,
            'exclude_from_search' => true, 'has_archive' => false,
            'rewrite' => false,
            'supports' => array('title', 'author'),
            'capability_type' => 'post',
            'map_meta_cap' => false,
            'capabilities' => array_fill_keys(array(
                'edit_post','read_post','delete_post','edit_posts','edit_others_posts',
                'publish_posts','read_private_posts','delete_posts','delete_private_posts',
                'delete_published_posts','delete_others_posts','edit_private_posts',
                'edit_published_posts','create_posts'
            ), 'manage_options'),
        ));
    }

    public static function menu() {
        add_submenu_page('options-general.php', 'Newsletter Studio',
            'Newsletter Studio (MEDIA-07)', 'manage_options',
            self::PAGE, array(__CLASS__, 'screen'));
    }

    public static function assets($hook) {
        if ($hook !== 'settings_page_' . self::PAGE || !current_user_can('manage_options')) { return; }
        $base = plugin_dir_url(dirname(__DIR__) . '/sustainable-catalyst-engagement-communications.php');
        // Production candidate assets are self-hosted by the CI release ZIP.
        // Source checkouts without vendor assets can use pinned CDN for local staging.
        $vendor_dir = dirname(__DIR__) . '/assets/vendor/';
        $local = is_file($vendor_dir . 'grapes.min.js') &&
            is_file($vendor_dir . 'grapes.min.css') &&
            is_file($vendor_dir . 'grapesjs-mjml.min.js');
        $grapes_css = $local ? $base . 'assets/vendor/grapes.min.css'
            : 'https://cdn.jsdelivr.net/npm/grapesjs@0.23.6/dist/css/grapes.min.css';
        $grapes_js = $local ? $base . 'assets/vendor/grapes.min.js'
            : 'https://cdn.jsdelivr.net/npm/grapesjs@0.23.6/dist/grapes.min.js';
        $mjml_js = $local ? $base . 'assets/vendor/grapesjs-mjml.min.js'
            : 'https://cdn.jsdelivr.net/npm/grapesjs-mjml@1.0.8/dist/grapesjs-mjml.min.js';
        wp_enqueue_style('scec07-grapesjs', $grapes_css, array(), '0.23.6');
        wp_enqueue_script('scec07-grapesjs', $grapes_js, array(), '0.23.6', true);
        wp_enqueue_script('scec07-mjml', $mjml_js,
            array('scec07-grapesjs'), '1.0.8', true);
        wp_enqueue_style('scec07-ui', $base . 'assets/media07-studio.css',
            array('scec07-grapesjs'), '8.9.4');
        wp_enqueue_script('scec07-ui', $base . 'assets/media07-studio.js',
            array('scec07-mjml'), '8.9.4', true);
        wp_enqueue_media();
        wp_add_inline_script('scec07-ui', 'window.SCEC07_BOOT = ' .
            wp_json_encode(array(
                'ajaxUrl' => admin_url('admin-ajax.php'),
                'nonce' => wp_create_nonce('scec07_editor'),
                'issues' => self::list_issues(),
                'substackUrl' => 'https://newsletter.sustainablecatalyst.com/',
                'maxJsonBytes' => self::MAX_JSON_BYTES,
                'listmonkStagingAvailable' => self::bridge_ready(),
            ), JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT) . ';', 'before');
    }

    private static function list_issues() {
        $posts = get_posts(array(
            'post_type' => self::TYPE, 'post_status' => 'private',
            'numberposts' => 100, 'orderby' => 'modified', 'order' => 'DESC'
        ));
        return array_map(function($p) {
            return array(
                'id' => (int)$p->ID,
                'title' => $p->post_title,
                'revision' => (int)get_post_meta($p->ID, self::META . 'revision', true),
                'modified' => get_post_modified_time('c', true, $p->ID),
            );
        }, $posts);
    }

    private static function authorize() {
        if (!current_user_can('manage_options')) {
            wp_send_json_error(array('message'=>'Forbidden'), 403);
        }
        if (!check_ajax_referer('scec07_editor', 'nonce', false)) {
            wp_send_json_error(array('message'=>'Invalid or expired editor nonce'), 403);
        }
        if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
            wp_send_json_error(array('message'=>'POST required'), 405);
        }
    }

    private static function issue($id) {
        if ($id <= 0) { return null; }
        $p = get_post($id);
        return ($p && $p->post_type === self::TYPE && $p->post_status === 'private')
            ? $p : null;
    }

    /** Validate only JSON structure and bounded size, not renderability or MJML safety. */
    public static function validate_project($raw) {
        if (!is_string($raw) || strlen($raw) < 2 || strlen($raw) > self::MAX_JSON_BYTES) {
            return false;
        }
        $project = json_decode($raw, true, 48);
        if (!is_array($project) || json_last_error() !== JSON_ERROR_NONE ||
            !isset($project['pages']) || !is_array($project['pages']) ||
            count($project['pages']) !== 1) { return false; }
        // The actual markup is rendered only in the authenticated admin browser,
        // never echoed by PHP or used in a public template.
        return $project;
    }


    /** Bounded, inert HTML for a synthetic staging draft. No template execution. */
    public static function validate_compiled_html($html) {
        return is_string($html) && strlen($html) >= 20 && strlen($html) <= 100000 &&
            !preg_match('/<\s*\/?\s*(?:script|iframe|object|embed|form|input|svg|math)\b|on[a-z]{3,24}\s*=|javascript\s*:/i', $html) &&
            strpos($html, '{{') === false && strpos($html, '}}') === false;
    }

    public static function save() {
        self::authorize();
        $id = isset($_POST['id']) ? absint($_POST['id']) : 0;
        $title = sanitize_text_field(wp_unslash((string)($_POST['title'] ?? '')));
        $subject = sanitize_text_field(wp_unslash((string)($_POST['subject'] ?? '')));
        $preheader = sanitize_text_field(wp_unslash((string)($_POST['preheader'] ?? '')));
        $raw = wp_unslash((string)($_POST['project'] ?? ''));
        $rev = isset($_POST['revision']) ? absint($_POST['revision']) : 0;
        $project = self::validate_project($raw);
        $html = wp_unslash((string)($_POST['compiled_html'] ?? ''));
        if (!self::validate_compiled_html($html)) {
            wp_send_json_error(array('message'=>'Save requires valid compiled synthetic-safe newsletter HTML'), 422);
        }
        $html_sha = hash('sha256', $html);
        if ($title === '' || $subject === '' ||
            strlen($title) > 140 || strlen($subject) > 200 ||
            strlen($preheader) > 180 || $project === false) {
            wp_send_json_error(array('message'=>'Invalid metadata or newsletter project'), 422);
        }

        $p = self::issue($id);
        if ($id > 0 && !$p) { wp_send_json_error(array('message'=>'Newsletter not found'), 404); }
        $latest_rev = $p ? (int)get_post_meta($id, self::META . 'revision', true) : 0;
        if ($rev !== $latest_rev) {
            wp_send_json_error(array('message'=>'Revision conflict. Reload before saving to avoid overwriting changes.',
                'revision'=>$latest_rev), 409);
        }
        if (!$p) {
            $id = wp_insert_post(array(
                'post_type'=>self::TYPE, 'post_status'=>'private',
                'post_title'=>$title, 'post_author'=>get_current_user_id()
            ), true);
            if (is_wp_error($id) || !$id) {
                wp_send_json_error(array('message'=>'Could not create private newsletter'), 500);
            }
        } else {
            $result = wp_update_post(array('ID'=>$id, 'post_title'=>$title), true);
            if (is_wp_error($result)) {
                wp_send_json_error(array('message'=>'Could not update newsletter'), 500);
            }
        }

        // Store editable project JSON only, not compiled HTML or subscriber details.
        $canonical = wp_json_encode($project, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        $sha = hash('sha256', $canonical . "\n" . $subject . "\n" . $preheader . "\n" . $html_sha);
        $next = $latest_rev + 1;
        update_post_meta($id, self::META . 'project', wp_slash($canonical));
        // The exact HTML used for staging is now bound to the saved revision.
        // Existing legacy revisions must be re-saved before staging transfer.
        update_post_meta($id, self::META . 'compiled_html', wp_slash($html));
        update_post_meta($id, self::META . 'rendered_html_sha256', $html_sha);
        update_post_meta($id, self::META . 'subject', $subject);
        update_post_meta($id, self::META . 'preheader', $preheader);
        update_post_meta($id, self::META . 'revision', $next);
        update_post_meta($id, self::META . 'sha256', $sha);

        // Bounded metadata receipts; no recipient or sending claims.
        $history = get_post_meta($id, self::META . 'history', true);
        if (!is_array($history)) { $history = array(); }
        $history[] = array('revision'=>$next, 'sha256'=>$sha,
            'rendered_html_sha256'=>$html_sha,
            'actor_id'=>get_current_user_id(), 'saved_utc'=>gmdate('c'));
        update_post_meta($id, self::META . 'history', array_slice($history, -25));
        wp_send_json_success(array('id'=>(int)$id, 'revision'=>$next,
            'sha256'=>$sha, 'rendered_html_sha256'=>$html_sha,
            'issues'=>self::list_issues(),
            'sending_enabled'=>false, 'substack_published'=>false));
    }

    public static function load() {
        self::authorize();
        $id = isset($_POST['id']) ? absint($_POST['id']) : 0;
        $p = self::issue($id);
        if (!$p) { wp_send_json_error(array('message'=>'Newsletter not found'), 404); }
        $json = get_post_meta($id, self::META . 'project', true);
        $project = self::validate_project($json);
        if ($project === false) {
            wp_send_json_error(array('message'=>'Stored project is invalid'), 500);
        }
        wp_send_json_success(array(
            'id'=>$id, 'title'=>$p->post_title,
            'subject'=>(string)get_post_meta($id, self::META . 'subject', true),
            'preheader'=>(string)get_post_meta($id, self::META . 'preheader', true),
            'revision'=>(int)get_post_meta($id, self::META . 'revision', true),
            'sha256'=>(string)get_post_meta($id, self::META . 'sha256', true),
            'rendered_html_sha256'=>(string)get_post_meta($id, self::META . 'rendered_html_sha256', true),
            'staging_receipt'=>self::current_staging_receipt($id),
            'project'=>$project,
            'sending_enabled'=>false,
        ));
    }


    /** Private local acknowledgement, not an assertion of live provider health. */
    private static function current_staging_receipt($id) {
        $receipt = get_post_meta($id, self::META . 'staging_receipt', true);
        if (!is_array($receipt) ||
            ($receipt['revision'] ?? 0) !== (int)get_post_meta($id, self::META . 'revision', true) ||
            ($receipt['source_sha256'] ?? '') !== (string)get_post_meta($id, self::META . 'sha256', true)) {
            return null;
        }
        return array(
            'revision' => $receipt['revision'],
            'campaign_id' => (int)($receipt['campaign_id'] ?? 0),
            'synthetic_only' => true,
            'last_synced_utc' => (string)($receipt['synced_utc'] ?? ''),
            'live_provider_status_verified' => false,
        );
    }

    /** Never expose the bridge URL or secret to browser scripts. */
    private static function bridge_ready() {
        return defined('SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED') &&
            SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED === true &&
            defined('SCEC_MEDIA07_STUDIO_BRIDGE_URL') &&
            defined('SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY') &&
            defined('SCEC_MEDIA07_STUDIO_ORGANIZATION_ID') &&
            is_string(SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY) &&
            strlen(SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY) >= 32 &&
            preg_match('/^[a-f0-9-]{36}$/i', (string)SCEC_MEDIA07_STUDIO_ORGANIZATION_ID);
    }

    /**
     * Explicit administrator action: sign and transfer only the current,
     * private, saved Studio revision to the independently gated API canary.
     * No subscribers, list IDs, SMTP, or listmonk credentials live here.
     */
    public static function sync_staging_draft() {
        self::authorize();
        if (!self::bridge_ready()) {
            wp_send_json_error(array('message'=>'Private staging bridge not configured'), 503);
        }
        if (($_POST['synthetic_confirmed'] ?? '') !== '1') {
            wp_send_json_error(array('message'=>'Synthetic-content confirmation required'), 422);
        }
        $id = absint($_POST['id'] ?? 0);
        $rev = absint($_POST['revision'] ?? 0);
        $p = self::issue($id);
        if (!$p) { wp_send_json_error(array('message'=>'Private draft not found'), 404); }

        $stored_rev = (int)get_post_meta($id, self::META . 'revision', true);
        $stored_sha = (string)get_post_meta($id, self::META . 'sha256', true);
        $claimed_sha = sanitize_text_field(wp_unslash((string)($_POST['studio_revision_sha256'] ?? '')));
        $source = self::validate_project(get_post_meta($id, self::META . 'project', true));
        $subject = (string)get_post_meta($id, self::META . 'subject', true);
        if (strpos($p->post_title, '[SYNTHETIC]') !== 0 || strpos($subject, '[SYNTHETIC]') !== 0) {
            wp_send_json_error(array('message'=>'Staging transfer requires a [SYNTHETIC] title and subject'), 422);
        }
        $preheader = (string)get_post_meta($id, self::META . 'preheader', true);
        if ($rev < 1 || $rev !== $stored_rev || $source === false ||
            !preg_match('/^[a-f0-9]{64}$/', $stored_sha) ||
            !hash_equals($stored_sha, $claimed_sha)) {
            wp_send_json_error(array('message'=>'Draft changed. Reload the saved revision before staging.'), 409);
        }
        $canonical = wp_json_encode($source, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        $html = (string)get_post_meta($id, self::META . 'compiled_html', true);
        $html_sha = (string)get_post_meta($id, self::META . 'rendered_html_sha256', true);
        if (!self::validate_compiled_html($html) ||
            !preg_match('/^[a-f0-9]{64}$/', $html_sha) ||
            !hash_equals($html_sha, hash('sha256', $html)) ||
            !hash_equals($stored_sha, hash('sha256', $canonical . "\n" . $subject . "\n" . $preheader . "\n" . $html_sha))) {
            wp_send_json_error(array('message'=>'Saved compiled HTML missing or inconsistent with the private revision; re-save draft'), 409);
        }
        // Ignore any browser-supplied HTML. Only the stored, hashed revision
        // may be signed and transferred to the synthetic staging adapter.
        $altbody = trim(preg_replace('/\s+/u', ' ', wp_strip_all_tags($html)));
        if (strlen($altbody) < 1 || strlen($altbody) > 15000) {
            wp_send_json_error(array('message'=>'Plain-text newsletter must be 1-15000 bytes'), 422);
        }

        $url = (string)SCEC_MEDIA07_STUDIO_BRIDGE_URL;
        $parts = wp_parse_url($url);
        if (!is_array($parts) || ($parts['scheme'] ?? '') !== 'https' ||
            empty($parts['host']) ||
            ($parts['path'] ?? '') !== '/v1/newsletter-studio/bridge/drafts' ||
            isset($parts['user']) || isset($parts['pass']) ||
            isset($parts['query']) || isset($parts['fragment']) ||
            (isset($parts['port']) && $parts['port'] !== 443)) {
            wp_send_json_error(array('message'=>'Approved HTTPS staging bridge URL is invalid'), 503);
        }

        $payload = array(
            'schema_version' => 'scec.media07.listmonk-draft/1',
            'organization_id' => (string)SCEC_MEDIA07_STUDIO_ORGANIZATION_ID,
            'newsletter_ref' => 'wp-newsletter:' . $id,
            'studio_revision_sha256' => $stored_sha,
            'rendered_html_sha256' => $html_sha,
            'title' => $p->post_title,
            'subject' => $subject,
            'preheader' => $preheader,
            'body_html' => $html,
            'altbody' => $altbody,
            'synthetic_only' => true,
        );
        $body = wp_json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if (!is_string($body)) {
            wp_send_json_error(array('message'=>'Could not encode private staging payload'), 422);
        }
        $stamp = (string)time();
        $signature = hash_hmac('sha256', $stamp . "\n" . $body, SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY);
        $headers = array(
            'Content-Type' => 'application/json',
            'Accept' => 'application/json',
            'X-SCEC-MEDIA07-Timestamp' => $stamp,
            'X-SCEC-MEDIA07-Signature' => $signature,
        );
        // Optional defense-in-depth transport: Cloudflare Access service
        // credentials remain in wp-config, never localized to JS or receipts.
        // Either supply BOTH constants or neither. An approved private mTLS/
        // allowlisted TLS ingress is also possible; never plain HTTP.
        $has_access_id = defined('SCEC_MEDIA07_ACCESS_CLIENT_ID') &&
            is_string(SCEC_MEDIA07_ACCESS_CLIENT_ID) && SCEC_MEDIA07_ACCESS_CLIENT_ID !== '';
        $has_access_secret = defined('SCEC_MEDIA07_ACCESS_CLIENT_SECRET') &&
            is_string(SCEC_MEDIA07_ACCESS_CLIENT_SECRET) && SCEC_MEDIA07_ACCESS_CLIENT_SECRET !== '';
        if ($has_access_id !== $has_access_secret) {
            wp_send_json_error(array('message'=>'Private ingress credentials incomplete'), 503);
        }
        if ($has_access_id) {
            if (preg_match('/[\r\n]/', SCEC_MEDIA07_ACCESS_CLIENT_ID . SCEC_MEDIA07_ACCESS_CLIENT_SECRET) ||
                strlen(SCEC_MEDIA07_ACCESS_CLIENT_ID) > 256 ||
                strlen(SCEC_MEDIA07_ACCESS_CLIENT_SECRET) < 32 ||
                strlen(SCEC_MEDIA07_ACCESS_CLIENT_SECRET) > 512) {
                wp_send_json_error(array('message'=>'Private ingress credentials invalid'), 503);
            }
            $headers['CF-Access-Client-Id'] = SCEC_MEDIA07_ACCESS_CLIENT_ID;
            $headers['CF-Access-Client-Secret'] = SCEC_MEDIA07_ACCESS_CLIENT_SECRET;
        }
        $response = wp_safe_remote_post($url, array(
            'timeout' => 8, 'redirection' => 0, 'sslverify' => true,
            'headers' => $headers,
            'body' => $body,
        ));
        if (is_wp_error($response) || (int)wp_remote_retrieve_response_code($response) !== 201) {
            // Never echo host, proxy, response body or secrets to the editor.
            wp_send_json_error(array('message'=>'Isolated staging draft sync unavailable or rejected'), 502);
        }
        $receipt = json_decode(wp_remote_retrieve_body($response), true);
        if (!is_array($receipt) ||
            ($receipt['campaign_status'] ?? '') !== 'draft' ||
            ($receipt['synthetic_only'] ?? false) !== true ||
            ($receipt['sent'] ?? true) !== false ||
            ($receipt['organization_id'] ?? '') !== (string)SCEC_MEDIA07_STUDIO_ORGANIZATION_ID ||
            !isset($receipt['campaign_id']) || !is_int($receipt['campaign_id']) || $receipt['campaign_id'] <= 0) {
            wp_send_json_error(array('message'=>'Provider did not confirm an unsent staging draft'), 502);
        }
        // A change during network transfer cannot be claimed as current.
        if ((int)get_post_meta($id, self::META . 'revision', true) !== $rev ||
            (string)get_post_meta($id, self::META . 'sha256', true) !== $stored_sha) {
            wp_send_json_error(array('message'=>'Revision changed during staging sync; reconcile existing draft'), 409);
        }
        update_post_meta($id, self::META . 'staging_receipt', array(
            'revision' => $rev, 'source_sha256' => $stored_sha,
            'campaign_id' => $receipt['campaign_id'],
            'fingerprint' => sanitize_text_field((string)($receipt['fingerprint'] ?? '')),
            'synced_utc' => gmdate('c'), 'synthetic_only' => true,
        ));
        wp_send_json_success(array(
            'campaign_id' => $receipt['campaign_id'],
            'campaign_status' => 'draft', 'synthetic_only' => true, 'sent' => false,
            'draft_reused' => ($receipt['draft_reused'] ?? false) === true,
            'revision' => $rev,
        ));
    }

    public static function screen() {
        if (!current_user_can('manage_options')) { wp_die('Forbidden', '', 403); }
        ?>
        <div class="wrap scec07-wrap">
          <div class="scec07-heading">
            <div><span class="scec07-kicker">SUSTAINABLE CATALYST / MEDIA-07</span>
              <h1>Newsletter Studio<span class="scec07-red">.</span></h1>
              <p>Design once. Export a Substack edition. Keep your editable master independent of delivery.</p></div>
            <div class="scec07-state">PRIVATE DRAFTS <span>•</span> SENDING DISABLED</div>
          </div>
          <div class="scec07-app">
            <aside class="scec07-sidebar">
              <label for="scec07-issues">Saved newsletters</label>
              <select id="scec07-issues"><option value="0">New newsletter</option></select>
              <label for="scec07-template">Starting template</label>
              <select id="scec07-template">
                <option value="research">Research bulletin</option>
                <option value="policy">Policy digest</option>
                <option value="institutional">Institutional update</option>
              </select>
              <button type="button" class="button" id="scec07-new">Create new draft</button>
              <hr>
              <label for="scec07-title">Internal title</label>
              <input id="scec07-title" type="text" maxlength="140" placeholder="Research bulletin · November" />
              <label for="scec07-subject">Email subject</label>
              <input id="scec07-subject" type="text" maxlength="200" placeholder="Research, policy &amp; insight" />
              <label for="scec07-preheader">Preheader</label>
              <textarea id="scec07-preheader" rows="2" maxlength="180" placeholder="A short preview of the issue"></textarea>
              <hr>
              <button type="button" class="button button-primary" id="scec07-save">Save private revision</button>
              <button type="button" class="button" id="scec07-media">Insert WordPress image</button>
              <a class="button" href="<?php echo esc_url(admin_url('options-general.php?page=scec-media08')); ?>">Open Press Room drafts</a>
              <div class="scec07-revision" id="scec07-revision" aria-live="polite">Unsaved draft</div>
              <label><input type="checkbox" id="scec07-synthetic-confirm" /> I confirm this saved issue contains synthetic test content only.</label>
              <button type="button" class="button" id="scec07-listmonk" <?php disabled(!self::bridge_ready()); ?>>Create private listmonk staging draft</button>
              <p class="scec07-note">Saved revisions only · empty synthetic list · no recipients or sending. <?php echo self::bridge_ready() ? 'Bridge configured; independent staging acceptance still required.' : 'Staging bridge is disabled until separately configured.'; ?></p>
              <hr>
              <label>Preview</label>
              <div class="scec07-actions">
                <button type="button" class="button" id="scec07-desktop">Desktop</button>
                <button type="button" class="button" id="scec07-mobile">Mobile</button>
                <button type="button" class="button" id="scec07-preview">Full email</button>
              </div>
              <label>Download &amp; transfer</label>
              <button type="button" class="button" id="scec07-html">Download email HTML</button>
              <button type="button" class="button" id="scec07-mjml">Download editable MJML</button>
              <button type="button" class="button" id="scec07-json">Download project JSON</button>
              <button type="button" class="button" id="scec07-substack">Copy Substack edition</button>
              <p class="scec07-note">Substack does not accept arbitrary custom HTML/CSS. Review the pasted version there before sending. No subscriber data or credentials are shared here.</p>
            </aside>
            <section class="scec07-main" aria-label="Visual newsletter editor">
              <div class="scec07-mainbar"><span>VISUAL EDITOR</span><span>DRAG ELEMENTS • SELECT TO EDIT • SAVE REVISIONS</span></div>
              <div id="scec07-editor" aria-label="Drag and drop newsletter canvas"></div>
              <p class="scec07-feedback" id="scec07-feedback" role="status" aria-live="polite">Loading visual editor…</p>
            </section>
          </div>
        </div>
        <?php
    }
}
