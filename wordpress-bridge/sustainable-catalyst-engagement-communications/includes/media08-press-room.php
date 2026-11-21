<?php
/**
 * MEDIA-08 / MEDIA-08.1: dedicated institutional Press Room, private editorial
 * objects, and an approved-only public projection with permanent release URLs.
 * No email/outreach/remote publishing.
 *
 * Publication is disabled unless separately enabled in wp-config and the
 * immutable submitted revision is approved either by a reviewer other than the
 * author (independent review) or, when SCEC_MEDIA08_SINGLE_OPERATOR_OWNER names
 * an administrator, by that institutional owner with an explicit, recorded
 * self-review declaration (single-operator mode, disclosed publicly as such).
 * Released records are revised in place through a working revision: the published
 * text stays live until the update is approved and published, which replaces it in
 * one transaction while keeping the permanent URL, reference and publication date.
 * Every saved text is kept as an append-only snapshot (compare, preview, restore);
 * factual corrections carry a public notice on the same release. Withdrawals keep a
 * public notice at the same URL, and every state change is appended to the history.
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Media08_Press_Room {
    const TYPE = 'scec_press_release';
    const META = '_scec_media08_';
    const PAGE = 'scec-media08';
    const REWRITE_VERSION = '8.9.7-1';
    const REWRITE_OPTION = 'scec_media08_rewrite_version';
    const ROLE = 'scec_press_reviewer';
    // Least-privilege capabilities. Administrators hold all three; the Press
    // reviewer role holds only `read` and CAP_REVIEW.
    const CAP_AUTHOR = 'scec_press_author';
    const CAP_REVIEW = 'scec_press_review';
    const CAP_PUBLISH = 'scec_press_publish';
    const KINDS = array(
        'press-release' => 'Press release',
        'announcement' => 'Institutional announcement',
        'statement' => 'Official statement',
        'research-release' => 'Research release',
        'institutional-update' => 'Institutional update',
        'methodology-note' => 'Methodology note',
        'data-release' => 'Data release',
        'event-notice' => 'Event notice',
    );
    const MODE_INDEPENDENT = 'independent';
    const MODE_OWNER_SELF = 'owner_self';
    const CHANGE_TYPES = array(
        'editorial' => 'Editorial update: wording, layout, formatting, images or clarity; no change to facts (public note optional)',
        'correction' => 'Factual correction: a statement of fact changes (public correction notice required)',
    );
    const SELF_REVIEW_LABEL = 'Approved by the institutional publisher (single-operator self-review; not independent review)';
    const ATTESTATIONS = array(
        'rights' => 'Rights and attribution',
        'source' => 'Source integrity',
        'privacy' => 'Privacy/public suitability',
        'institutional' => 'Institutional authority',
    );

    /** The release currently being rendered at its permanent URL, if any. */
    private static $current = null;

    public static function boot() {
        add_action('init', array(__CLASS__, 'register_type'));
        add_action('init', array(__CLASS__, 'register_routes'));
        add_action('init', array(__CLASS__, 'ensure_roles'));
        add_filter('query_vars', array(__CLASS__, 'query_vars'));
        add_action('wp', array(__CLASS__, 'resolve_request'), 1);
        add_action('template_redirect', array(__CLASS__, 'preview'), 0);
        add_action('template_redirect', array(__CLASS__, 'template_redirect'), 1);
        add_action('admin_menu', array(__CLASS__, 'menu'));
        foreach (array('save','submit','approve','return','release','withdraw','correct',
                       'reopen','save_update','discard_update','publish_update','restore') as $action) {
            add_action('admin_post_scec08_' . $action, array(__CLASS__, $action === 'return' ? 'return_to_author' : $action));
        }
        add_shortcode('sc_press_room', array(__CLASS__, 'render'));
        add_shortcode('sc_press_inquiry', array(__CLASS__, 'inquiry_link'));
        add_filter('rank_math/sitemap/index', array(__CLASS__, 'sitemap_index'));
    }

    public static function enabled() {
        return defined('SCEC_MEDIA08_PUBLIC_RELEASE') && SCEC_MEDIA08_PUBLIC_RELEASE === true;
    }

    /**
     * Single-operator mode: the user ID in SCEC_MEDIA08_SINGLE_OPERATOR_OWNER, if that
     * user is an administrator; otherwise 0 (mode off, independent review required).
     */
    public static function single_operator_owner() {
        if (!defined('SCEC_MEDIA08_SINGLE_OPERATOR_OWNER') || !is_int(SCEC_MEDIA08_SINGLE_OPERATOR_OWNER) ||
            SCEC_MEDIA08_SINGLE_OPERATOR_OWNER <= 0) {
            return 0;
        }
        $owner = SCEC_MEDIA08_SINGLE_OPERATOR_OWNER;
        return user_can($owner, 'manage_options') ? $owner : 0;
    }

    /**
     * Whether an approval satisfies the review rule. Independent: a reviewer other than
     * the submitter. Owner self-review: recorded as such and made by $owner_id (the
     * authorised single-operator owner, or 0 when none).
     */
    public static function approval_ok($author_id, $reviewer_id, $mode, $owner_id) {
        $author_id = (int)$author_id; $reviewer_id = (int)$reviewer_id; $owner_id = (int)$owner_id;
        if (!$author_id || !$reviewer_id) { return false; }
        if ($mode === self::MODE_OWNER_SELF) { return $owner_id > 0 && $reviewer_id === $owner_id; }
        return $author_id !== $reviewer_id;
    }

    /** The published, non-password /press/ page carrying [sc_press_room]. */
    public static function press_page() {
        $page = get_page_by_path('press', OBJECT, 'page');
        if (!$page || $page->post_status !== 'publish' || post_password_required($page) ||
            !has_shortcode($page->post_content, 'sc_press_room')) {
            return null;
        }
        return $page;
    }

    /** Public launch requires both the wp-config flag and the dedicated page. */
    public static function launch_ready() {
        return self::enabled() && (bool)self::press_page();
    }

    public static function register_type() {
        register_post_type(self::TYPE, array(
            'label' => 'Private press releases',
            'public' => false, 'publicly_queryable' => false,
            'exclude_from_search' => true, 'has_archive' => false,
            'rewrite' => false, 'show_in_rest' => false, 'show_ui' => false,
            'supports' => array('title', 'author'),
            'capability_type' => 'post', 'map_meta_cap' => false,
            'capabilities' => array_fill_keys(array(
                'edit_post','read_post','delete_post','edit_posts','edit_others_posts',
                'publish_posts','read_private_posts','delete_posts','delete_private_posts',
                'delete_published_posts','delete_others_posts','edit_private_posts',
                'edit_published_posts','create_posts'), 'manage_options'),
        ));
    }

    /** Role and capability definitions only; never creates or changes users. */
    public static function ensure_roles() {
        if (get_option(self::REWRITE_OPTION . '_roles') === self::REWRITE_VERSION) { return; }
        $admin = get_role('administrator');
        if ($admin) {
            foreach (array(self::CAP_AUTHOR, self::CAP_REVIEW, self::CAP_PUBLISH) as $cap) { $admin->add_cap($cap); }
        }
        remove_role(self::ROLE);
        add_role(self::ROLE, 'Press reviewer', array('read' => true, self::CAP_REVIEW => true));
        update_option(self::REWRITE_OPTION . '_roles', self::REWRITE_VERSION, false);
    }

    private static function can($cap) {
        return current_user_can($cap) || current_user_can('manage_options');
    }

    // ---------------------------------------------------------------- routes

    public static function register_routes() {
        add_rewrite_rule('^press/([0-9]{4})/([a-z0-9-]{1,90})/?$',
            'index.php?scec_press_year=$matches[1]&scec_press_slug=$matches[2]', 'top');
        // /press/sitemap.xml: hosts commonly serve missing *.xml as static 404s unless the name
        // contains "sitemap", and Rank Math's root-level `([^/]+?)-sitemap.xml` rule cannot match a
        // path with a slash, so this reaches WordPress and is not captured by Rank Math.
        add_rewrite_rule('^press/sitemap\.xml$', 'index.php?scec_press_sitemap=1', 'top');
        // Flush once per version, only on a web request: under WP-CLI other plugins
        // (e.g. Rank Math's sitemap) do not register their rules, so a CLI flush drops them.
        if (get_option(self::REWRITE_OPTION) !== self::REWRITE_VERSION && !(defined('WP_CLI') && WP_CLI)) {
            flush_rewrite_rules(false);
            // Rank Math caches the sitemap index as files, which outlive plugin upgrades.
            self::invalidate_sitemaps();
            update_option(self::REWRITE_OPTION, self::REWRITE_VERSION, false);
        }
    }

    public static function query_vars($vars) {
        return array_merge($vars, array('scec_press_year', 'scec_press_slug', 'scec_press_sitemap'));
    }

    public static function permalink($id) {
        $path = (string)self::meta($id, 'permalink_path');
        return $path ? home_url('/press/' . $path . '/') : '';
    }

    private static function find_by_path($path) {
        $posts = get_posts(array('post_type'=>self::TYPE,'post_status'=>'private','numberposts'=>1,
            'meta_query'=>array(array('key'=>self::META.'permalink_path','value'=>$path))));
        return $posts ? $posts[0] : null;
    }

    public static function resolve_request() {
        global $wp_query;
        if (get_query_var('scec_press_sitemap')) {
            $wp_query->is_home = false;
            return;
        }
        $year = (string)get_query_var('scec_press_year');
        $slug = (string)get_query_var('scec_press_slug');
        if ($year === '' || $slug === '') { return; }
        $p = self::launch_ready() ? self::find_by_path($year . '/' . $slug) : null;
        if (!$p || self::public_state($p) === '') {
            $wp_query->set_404();
            status_header(404);
            nocache_headers();
            return;
        }
        self::$current = $p;
        $wp_query->is_home = false;
        $wp_query->is_404 = false;
        status_header(200);
        self::seo_hooks();
    }

    /** Signed-in preview of any saved text, rendered with the site theme and Press styles. */
    public static function preview_url($id, $which) {
        return add_query_arg(array('scec_press_preview' => (int)$id, 'rev' => $which,
            '_wpnonce' => wp_create_nonce('scec08_preview_' . (int)$id)), home_url('/'));
    }

    public static function preview() {
        if (!isset($_GET['scec_press_preview'])) { return; }
        $id = absint($_GET['scec_press_preview']);
        if (!is_user_logged_in() || !self::can(self::CAP_REVIEW) ||
            !wp_verify_nonce((string)($_GET['_wpnonce'] ?? ''), 'scec08_preview_' . $id)) {
            wp_die('Preview not available', '', 403);
        }
        $p = self::post($id);
        if (!$p) { wp_die('Not found', '', 404); }
        $which = sanitize_key((string)($_GET['rev'] ?? 'current'));
        $c = self::content_of($p);
        $label = self::meta($id,'state') === 'released' ? 'published text' : 'saved draft';
        if ($which === 'working' && ($u = self::pending($id))) {
            $c = $u['content']; $label = 'working revision r' . (int)$u['snapshot'] . ' (not published)';
        } elseif (ctype_digit($which) && ($s = self::snapshot_content($id, (int)$which))) {
            $c = $s; $label = 'revision r' . (int)$which;
        }
        if (!defined('DONOTCACHEPAGE')) { define('DONOTCACHEPAGE', true); }
        nocache_headers();
        header('X-Robots-Tag: noindex, nofollow');
        add_filter('wp_robots', 'wp_robots_no_robots');
        $title = 'Preview: ' . $c['title'];
        add_filter('pre_get_document_title', function () use ($title) { return $title; }, 99);
        add_filter('rank_math/frontend/title', function () use ($title) { return $title; }, 99);
        add_filter('rank_math/frontend/robots', function () { return array('index' => 'noindex', 'follow' => 'nofollow'); }, 99);
        status_header(200);
        get_header();
        echo '<main id="primary" class="site-main scec-press-release-page">' .
            '<p class="scec-press-notice scec-press-preview-banner" role="note" style="border:2px dashed #a00000;padding:12px 16px;max-width:860px;margin:16px auto">' .
            '<strong>Preview: ' . esc_html($label) . '.</strong> Not public. This is how it appears in the Press Room.</p>' .
            self::article($p, $c, 'preview') . '</main>';
        get_footer();
        exit;
    }

    public static function template_redirect() {
        if (get_query_var('scec_press_sitemap')) {
            self::sitemap();
            exit;
        }
        if (!self::$current) { return; }
        get_header();
        echo '<main id="primary" class="site-main scec-press-release-page">' . self::single(self::$current) . '</main>';
        get_footer();
        exit;
    }

    // ---------------------------------------------------- public eligibility

    /**
     * 'released', 'withdrawn' or '' (not public). A record is public only if it
     * passed the original gate: approved and released hashes equal the current
     * content hash, the approval satisfies the review rule (independent, or a recorded
     * owner self-review by a user who is still an administrator), and any embargo has passed.
     */
    public static function public_state($p) {
        if (!self::launch_ready()) { return ''; }
        $state = (string)self::meta($p->ID, 'state');
        if (!in_array($state, array('released', 'withdrawn'), true)) { return ''; }
        $sha = self::current_sha($p);
        if (!hash_equals((string)self::meta($p->ID,'released_sha'), $sha) ||
            !hash_equals((string)self::meta($p->ID,'approved_sha'), $sha) ||
            !self::approval_ok(self::meta($p->ID,'submitted_by'), self::meta($p->ID,'reviewer_id'),
                (string)self::meta($p->ID,'approval_mode'), self::self_review_owner_at_render($p))) {
            return '';
        }
        if (!self::embargo_passed((string)self::meta($p->ID,'embargo_until'), time())) { return ''; }
        return $state;
    }

    /** Owner self-review stays valid after release while the approver remains an administrator. */
    private static function self_review_owner_at_render($p) {
        $reviewer = (int)self::meta($p->ID,'reviewer_id');
        return $reviewer && user_can($reviewer, 'manage_options') ? $reviewer : 0;
    }

    private static function embargo_passed($embargo, $now_utc) {
        if (!$embargo) { return true; }
        $date = DateTimeImmutable::createFromFormat('!Y-m-d\\TH:i', (string)$embargo, new DateTimeZone('UTC'));
        return $date && $date->format('Y-m-d\\TH:i') === (string)$embargo && $date->getTimestamp() <= (int)$now_utc;
    }

    // --------------------------------------------------------- record model

    private static function post($id) {
        $p = $id > 0 ? get_post($id) : null;
        return $p && $p->post_type === self::TYPE && $p->post_status === 'private' ? $p : null;
    }

    private static function meta($id, $name, $default = '') {
        $value = get_post_meta($id, self::META . $name, true);
        return $value === '' ? $default : $value;
    }

    public static function digest($title, $summary, $body, $kind, $source_url, $embargo) {
        return hash('sha256', wp_json_encode(array(
            'title'=>$title,'summary'=>$summary,'body'=>$body,
            'kind'=>$kind,'source_url'=>$source_url,'embargo'=>$embargo
        ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
    }

    public static function publication_gate($enabled, $state, $current_sha, $approved_sha, $author_id, $reviewer_id, $embargo, $now_utc,
                                            $mode = self::MODE_INDEPENDENT, $owner_id = 0) {
        if (!$enabled || $state !== 'approved' || !$approved_sha ||
            !hash_equals((string)$approved_sha, (string)$current_sha) ||
            !self::approval_ok($author_id, $reviewer_id, $mode, $owner_id)) {
            return false;
        }
        if (!$embargo) { return true; }
        $date = DateTimeImmutable::createFromFormat('!Y-m-d\\TH:i', (string)$embargo, new DateTimeZone('UTC'));
        return $date && $date->format('Y-m-d\\TH:i') === (string)$embargo &&
            $date->getTimestamp() <= (int)$now_utc;
    }

    /** Permanent path: YYYY/slug from the release year and headline; unique, never reassigned. */
    public static function path_for($year, $title, $taken) {
        $slug = trim(preg_replace('/[^a-z0-9]+/', '-', strtolower(remove_accents((string)$title))), '-');
        if (strlen($slug) > 80) {
            // Cut at a word boundary so permanent URLs never end mid-word.
            $cut = substr($slug, 0, 81);
            $slug = strrpos($cut, '-') !== false ? substr($cut, 0, strrpos($cut, '-')) : substr($slug, 0, 80);
        }
        $slug = trim($slug, '-') ?: 'release';
        $path = $year . '/' . $slug;
        for ($n = 2; in_array($path, $taken, true); $n++) { $path = $year . '/' . $slug . '-' . $n; }
        return $path;
    }

    /** Release reference SC-PR-YYYY-NNN, sequential per year among released records. */
    public static function reference_for($year, $taken) {
        $max = 0;
        foreach ($taken as $ref) {
            if (preg_match('/^SC-PR-' . preg_quote((string)$year, '/') . '-(\d{3,})$/', (string)$ref, $m)) { $max = max($max, (int)$m[1]); }
        }
        return sprintf('SC-PR-%s-%03d', $year, $max + 1);
    }

    private static function current_sha($p) {
        return self::digest($p->post_title,
            (string)self::meta($p->ID, 'summary'),
            (string)self::meta($p->ID, 'body'),
            (string)self::meta($p->ID, 'kind'),
            (string)self::meta($p->ID, 'source_url'),
            (string)self::meta($p->ID, 'embargo_until'));
    }

    /** Append-only history: one meta row per event, never updated in place. */
    private static function event($id, $action, $note = '') {
        $p = get_post($id);
        // wp_slash: add_post_meta unslashes, which would corrupt JSON escapes in notes.
        add_post_meta($id, self::META . 'event', wp_slash(wp_json_encode(array(
            'at' => gmdate('c'), 'action' => $action, 'user' => get_current_user_id(),
            'state' => (string)self::meta($id, 'state'),
            'sha256' => $p ? self::current_sha($p) : '',
            'note' => (string)$note,
        ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)));
    }

    /** The record's current (for a release: published) text. */
    private static function content_of($p) {
        return array('title' => $p->post_title, 'summary' => (string)self::meta($p->ID,'summary'),
            'body' => (string)self::meta($p->ID,'body'), 'kind' => (string)self::meta($p->ID,'kind'),
            'source_url' => (string)self::meta($p->ID,'source_url'), 'embargo' => (string)self::meta($p->ID,'embargo_until'));
    }

    public static function sha_of($c) {
        return self::digest($c['title'], $c['summary'], $c['body'], $c['kind'], $c['source_url'], $c['embargo']);
    }

    /** Append-only text snapshots: every saved draft, working revision, restore and baseline. */
    private static function add_snapshot($id, $c, $origin, $note = '') {
        $n = count(get_post_meta($id, self::META . 'snapshot', false)) + 1;
        $c = array_intersect_key($c, array_flip(array('title','summary','body','kind','source_url','embargo')));
        add_post_meta($id, self::META . 'snapshot', wp_slash(wp_json_encode(array(
            'n' => $n, 'at' => gmdate('c'), 'user' => get_current_user_id(), 'origin' => $origin,
            'note' => (string)$note, 'sha256' => self::sha_of($c)) + $c, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)));
        return $n;
    }

    public static function snapshots($id) {
        $rows = array();
        foreach (get_post_meta($id, self::META . 'snapshot', false) as $raw) {
            $r = json_decode((string)$raw, true);
            if (is_array($r)) { $rows[(int)$r['n']] = $r; }
        }
        ksort($rows);
        return $rows;
    }

    private static function snapshot_content($id, $n) {
        $rows = self::snapshots($id);
        if (!isset($rows[$n])) { return null; }
        return array_intersect_key($rows[$n], array_flip(array('title','summary','body','kind','source_url','embargo')));
    }

    /** Before the first in-place change, keep the published text as a snapshot. */
    private static function ensure_baseline($id) {
        $live = self::content_of(get_post($id));
        $sha = self::sha_of($live);
        foreach (self::snapshots($id) as $r) { if ($r['sha256'] === $sha) { return; } }
        self::add_snapshot($id, $live, 'baseline', 'published text recorded before revision');
    }

    /** The working revision of a released record (not public), or null. */
    public static function pending($id) {
        $u = json_decode((string)get_post_meta($id, self::META . 'update', true), true);
        return is_array($u) && isset($u['content'], $u['sha256']) ? $u : null;
    }

    public static function history($id) {
        $events = array();
        foreach (get_post_meta($id, self::META . 'event', false) as $raw) {
            $e = json_decode((string)$raw, true);
            if (is_array($e)) { $events[] = $e; }
        }
        usort($events, function ($a, $b) { return strcmp((string)$a['at'], (string)$b['at']); });
        return $events;
    }

    private static function all_meta_values($name) {
        $values = array();
        foreach (get_posts(array('post_type'=>self::TYPE,'post_status'=>'private','numberposts'=>-1,'fields'=>'ids')) as $id) {
            $v = (string)self::meta($id, $name);
            if ($v !== '') { $values[] = $v; }
        }
        return $values;
    }

    // ------------------------------------------------------------- actions

    private static function admin_check($action, $id, $cap) {
        if (!self::can($cap)) { wp_die('Not authorized', '', 403); }
        if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') { wp_die('POST only', '', 405); }
        check_admin_referer($action . '_' . $id);
    }

    private static function back($notice, $id = 0) {
        wp_safe_redirect(add_query_arg(array('page'=>self::PAGE,'notice'=>$notice,'id'=>$id),
            admin_url('admin.php')));
        exit;
    }

    private static function post_url($id) {
        $args = array('page'=>self::PAGE);
        if ($id) { $args['id'] = $id; }
        return add_query_arg($args, admin_url('admin.php'));
    }

    private static function purge_cache() {
        // Endurance/nginx page cache on the production host; harmless elsewhere.
        do_action('epc_purge');
        self::invalidate_sitemaps();
    }

    private static function invalidate_sitemaps() {
        // Rank Math caches sitemaps as files. Clear all of them directly: typed invalidation only removes
        // files listed in its cache-file index, and its watcher does not run under WP-CLI. Releases are rare.
        if (class_exists('\\RankMath\\Sitemap\\Cache')) { \RankMath\Sitemap\Cache::invalidate_storage(); }
    }

    public static function save() {
        $id = absint($_POST['id'] ?? 0);
        self::admin_check('scec08_save', $id, self::CAP_AUTHOR);
        $p = self::post($id);
        if ($id && !$p) { self::back('not_found'); }
        if ($p && self::meta($id,'state','draft') !== 'draft') {
            self::back('locked', $id);
        }
        $c = self::read_form($id);
        $created = !$p;
        if (!$p) {
            $id = wp_insert_post(array('post_type'=>self::TYPE,'post_status'=>'private',
                'post_title'=>$c['title'],'post_author'=>get_current_user_id()),true);
            if (is_wp_error($id) || !$id) { self::back('save_failed'); }
        }
        if (!self::write_draft($id, $c)) { self::back('save_failed',$id); }
        self::event($id, $created ? 'created' : 'saved', 'revision ' . (int)self::meta($id,'revision'));
        self::back('saved',$id);
    }

    /** Validated editor fields; the same rules for drafts and working revisions. */
    private static function read_form($id) {
        $c = array(
            'title' => sanitize_text_field(wp_unslash((string)($_POST['title'] ?? ''))),
            'summary' => sanitize_textarea_field(wp_unslash((string)($_POST['summary'] ?? ''))),
            'body' => wp_kses_post(wp_unslash((string)($_POST['body'] ?? ''))),
            'kind' => sanitize_key((string)($_POST['kind'] ?? '')),
            'source_url' => esc_url_raw(wp_unslash((string)($_POST['source_url'] ?? ''))),
            'embargo' => sanitize_text_field(wp_unslash((string)($_POST['embargo_until'] ?? ''))),
        );
        if ($c['title'] === '' || $c['summary'] === '' || trim(wp_strip_all_tags($c['body'])) === '' ||
            !isset(self::KINDS[$c['kind']]) || strlen($c['title'])>180 || strlen($c['summary'])>900 ||
            strlen($c['body'])>75000 || strlen($c['source_url'])>600 ||
            ($c['source_url'] && (strpos($c['source_url'], 'https://') !== 0 || !wp_http_validate_url($c['source_url']))) ||
            ($c['embargo'] && !preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/D', $c['embargo']))) {
            self::back('invalid',$id);
        }
        // Store the title exactly as WordPress will save it, so fingerprints match after publishing.
        $c['title'] = wp_unslash(sanitize_post_field('post_title', wp_slash($c['title']), $id, 'db'));
        return $c;
    }

    /** Write an unreleased draft's text as a new revision and snapshot. */
    private static function write_draft($id, $c, $origin = 'draft', $note = '') {
        $result = wp_update_post(array('ID'=>$id,'post_title'=>$c['title']),true);
        if (is_wp_error($result)) { return false; }
        update_post_meta($id,self::META.'summary',$c['summary']);
        update_post_meta($id,self::META.'body',wp_slash($c['body']));
        update_post_meta($id,self::META.'kind',$c['kind']);
        update_post_meta($id,self::META.'source_url',$c['source_url']);
        update_post_meta($id,self::META.'embargo_until',$c['embargo']);
        update_post_meta($id,self::META.'state','draft');
        update_post_meta($id,self::META.'draft_sha',self::current_sha(get_post($id)));
        update_post_meta($id,self::META.'revision',1+(int)self::meta($id,'revision',0));
        self::add_snapshot($id, self::content_of(get_post($id)), $origin,
            trim('revision ' . (int)self::meta($id,'revision') . ' ' . $note));
        return true;
    }

    public static function submit() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_submit',$id,self::CAP_AUTHOR);
        $p=self::post($id);
        if (!$p || self::meta($id,'state','draft')!=='draft') { self::back('invalid_state',$id); }
        if (!self::meta($id,'summary') || !self::meta($id,'body')) { self::back('invalid',$id); }
        $sha=self::current_sha($p);
        update_post_meta($id,self::META.'submitted_sha',$sha);
        update_post_meta($id,self::META.'state','in_review');
        update_post_meta($id,self::META.'submitted_by',get_current_user_id());
        update_post_meta($id,self::META.'submitted_at',gmdate('c'));
        self::event($id, 'submitted');
        self::back('submitted',$id);
    }

    public static function approve() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_approve',$id,self::CAP_REVIEW);
        $p=self::post($id);
        if (!$p || self::meta($id,'state')!=='in_review') { self::back('invalid_state',$id); }
        $author=(int)self::meta($id,'submitted_by',0);
        $me=get_current_user_id();
        $mode = self::MODE_INDEPENDENT;
        if (!$author || $author===$me || (int)$p->post_author===$me) {
            // Own release: only the configured single-operator owner, with an explicit declaration.
            if (!$author || $me !== self::single_operator_owner()) { self::back('independent_review_required',$id); }
            if (($_POST['owner_self_approval'] ?? '') !== '1') { self::back('self_review_declaration_required',$id); }
            $mode = self::MODE_OWNER_SELF;
        }
        if (!hash_equals((string)self::meta($id,'submitted_sha'),self::current_sha($p))) {
            self::back('source_changed',$id);
        }
        foreach (array_keys(self::ATTESTATIONS) as $check) {
            if (($_POST['check_'.$check] ?? '') !== '1') { self::back('review_incomplete',$id); }
        }
        $sha = self::current_sha($p);
        update_post_meta($id,self::META.'approved_sha',$sha);
        update_post_meta($id,self::META.'reviewer_id',$me);
        update_post_meta($id,self::META.'approved_at',gmdate('c'));
        update_post_meta($id,self::META.'approval_mode',$mode);
        update_post_meta($id,self::META.'attestations',implode(',', array_keys(self::ATTESTATIONS)));
        update_post_meta($id,self::META.'state','approved');
        if ($mode === self::MODE_OWNER_SELF) {
            self::event($id, 'owner_self_approved', 'decision: approved; single-operator owner self-review, not independent review; sha256 ' .
                $sha . '; attested: ' . implode(', ', array_keys(self::ATTESTATIONS)));
        } else {
            self::event($id, 'approved', 'attested: ' . implode(', ', array_keys(self::ATTESTATIONS)));
        }
        self::back('approved',$id);
    }

    /** Reviewer sends a submission back; the author may then edit (a new revision). */
    public static function return_to_author() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_return',$id,self::CAP_REVIEW);
        $p=self::post($id);
        if (!$p || self::meta($id,'state')!=='in_review') { self::back('invalid_state',$id); }
        $note = sanitize_textarea_field(wp_unslash((string)($_POST['note'] ?? '')));
        if ($note === '' || strlen($note) > 1000) { self::back('note_required',$id); }
        update_post_meta($id,self::META.'state','draft');
        delete_post_meta($id,self::META.'submitted_sha');
        self::event($id, 'returned', $note);
        self::back('returned',$id);
    }

    /** Explicitly feature gated. No auto-send, social, API or cross-post. */
    public static function release() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_release',$id,self::CAP_PUBLISH);
        $p=self::post($id);
        if (!$p) { self::back('not_found',$id); }
        // Require an actual public Press page with the dedicated shortcode.
        if (!self::press_page()) {
            self::back('press_page_missing',$id);
        }
        $eligible=self::publication_gate(self::enabled(),
            self::meta($id,'state'),self::current_sha($p),
            self::meta($id,'approved_sha'),(int)self::meta($id,'submitted_by',0),
            (int)self::meta($id,'reviewer_id',0),
            self::meta($id,'embargo_until'),time(),
            (string)self::meta($id,'approval_mode'), self::single_operator_owner());
        if (!$eligible) { self::back('release_blocked',$id); }
        $year = gmdate('Y');
        if (!self::meta($id,'permalink_path')) {
            update_post_meta($id,self::META.'permalink_path',self::path_for($year,$p->post_title,self::all_meta_values('permalink_path')));
        }
        if (!self::meta($id,'reference')) {
            update_post_meta($id,self::META.'reference',self::reference_for($year,self::all_meta_values('reference')));
        }
        update_post_meta($id,self::META.'state','released');
        update_post_meta($id,self::META.'released_sha',self::current_sha($p));
        update_post_meta($id,self::META.'released_at',gmdate('c'));
        update_post_meta($id,self::META.'released_by',get_current_user_id());
        self::event($id, 'released', self::permalink($id));
        $original = (int)self::meta($id,'corrects');
        if ($original && self::post($original)) {
            // Notice on the original; its approved content is not touched.
            update_post_meta($original,self::META.'corrected_by',$id);
            update_post_meta($original,self::META.'corrected_at',gmdate('c'));
            self::event($original, 'corrected', 'correction ' . (string)self::meta($id,'reference') . ' ' . self::permalink($id));
        }
        self::purge_cache();
        self::back('released',$id);
    }

    /** Edit an unreleased record that is in review or approved: back to draft, approval cleared. */
    public static function reopen() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_reopen',$id,self::CAP_AUTHOR);
        $p=self::post($id);
        if (!$p || !in_array(self::meta($id,'state'), array('in_review','approved'), true)) { self::back('invalid_state',$id); }
        foreach (array('submitted_sha','approved_sha','reviewer_id','approval_mode','approved_at','attestations') as $k) {
            delete_post_meta($id,self::META.$k);
        }
        update_post_meta($id,self::META.'state','draft');
        self::event($id, 'reopened', 'returned to draft for editing; approval cleared');
        self::back('reopened',$id);
    }

    /** Save a working revision of a released record. The published text stays live. */
    public static function save_update() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_save_update',$id,self::CAP_AUTHOR);
        $p=self::post($id);
        if (!$p || self::meta($id,'state')!=='released') { self::back('invalid_state',$id); }
        $c = self::read_form($id);
        $c['embargo'] = (string)self::meta($id,'embargo_until'); // fixed once released
        // Browsers submit CRLF line breaks and the visual editor drops trailing whitespace;
        // keep the published body byte-for-byte when those are the only differences.
        $live = (string)self::meta($id,'body');
        $norm = function ($b) { return rtrim(str_replace("\r\n", "\n", $b)); };
        if ($norm($c['body']) === $norm($live)) { $c['body'] = $live; }
        if (hash_equals(self::current_sha($p), self::sha_of($c))) { self::back('no_changes',$id); }
        self::stage_update($id, $c, 'update');
        self::back('update_saved',$id);
    }

    private static function stage_update($id, $c, $origin, $note = '') {
        self::ensure_baseline($id);
        $n = self::add_snapshot($id, $c, $origin, $note);
        $sha = self::sha_of($c);
        update_post_meta($id, self::META.'update', wp_slash(wp_json_encode(array(
            'content' => $c, 'sha256' => $sha, 'snapshot' => $n, 'by' => get_current_user_id(), 'at' => gmdate('c'),
        ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)));
        self::event($id, 'update_saved', trim('working revision r' . $n . ' sha256 ' . $sha . ' ' . $note));
    }

    public static function discard_update() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_discard_update',$id,self::CAP_AUTHOR);
        $u = self::post($id) ? self::pending($id) : null;
        if (!$u) { self::back('no_update',$id); }
        delete_post_meta($id, self::META.'update');
        self::event($id, 'update_discarded', 'working revision r' . (int)$u['snapshot'] . ' discarded; published text unchanged');
        self::back('update_discarded',$id);
    }

    /**
     * Approve and publish the working revision in place. Same review rule as a release
     * (independent, or the configured owner's declared self-review), the four attestations,
     * the exact working fingerprint, and a change type. Replaces the published text in one
     * transaction; URL, reference and publication date are kept.
     */
    public static function publish_update() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_publish_update',$id,self::CAP_PUBLISH);
        $p=self::post($id);
        if (!$p || self::meta($id,'state')!=='released') { self::back('invalid_state',$id); }
        $u=self::pending($id);
        if (!$u) { self::back('no_update',$id); }
        if (!hash_equals((string)$u['sha256'], (string)($_POST['update_sha'] ?? '')) ||
            !hash_equals((string)$u['sha256'], self::sha_of($u['content']))) {
            self::back('update_changed',$id);
        }
        $me=get_current_user_id();
        $author=(int)$u['by'];
        $mode=self::MODE_INDEPENDENT;
        if (!$author || $author===$me) {
            if (!$author || $me !== self::single_operator_owner()) { self::back('independent_review_required',$id); }
            if (($_POST['owner_self_approval'] ?? '') !== '1') { self::back('self_review_declaration_required',$id); }
            $mode=self::MODE_OWNER_SELF;
        }
        foreach (array_keys(self::ATTESTATIONS) as $check) {
            if (($_POST['check_'.$check] ?? '') !== '1') { self::back('review_incomplete',$id); }
        }
        $type = sanitize_key((string)($_POST['change_type'] ?? ''));
        if (!isset(self::CHANGE_TYPES[$type])) { self::back('change_type_required',$id); }
        $note = sanitize_textarea_field(wp_unslash((string)($_POST['public_note'] ?? '')));
        if (strlen($note) > 500) { self::back('note_too_long',$id); }
        if ($type === 'correction' && $note === '') { self::back('correction_notice_required',$id); }
        self::ensure_baseline($id);
        $previous = self::current_sha($p);
        $c = $u['content'];
        $now = gmdate('c');
        global $wpdb;
        // One transaction: readers see the previous published text or the new one, never a mix.
        $wpdb->query('START TRANSACTION');
        $result = wp_update_post(array('ID'=>$id,'post_title'=>$c['title']),true);
        if (!is_wp_error($result)) {
            update_post_meta($id,self::META.'summary',$c['summary']);
            update_post_meta($id,self::META.'body',wp_slash($c['body']));
            update_post_meta($id,self::META.'kind',$c['kind']);
            update_post_meta($id,self::META.'source_url',$c['source_url']);
            clean_post_cache($id);
        }
        if (is_wp_error($result) || !hash_equals((string)$u['sha256'], self::current_sha(get_post($id)))) {
            $wpdb->query('ROLLBACK');
            clean_post_cache($id);
            self::back('update_changed',$id);
        }
        foreach (array('approved_sha','released_sha','submitted_sha') as $k) { update_post_meta($id,self::META.$k,$u['sha256']); }
        update_post_meta($id,self::META.'submitted_by',$author);
        update_post_meta($id,self::META.'reviewer_id',$me);
        update_post_meta($id,self::META.'approval_mode',$mode);
        update_post_meta($id,self::META.'approved_at',$now);
        update_post_meta($id,self::META.'attestations',implode(',', array_keys(self::ATTESTATIONS)));
        update_post_meta($id,self::META.'updated_at',$now);
        update_post_meta($id,self::META.'updated_by',$me);
        update_post_meta($id,self::META.'published_snapshot',(int)$u['snapshot']);
        if ($note !== '') {
            add_post_meta($id, self::META.'public_note', wp_slash(wp_json_encode(array('at'=>$now,'type'=>$type,'text'=>$note),
                JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)));
        }
        delete_post_meta($id, self::META.'update');
        self::event($id, $type === 'correction' ? 'correction_published' : 'update_published',
            'published working revision r' . (int)$u['snapshot'] . '; ' . ($mode === self::MODE_OWNER_SELF
                ? 'single-operator owner self-review, not independent review' : 'independent review') .
            '; sha256 ' . $previous . ' -> ' . $u['sha256'] . ($note !== '' ? '; public note: ' . $note : ''));
        $wpdb->query('COMMIT');
        self::purge_cache();
        self::back('update_published',$id);
    }

    /** Restore an earlier snapshot as a new revision; nothing goes public until published. */
    public static function restore() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_restore',$id,self::CAP_AUTHOR);
        $p=self::post($id);
        $n=absint($_POST['snapshot'] ?? 0);
        $c=$p ? self::snapshot_content($id,$n) : null;
        if (!$c) { self::back('not_found',$id); }
        $state=(string)self::meta($id,'state','draft');
        if ($state==='released') {
            $c['embargo'] = (string)self::meta($id,'embargo_until');
            self::stage_update($id, $c, 'restore', 'restored from r' . $n);
            self::back('restored',$id);
        }
        if ($state!=='draft') { self::back('invalid_state',$id); }
        if (!self::write_draft($id, $c, 'restore', 'restored from r' . $n)) { self::back('save_failed',$id); }
        self::event($id, 'saved', 'revision ' . (int)self::meta($id,'revision') . ' restored from r' . $n);
        self::back('restored',$id);
    }

    /** Remove from public view while keeping a dated notice at the same URL. */
    public static function withdraw() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_withdraw',$id,self::CAP_PUBLISH);
        $p=self::post($id);
        if (!$p || self::meta($id,'state')!=='released') { self::back('invalid_state',$id); }
        $reason = sanitize_textarea_field(wp_unslash((string)($_POST['reason'] ?? '')));
        if ($reason === '' || strlen($reason) > 500 || ($_POST['confirm_withdraw'] ?? '') !== '1') { self::back('reason_required',$id); }
        update_post_meta($id,self::META.'state','withdrawn');
        update_post_meta($id,self::META.'withdrawn_at',gmdate('c'));
        update_post_meta($id,self::META.'withdrawn_by',get_current_user_id());
        update_post_meta($id,self::META.'withdrawal_reason',$reason);
        self::event($id, 'withdrawn', $reason);
        self::purge_cache();
        self::back('withdrawn',$id);
    }

    /** Optional: a separate correction release (a NEW private draft through the full workflow).
     *  Corrections can also be published in place with "Update published release". */
    public static function correct() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_correct',$id,self::CAP_AUTHOR);
        $p=self::post($id);
        if (!$p || !in_array(self::meta($id,'state'), array('released','withdrawn'), true)) { self::back('invalid_state',$id); }
        $new = wp_insert_post(array('post_type'=>self::TYPE,'post_status'=>'private',
            'post_title'=>substr('Correction: ' . $p->post_title, 0, 180),'post_author'=>get_current_user_id()),true);
        if (is_wp_error($new) || !$new) { self::back('save_failed',$id); }
        foreach (array('summary','kind','source_url') as $k) { update_post_meta($new,self::META.$k,(string)self::meta($id,$k)); }
        update_post_meta($new,self::META.'body',wp_slash((string)self::meta($id,'body')));
        update_post_meta($new,self::META.'embargo_until','');
        update_post_meta($new,self::META.'corrects',$id);
        update_post_meta($new,self::META.'state','draft');
        update_post_meta($new,self::META.'revision',1);
        update_post_meta($new,self::META.'draft_sha',self::current_sha(get_post($new)));
        self::event($new, 'created', 'correction of ' . (string)self::meta($id,'reference'));
        self::event($id, 'correction_started', 'draft #' . (int)$new);
        self::back('correction_draft',$new);
    }

    // ------------------------------------------------------- public output

    private static function date_label($iso) {
        $t = strtotime((string)$iso);
        return $t ? gmdate('j F Y', $t) : '';
    }

    private static function meta_line($p, $kind = null) {
        $kind = $kind === null ? (string)self::meta($p->ID,'kind') : $kind;
        $parts = array(esc_html(self::KINDS[$kind] ?? 'Institutional release'));
        if (self::meta($p->ID,'reference')) { $parts[] = esc_html((string)self::meta($p->ID,'reference')); }
        $released = (string)self::meta($p->ID,'released_at');
        $parts[] = $released ? '<time datetime="' . esc_attr($released) . '">' . esc_html(self::date_label($released)) . '</time>' : 'Not yet released';
        $updated = (string)self::meta($p->ID,'updated_at');
        if ($updated && $released) {
            $parts[] = 'Updated <time datetime="' . esc_attr($updated) . '">' . esc_html(self::date_label($updated)) . '</time>';
        }
        return '<p class="scec-press-release-meta">' . implode(' · ', $parts) . '</p>';
    }

    /** Public notes added with in-place updates: correction notices and optional update notes. */
    private static function public_notes($p) {
        $html = '';
        foreach (self::notes($p->ID) as $n) {
            $label = $n['type'] === 'correction' ? 'Correction' : 'Update';
            $html .= '<p class="scec-press-notice scec-press-notice-' . ($n['type'] === 'correction' ? 'correction' : 'update') . '"><strong>' .
                $label . ', <time datetime="' . esc_attr((string)$n['at']) . '">' . esc_html(self::date_label($n['at'])) . '</time>:</strong> ' .
                esc_html((string)$n['text']) . '</p>';
        }
        return $html;
    }

    private static function notes($id) {
        $notes = array();
        foreach (get_post_meta($id, self::META . 'public_note', false) as $raw) {
            $n = json_decode((string)$raw, true);
            if (is_array($n) && isset($n['at'], $n['type'], $n['text'])) { $notes[] = $n; }
        }
        usort($notes, function ($a, $b) { return strcmp((string)$a['at'], (string)$b['at']); });
        return $notes;
    }

    /** Release body as published: captions from the Media Library and responsive images. */
    public static function format_body($html) {
        $html = preg_replace_callback('/\[caption([^\]]*)\](.*?)\[\/caption\]/s', function ($m) {
            $atts = shortcode_parse_atts($m[1]);
            return img_caption_shortcode(is_array($atts) ? $atts : array(), $m[2]);
        }, (string)$html);
        $html = wp_kses_post($html);
        return function_exists('wp_filter_content_tags') ? wp_filter_content_tags($html) : $html;
    }

    private static function notices($p) {
        $html = '';
        $corrects = (int)self::meta($p->ID,'corrects');
        if ($corrects && ($o = self::post($corrects)) && self::public_state($o) !== '') {
            $html .= '<p class="scec-press-notice scec-press-notice-correction">This release corrects <a href="' .
                esc_url(self::permalink($o->ID)) . '">' . esc_html((string)self::meta($o->ID,'reference') ?: $o->post_title) .
                '</a>, released ' . esc_html(self::date_label(self::meta($o->ID,'released_at'))) . '.</p>';
        }
        $by = (int)self::meta($p->ID,'corrected_by');
        if ($by && ($c = self::post($by)) && self::public_state($c) !== '') {
            $html .= '<p class="scec-press-notice scec-press-notice-corrected"><strong>Correction issued ' .
                esc_html(self::date_label(self::meta($p->ID,'corrected_at'))) . '.</strong> See <a href="' .
                esc_url(self::permalink($c->ID)) . '">' . esc_html((string)self::meta($c->ID,'reference') ?: $c->post_title) .
                '</a>. The original text below is unchanged.</p>';
        }
        return $html;
    }

    /** Public history: dated actions only; no user identities or private notes. */
    private static function public_history($p, $sha = null) {
        $labels = array('approved'=>'Approved by an independent reviewer',
            'owner_self_approved'=>self::SELF_REVIEW_LABEL,'released'=>'Released',
            'update_published'=>'Updated','correction_published'=>'Corrected (see notice)',
            'corrected'=>'Correction issued','withdrawn'=>'Withdrawn');
        $items = '';
        foreach (self::history($p->ID) as $e) {
            if (!isset($labels[$e['action']])) { continue; }
            $items .= '<li><time datetime="' . esc_attr((string)$e['at']) . '">' . esc_html(self::date_label($e['at'])) .
                '</time> — ' . esc_html($labels[$e['action']]) . '</li>';
        }
        $sha = $sha === null ? self::current_sha($p) : $sha;
        return '<section class="scec-press-history" aria-label="Release record"><h2>Release record</h2>' .
            ($items ? '<ul>' . $items . '</ul>' : '') .
            '<p>Content fingerprint (SHA-256): <code>' . esc_html($sha) . '</code></p>' .
            '<p>' . (self::meta($p->ID,'approval_mode') === self::MODE_OWNER_SELF
                ? 'The current text was approved by Sustainable Catalyst&rsquo;s institutional publisher under a single-operator editorial process: it was self-reviewed, not independently reviewed. '
                : 'The current text was approved by a reviewer other than its author. ') .
            'Published text may be revised in place; every published revision is fingerprinted and kept in the release record, ' .
            'and factual corrections are noted on this page. Withdrawn releases keep a notice at this address.</p></section>';
    }

    public static function single($p) {
        return self::article($p, self::content_of($p), self::public_state($p));
    }

    /** One renderer for public pages and previews, so a preview matches the published page. */
    private static function article($p, $c, $state) {
        $room = self::press_page();
        $back = $room ? '<p class="scec-press-back"><a href="' . esc_url(get_permalink($room)) . '">← Press Room</a></p>' : '';
        if ($state === 'withdrawn') {
            return '<article class="scec-press scec-press-release scec-press-withdrawn">' . $back .
                '<h1>Withdrawn: ' . esc_html($c['title']) . '</h1>' . self::meta_line($p, $c['kind']) .
                '<p class="scec-press-notice scec-press-notice-withdrawn"><strong>This release was withdrawn on ' .
                esc_html(self::date_label(self::meta($p->ID,'withdrawn_at'))) . '.</strong> ' .
                esc_html((string)self::meta($p->ID,'withdrawal_reason')) . '</p>' .
                self::public_history($p) . '</article>';
        }
        $source = (string)$c['source_url'];
        return '<article class="scec-press scec-press-release">' . $back .
            '<h1>' . esc_html($c['title']) . '</h1>' . self::meta_line($p, $c['kind']) . self::notices($p) . self::public_notes($p) .
            '<p class="scec-press-release-summary">' . esc_html((string)$c['summary']) . '</p>' .
            '<div class="scec-press-release-body">' . self::format_body((string)$c['body']) . '</div>' .
            ($source ? '<p><a href="' . esc_url($source) . '" rel="noopener noreferrer">Source and background</a></p>' : '') .
            self::public_history($p, self::sha_of($c)) . '</article>';
    }

    private static function public_item($p) {
        $state = self::public_state($p);
        if ($state === '') { return ''; }
        $url = self::permalink($p->ID);
        $html = '<article class="scec-press-release" id="press-release-' . (int)$p->ID . '">' . self::meta_line($p);
        if ($state === 'withdrawn') {
            return $html . '<h3><a href="' . esc_url($url) . '">Withdrawn: ' . esc_html($p->post_title) . '</a></h3>' .
                '<p>Withdrawn ' . esc_html(self::date_label(self::meta($p->ID,'withdrawn_at'))) . '.</p></article>';
        }
        return $html . '<h3><a href="' . esc_url($url) . '">' . esc_html($p->post_title) . '</a></h3>' .
            self::notices($p) . self::public_notes($p) . '<p>' . esc_html((string)self::meta($p->ID,'summary')) . '</p>' .
            '<p><a class="scec-press-read" href="' . esc_url($url) . '">Read release</a></p></article>';
    }

    private static function public_records() {
        if (!self::launch_ready()) { return array(); }
        return get_posts(array('post_type'=>self::TYPE,'post_status'=>'private',
            'numberposts'=>60,'meta_key'=>self::META.'released_at','orderby'=>'meta_value','order'=>'DESC',
            'meta_query'=>array(array('key'=>self::META.'state','value'=>array('released','withdrawn'),'compare'=>'IN'))));
    }

    public static function render($atts=array()) {
        // Reuse the reviewed institutional Press renderer from PR #24, not a second
        // public design or a substitute for the Media hub.
        $base=SC_Engagement_Bridge_882::render_press($atts);
        $archive='';
        foreach (self::public_records() as $p) { $archive.=self::public_item($p); }
        $archive=$archive ?: '<p>No approved public press releases are available yet.</p>';
        return $base.'<section class="scec-press scec-press-archive" aria-labelledby="scec-press-archive-title">'.
            '<div class="scec-press-section"><h2 id="scec-press-archive-title">Official releases &amp; announcements</h2>'.
            $archive.'</div></section>'.self::inquiry_link();
    }

    public static function inquiry_link() {
        // A link to the first-party form; WordPress never owns inbox identity,
        // stores contact records, or relays browser/service credentials.
        if (!defined('SCEC_MEDIA09_PRESS_URL')) { return ''; }
        $url = (string)SCEC_MEDIA09_PRESS_URL;
        $parts = wp_parse_url($url);
        if (!$parts || ($parts['scheme'] ?? '') !== 'https' ||
            !in_array(strtolower($parts['host'] ?? ''), array('sustainablecatalyst.com', 'api.sustainablecatalyst.com'), true) ||
            isset($parts['user']) || isset($parts['pass']) || isset($parts['query']) || isset($parts['fragment']) ||
            (isset($parts['port']) && (int)$parts['port'] !== 443)) { return ''; }
        return '<section class="scec-press"><div class="scec-press-section"><h2>Media &amp; institutional inquiries</h2>'.
            '<p>Press, research collaboration, institutional partnership, and funding inquiries go directly to our private Media team.</p>'.
            '<p><a class="scec880-action" href="'.esc_url($url).'">Send an inquiry</a></p></div></section>';
    }

    // ---------------------------------------------------------- SEO output

    private static function seo_title($p) {
        $prefix = self::public_state($p) === 'withdrawn' ? 'Withdrawn: ' : '';
        return $prefix . $p->post_title . ' | Press | ' . get_bloginfo('name');
    }

    private static function seo_description($p) {
        return wp_html_excerpt((string)self::meta($p->ID,'summary'), 155, '…');
    }

    private static function seo_robots($p) {
        return self::public_state($p) === 'withdrawn' ? array('noindex', 'follow') : array('index', 'follow');
    }

    private static function seo_hooks() {
        $p = self::$current;
        $title = self::seo_title($p);
        $desc = self::seo_description($p);
        $url = self::permalink($p->ID);
        $robots = self::seo_robots($p);
        add_filter('pre_get_document_title', function () use ($title) { return $title; }, 99);
        if (defined('RANK_MATH_VERSION')) {
            add_filter('rank_math/frontend/title', function () use ($title) { return $title; }, 99);
            add_filter('rank_math/frontend/description', function () use ($desc) { return $desc; }, 99);
            add_filter('rank_math/frontend/canonical', function () use ($url) { return $url; }, 99);
            add_filter('rank_math/frontend/robots', function () use ($robots) {
                return array('index' => $robots[0], 'follow' => $robots[1]);
            }, 99);
            foreach (array('facebook/og_title','twitter/twitter_title') as $f) {
                add_filter('rank_math/opengraph/' . $f, function () use ($title) { return $title; }, 99);
            }
            foreach (array('facebook/og_description','twitter/twitter_description') as $f) {
                add_filter('rank_math/opengraph/' . $f, function () use ($desc) { return $desc; }, 99);
            }
            add_filter('rank_math/opengraph/facebook/og_url', function () use ($url) { return $url; }, 99);
            add_filter('rank_math/opengraph/facebook/og_type', function () { return 'article'; }, 99);
            // The release's own NewsArticle replaces Rank Math's home/blog schema here.
            add_filter('rank_math/json_ld', function () { return array(); }, 99);
        } else {
            add_action('wp_head', function () use ($desc, $url, $robots) {
                echo '<meta name="description" content="' . esc_attr($desc) . '">' . "\n";
                echo '<link rel="canonical" href="' . esc_url($url) . '">' . "\n";
                echo '<meta name="robots" content="' . esc_attr(implode(', ', $robots)) . '">' . "\n";
            }, 1);
        }
        add_action('wp_head', array(__CLASS__, 'json_ld'), 20);
    }

    public static function structured_data($p) {
        if (self::public_state($p) !== 'released') { return null; }
        $url = self::permalink($p->ID);
        $modified = self::last_modified($p);
        $data = array(
            '@context' => 'https://schema.org', '@type' => 'NewsArticle',
            'headline' => $p->post_title,
            'description' => (string)self::meta($p->ID,'summary'),
            'datePublished' => (string)self::meta($p->ID,'released_at'),
            'dateModified' => $modified,
            'url' => $url, 'mainEntityOfPage' => $url,
            'identifier' => (string)self::meta($p->ID,'reference'),
            'isAccessibleForFree' => true,
            'publisher' => array('@type' => 'Organization', 'name' => get_bloginfo('name'), 'url' => home_url('/')),
            'author' => array('@type' => 'Organization', 'name' => get_bloginfo('name'), 'url' => home_url('/')),
        );
        $corrections = array();
        $by = (int)self::meta($p->ID,'corrected_by');
        if ($by && ($c = self::post($by)) && self::public_state($c) === 'released') {
            $corrections[] = array('@type' => 'CorrectionComment', 'url' => self::permalink($c->ID),
                'datePublished' => (string)self::meta($p->ID,'corrected_at'),
                'text' => 'Corrected by ' . (string)self::meta($c->ID,'reference'));
        }
        foreach (self::notes($p->ID) as $n) {
            if ($n['type'] !== 'correction') { continue; }
            $corrections[] = array('@type' => 'CorrectionComment', 'datePublished' => (string)$n['at'], 'text' => (string)$n['text']);
        }
        if ($corrections) { $data['correction'] = count($corrections) === 1 ? $corrections[0] : $corrections; }
        return $data;
    }

    private static function last_modified($p) {
        $dates = array((string)self::meta($p->ID,'released_at'), (string)self::meta($p->ID,'updated_at'), (string)self::meta($p->ID,'corrected_at'));
        foreach (self::history($p->ID) as $e) { if ($e['action'] === 'corrected') { $dates[] = (string)$e['at']; } }
        return max($dates);
    }

    public static function json_ld() {
        $data = self::$current ? self::structured_data(self::$current) : null;
        if (!$data) { return; }
        echo '<script type="application/ld+json">' .
            wp_json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_HEX_TAG) . '</script>' . "\n";
    }

    /** Released (not withdrawn) releases only; 404 until public launch. */
    public static function sitemap() {
        $items = array();
        foreach (self::public_records() as $p) {
            if (self::public_state($p) !== 'released') { continue; }
            $lastmod = self::last_modified($p);
            $items[] = '<url><loc>' . esc_url(self::permalink($p->ID)) . '</loc><lastmod>' . esc_html($lastmod) . '</lastmod></url>';
        }
        if (!$items) {
            status_header(404);
            nocache_headers();
            return;
        }
        status_header(200);
        header('Content-Type: application/xml; charset=UTF-8');
        header('X-Robots-Tag: noindex, follow');
        echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n" .
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . implode('', $items) . '</urlset>';
    }

    public static function sitemap_index($xml) {
        $latest = '';
        foreach (self::public_records() as $p) {
            if (self::public_state($p) === 'released') { $latest = max($latest, self::last_modified($p)); }
        }
        if ($latest === '') { return $xml; }
        return $xml . '<sitemap><loc>' . esc_url(home_url('/press/sitemap.xml')) . '</loc><lastmod>' . esc_html($latest) . '</lastmod></sitemap>';
    }

    // ---------------------------------------------------------------- admin

    public static function menu() {
        add_menu_page('Press Room', 'Press Room', self::CAP_REVIEW, self::PAGE,
            array(__CLASS__, 'screen'), 'dashicons-megaphone', 58);
    }

    /** Headline, type, summary, rich-text body (WordPress editor + Media Library), source, embargo. */
    private static function editor_fields($c, $with_embargo) {
        echo '<table class="form-table"><tbody>';
        echo '<tr><th><label for="sc08-title">Headline</label></th><td><input required class="large-text" id="sc08-title" name="title" maxlength="180" value="'.esc_attr($c['title']).'"></td></tr>';
        echo '<tr><th>Release type</th><td><select name="kind">';
        foreach (self::KINDS as $k=>$label) {
            echo '<option value="'.esc_attr($k).'" '.selected($c['kind'] ?: 'press-release',$k,false).'>'.esc_html($label).'</option>';
        }
        echo '</select></td></tr>';
        echo '<tr><th><label for="sc08-summary">Summary</label></th><td><textarea required class="large-text" id="sc08-summary" name="summary" rows="3" maxlength="900">'.esc_textarea($c['summary']).'</textarea></td></tr>';
        echo '<tr><th><label for="scec08body">Release body</label></th><td>';
        // WordPress's own editor: Visual and HTML (Text) modes, headings, lists, links, formatting and Add Media.
        // wpautop off so paragraphs are stored as <p> markup, matching existing releases and the fingerprint.
        wp_editor($c['body'], 'scec08body', array('textarea_name'=>'body','media_buttons'=>true,'textarea_rows'=>20,
            'wpautop'=>false,'drag_drop_upload'=>true,
            // Named entities keep stored markup (e.g. &mdash;) unchanged when nothing is edited.
            'tinymce'=>array('wordpress_adv_hidden'=>false,'entity_encoding'=>'named',
                'entities'=>'38,amp,60,lt,62,gt,160,nbsp,8211,ndash,8212,mdash,8216,lsquo,8217,rsquo,8220,ldquo,8221,rdquo,'.
                    '8230,hellip,8249,lsaquo,8250,rsaquo,171,laquo,187,raquo,169,copy,174,reg,8482,trade,176,deg,177,plusmn,215,times,183,middot,8226,bull',
                'block_formats'=>'Paragraph=p;Heading 2=h2;Heading 3=h3;Heading 4=h4;Quote=blockquote;Preformatted=pre')));
        echo '</td></tr>';
        echo '<tr><th><label for="sc08-source">Optional verified source URL</label></th><td><input class="regular-text" type="url" id="sc08-source" name="source_url" value="'.esc_attr($c['source_url']).'"></td></tr>';
        if ($with_embargo) {
            echo '<tr><th><label for="sc08-embargo">Embargo (UTC)</label></th><td><input type="datetime-local" id="sc08-embargo" name="embargo_until" value="'.esc_attr($c['embargo']).'"></td></tr>';
        }
        echo '</tbody></table>';
    }

    /** The working revision of a released record: preview, compare, publish in place or discard. */
    private static function pending_panel($p, $owner, $author) {
        $id = $p->ID;
        $u = self::pending($id);
        if (!$u) { return; }
        $by = get_userdata((int)$u['by']);
        echo '<div style="border-left:4px solid #b60000;background:#fff;padding:12px 16px;margin:16px 0;max-width:900px">';
        echo '<h3>Working revision r'.(int)$u['snapshot'].' (not public)</h3><p>Saved '.esc_html((string)$u['at']).' by '.
            esc_html($by ? $by->display_name : '#'.(int)$u['by']).' · SHA-256 <code>'.esc_html(substr($u['sha256'],0,16)).'…</code>. The published version remains live until you publish this update.</p>';
        echo '<p><a class="button" target="_blank" rel="noopener" href="'.esc_url(self::preview_url($id,'working')).'">Preview working revision</a> ';
        echo '<a class="button" href="'.esc_url(add_query_arg(array('compare_from'=>'live','compare_to'=>'working'),self::post_url($id))).'">Compare with published</a> ';
        if ($author) { echo '<a class="button" href="'.esc_url(add_query_arg('edit','1',self::post_url($id))).'">Continue editing</a>'; }
        echo '</p>';
        if (self::can(self::CAP_PUBLISH)) {
            $me = get_current_user_id();
            if ($me === (int)$u['by']) {
                if ($me === $owner) {
                    echo '<p><strong>Single-operator self-review.</strong> Publishing your own revision records an owner self-review, disclosed publicly; it is not independent review.</p>';
                    self::form('self_publish_update',$id,'Approve and publish update (self-review)');
                } else {
                    echo '<p><strong>Independent review required:</strong> another publisher must approve and publish your revision.</p>';
                }
            } else {
                self::form('publish_update',$id,'Approve and publish update');
            }
        }
        if ($author) { self::form('discard_update',$id,'Discard working revision'); }
        echo '</div>';
    }

    /** Saved texts (append-only): preview, compare and restore as a new revision. */
    private static function revisions_panel($p, $author) {
        $id = $p->ID;
        $rows = self::snapshots($id);
        $from = sanitize_key((string)($_GET['compare_from'] ?? ''));
        $to = sanitize_key((string)($_GET['compare_to'] ?? ''));
        if ($from !== '' && $to !== '') {
            $a = self::compare_content($p, $from); $b = self::compare_content($p, $to);
            if ($a && $b) {
                echo '<h2>Comparison: '.esc_html($from).' → '.esc_html($to).'</h2><div style="background:#fff;max-width:1100px">';
                $any = false;
                foreach (array('title'=>'Headline','summary'=>'Summary','body'=>'Body','kind'=>'Type','source_url'=>'Source URL') as $k=>$label) {
                    $ta = $k === 'body' ? self::diff_lines($a[$k]) : (string)$a[$k];
                    $tb = $k === 'body' ? self::diff_lines($b[$k]) : (string)$b[$k];
                    $d = wp_text_diff($ta, $tb, array('title'=>$label, 'show_split_view'=>true));
                    if ($d) { echo $d; $any = true; }
                }
                if (!$any) { echo '<p>No differences.</p>'; }
                echo '</div>';
            }
        }
        if (!$rows) { return; }
        $live = self::current_sha($p);
        echo '<h2>Revisions</h2><table class="widefat striped"><thead><tr><th>Rev</th><th>UTC</th><th>User</th><th>Origin</th><th>SHA-256</th><th>Note</th><th>Actions</th></tr></thead><tbody>';
        foreach (array_reverse($rows, true) as $n=>$r) {
            $usr = get_userdata((int)$r['user']);
            echo '<tr><td>r'.(int)$n.($r['sha256'] === $live ? ' <strong>(current)</strong>' : '').'</td><td>'.esc_html((string)$r['at']).'</td><td>'.
                esc_html($usr ? $usr->display_name : '#'.(int)$r['user']).'</td><td>'.esc_html((string)$r['origin']).'</td><td><code>'.
                esc_html(substr((string)$r['sha256'],0,12)).'</code></td><td>'.esc_html((string)$r['note']).'</td><td>'.
                '<a href="'.esc_url(self::preview_url($id,(string)$n)).'" target="_blank" rel="noopener">Preview</a> · '.
                '<a href="'.esc_url(add_query_arg(array('compare_from'=>(string)$n,'compare_to'=>'live'),self::post_url($id))).'">Compare with current</a>';
            if ($author && in_array((string)self::meta($id,'state','draft'), array('draft','released'), true) && $r['sha256'] !== $live) {
                self::form('restore',$id,'Restore as new revision',$n);
            }
            echo '</td></tr>';
        }
        echo '</tbody></table>';
    }

    private static function compare_content($p, $key) {
        if ($key === 'live') { return self::content_of($p); }
        if ($key === 'working') { $u = self::pending($p->ID); return $u ? $u['content'] : null; }
        return ctype_digit($key) ? self::snapshot_content($p->ID, (int)$key) : null;
    }

    /** One block element per line so body comparisons are readable. */
    private static function diff_lines($html) {
        return trim(preg_replace('#(</(p|h[1-6]|li|ul|ol|figure|blockquote|pre|table|tr)>|<br\s*/?>)#i', "$1\n", (string)$html));
    }

    private static function form($action,$id,$label,$extra=null) {
        echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
        $handler = $action === 'self_approve' ? 'approve' : ($action === 'self_publish_update' ? 'publish_update' : $action);
        echo '<input type="hidden" name="action" value="'.esc_attr('scec08_'.$handler).'">';
        echo '<input type="hidden" name="id" value="'.(int)$id.'">';
        wp_nonce_field('scec08_'.$handler.'_'.$id);
        if ($action==='publish_update' || $action==='self_publish_update') {
            $u = self::pending($id);
            echo '<input type="hidden" name="update_sha" value="'.esc_attr($u ? $u['sha256'] : '').'">';
            echo '<fieldset><legend><strong>Type of change</strong></legend>';
            foreach (self::CHANGE_TYPES as $k=>$type_label) {
                echo '<p><label><input type="radio" name="change_type" value="'.esc_attr($k).'" required> '.esc_html($type_label).'</label></p>';
            }
            echo '</fieldset><p><label>Public note (required for a factual correction; optional otherwise; shown on the release)<br>'.
                '<textarea name="public_note" rows="2" cols="70" maxlength="500"></textarea></label></p>';
        }
        if ($action==='restore') {
            echo '<input type="hidden" name="snapshot" value="'.(int)$extra.'">';
        }
        if (in_array($action, array('approve','self_approve','publish_update','self_publish_update'), true)) {
            foreach (self::ATTESTATIONS as $check=>$name) {
                echo '<p><label><input type="checkbox" name="check_'.esc_attr($check).'" value="1" required> '.esc_html($name).' confirmed</label></p>';
            }
        }
        if ($action==='self_approve' || $action==='self_publish_update') {
            echo '<p><label><input type="checkbox" name="owner_self_approval" value="1" required> I approve this exact revision as the institutional owner. '.
                'I understand this is single-operator self-review, not independent review, and that it is recorded and disclosed as such.</label></p>';
        }
        if ($action==='return') {
            echo '<p><label>Note to author (required)<br><textarea name="note" rows="3" cols="70" maxlength="1000" required></textarea></label></p>';
        }
        if ($action==='withdraw') {
            echo '<p><label>Public withdrawal reason (required, shown on the release page)<br><textarea name="reason" rows="3" cols="70" maxlength="500" required></textarea></label></p>';
            echo '<p><label><input type="checkbox" name="confirm_withdraw" value="1" required> Remove this release from public view and show the withdrawal notice at its permanent URL</label></p>';
        }
        submit_button($label,'secondary','submit',true);
        echo '</form>';
    }

    public static function screen() {
        if (!self::can(self::CAP_REVIEW)) { wp_die('Forbidden','',403); }
        $id=absint($_GET['id'] ?? 0);
        $p=self::post($id);
        $state=$p ? self::meta($id,'state','draft') : 'draft';
        $notice=sanitize_key((string)($_GET['notice'] ?? ''));
        $author = self::can(self::CAP_AUTHOR);
        echo '<div class="wrap"><h1>Press Room</h1>';
        $owner = self::single_operator_owner();
        echo '<p>Private institutional releases. Public release is disabled by default and requires a published Press page, explicit deployment authorization, and approval of the exact submitted revision: by a reviewer other than the author, or, in single-operator mode, by the institutional owner as a recorded self-review.</p>';
        echo '<p><strong>Review mode:</strong> '.($owner ? 'Single-operator (owner self-review permitted and disclosed; independent review also accepted)' : 'Independent review required').'</p>';
        echo '<p><strong>Public release gate:</strong> '.(self::enabled()?'Enabled by configuration':'OFF — private authoring only').
            ' · <strong>Press page:</strong> '.(self::press_page()?'published with [sc_press_room]':'not published').'</p>';
        if ($notice) { echo '<div class="notice notice-info"><p>'.esc_html(str_replace('_',' ',$notice)).'</p></div>'; }
        echo '<h2>Press records</h2>';
        if ($author) {
            echo '<p><a class="button" href="'.esc_url(self::post_url(0)).'">New press release</a> ';
            echo '<a class="button" href="'.esc_url(admin_url('options-general.php?page=scec-media07')).'">Newsletter Studio</a></p>';
        }
        $posts=get_posts(array('post_type'=>self::TYPE,'post_status'=>'private','numberposts'=>60,
            'orderby'=>'modified','order'=>'DESC'));
        echo '<table class="widefat striped"><thead><tr><th>Title</th><th>Kind</th><th>Reference</th><th>Editorial state</th></tr></thead><tbody>';
        foreach ($posts as $item) {
            echo '<tr><td><a href="'.esc_url(self::post_url($item->ID)).'">'.esc_html($item->post_title).'</a></td><td>'.
                esc_html(self::KINDS[self::meta($item->ID,'kind')] ?? '—').'</td><td>'.
                esc_html((string)self::meta($item->ID,'reference','—')).'</td><td>'.
                esc_html((string)self::meta($item->ID,'state','draft')).'</td></tr>';
        }
        echo '</tbody></table><h2>'.($p?'Press record':($author?'Create press draft':'Select a record to review')).'</h2>';
        if ($p) {
            echo '<p><strong>Status:</strong> '.esc_html($state).' · Revision '.(int)self::meta($id,'revision',1).
                ' · Content SHA-256 <code>'.esc_html(substr(self::current_sha($p),0,16)).'…</code></p>';
            if (self::meta($id,'corrects')) { echo '<p>Correction of record #'.(int)self::meta($id,'corrects').'.</p>'; }
            if (self::permalink($id)) { echo '<p><strong>Permanent URL:</strong> <code>'.esc_html(self::permalink($id)).'</code> · '.esc_html((string)self::meta($id,'reference')).'</p>'; }
        }
        $editing = $p && $state==='released' && $author && isset($_GET['edit']);
        if ($state==='draft' && $author) {
            echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
            echo '<input type="hidden" name="action" value="scec08_save"><input type="hidden" name="id" value="'.(int)$id.'">';
            wp_nonce_field('scec08_save_'.$id);
            self::editor_fields($p ? self::content_of($p) : array('title'=>'','summary'=>'','body'=>'','kind'=>'press-release','source_url'=>'','embargo'=>''), true);
            submit_button('Save private draft'); echo '</form>';
            if ($p) {
                echo '<p><a class="button" target="_blank" rel="noopener" href="'.esc_url(self::preview_url($id,'current')).'">Preview saved draft</a></p>';
                self::form('submit',$id,'Submit for review');
            }
        } elseif ($editing) {
            $u = self::pending($id);
            echo '<h3>Edit published release</h3><p>The published version stays live while you edit. Saving creates a working revision; nothing changes publicly until you approve and publish the update. The permanent URL, reference and publication date are kept.</p>';
            echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
            echo '<input type="hidden" name="action" value="scec08_save_update"><input type="hidden" name="id" value="'.(int)$id.'">';
            wp_nonce_field('scec08_save_update_'.$id);
            self::editor_fields($u ? $u['content'] : self::content_of($p), false);
            submit_button('Save working revision'); echo '</form>';
            echo '<p><a href="'.esc_url(self::post_url($id)).'">Cancel</a></p>';
        } elseif ($p) {
            echo '<p><strong>Headline:</strong> '.esc_html($p->post_title).'</p><p>'.esc_html((string)self::meta($id,'summary')).'</p>';
            echo '<div style="max-width:760px;padding:20px;background:#fff;border:1px solid #ddd">'.self::format_body((string)self::meta($id,'body')).'</div>';
            echo '<p><a class="button" target="_blank" rel="noopener" href="'.esc_url(self::preview_url($id,'current')).'">Preview</a>';
            if ($state==='released' && $author) {
                echo ' <a class="button button-primary" href="'.esc_url(add_query_arg('edit','1',self::post_url($id))).'">Edit release</a>';
            }
            if (self::permalink($id) && self::public_state($p) !== '') {
                echo ' <a class="button" target="_blank" rel="noopener" href="'.esc_url(self::permalink($id)).'">View public page</a>';
            }
            echo '</p>';
            if (in_array($state, array('in_review','approved'), true) && $author) {
                self::form('reopen',$id,'Edit release (return to draft; clears approval)');
            }
            if ($state==='in_review' && self::can(self::CAP_REVIEW)) {
                $me = get_current_user_id();
                if ($me === (int)self::meta($id,'submitted_by') || $me === (int)$p->post_author) {
                    if ($me === $owner) {
                        echo '<p><strong>Single-operator self-review.</strong> You authored or submitted this release. Approving it records an owner self-review, which is disclosed publicly and is not independent review.</p>';
                        self::form('self_approve',$id,'Approve as institutional owner (self-review)');
                        self::form('return',$id,'Return to draft');
                    } else {
                        echo '<p><strong>Independent review required:</strong> you authored or submitted this release, so another reviewer must approve or return it.</p>';
                    }
                } else {
                    self::form('approve',$id,'Approve independently reviewed release');
                    self::form('return',$id,'Return to author');
                }
            }
            if ($state==='approved' && self::can(self::CAP_PUBLISH)) { self::form('release',$id,'Release to public Press Room (feature-gated)'); }
            if ($state==='released') { self::pending_panel($p, $owner, $author); }
            if ($state==='released' && self::can(self::CAP_PUBLISH)) { self::form('withdraw',$id,'Withdraw release'); }
            if (in_array($state, array('released','withdrawn'), true) && $author && !self::meta($id,'corrected_by')) {
                self::form('correct',$id,'Optional: issue a separate correction release');
            }
        }
        if ($p) { self::revisions_panel($p, $author); }
        if ($p) {
            if (self::meta($id,'approval_mode')) {
                echo '<p><strong>Approval:</strong> '.esc_html(self::meta($id,'approval_mode') === self::MODE_OWNER_SELF ? self::SELF_REVIEW_LABEL : 'Independent reviewer').'</p>';
            }
            echo '<h2>History</h2><table class="widefat striped"><thead><tr><th>UTC</th><th>Action</th><th>User</th><th>SHA-256</th><th>Note</th></tr></thead><tbody>';
            foreach (self::history($id) as $e) {
                $u = get_userdata((int)$e['user']);
                echo '<tr><td>'.esc_html((string)$e['at']).'</td><td>'.esc_html((string)$e['action']).'</td><td>'.
                    esc_html($u ? $u->display_name : '#'.(int)$e['user']).'</td><td><code>'.esc_html(substr((string)$e['sha256'],0,12)).'</code></td><td>'.
                    esc_html((string)$e['note']).'</td></tr>';
            }
            echo '</tbody></table>';
        }
        echo '</div>';
    }
}
