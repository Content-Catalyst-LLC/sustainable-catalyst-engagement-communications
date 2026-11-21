<?php
/**
 * MEDIA-08 / MEDIA-08.1: dedicated institutional Press Room, private editorial
 * objects, and an approved-only public projection with permanent release URLs.
 * No email/outreach/remote publishing.
 *
 * Publication is disabled unless separately enabled in wp-config and a
 * distinct human reviewer approves the immutable submitted revision.
 * Released records are never rewritten: corrections are new reviewed records,
 * withdrawals keep a public notice at the same URL, and every state change is
 * appended to the record's history.
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Media08_Press_Room {
    const TYPE = 'scec_press_release';
    const META = '_scec_media08_';
    const PAGE = 'scec-media08';
    const REWRITE_VERSION = '8.9.5-2';
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
        add_action('template_redirect', array(__CLASS__, 'template_redirect'), 1);
        add_action('admin_menu', array(__CLASS__, 'menu'));
        foreach (array('save','submit','approve','return','release','withdraw','correct') as $action) {
            add_action('admin_post_scec08_' . $action, array(__CLASS__, $action === 'return' ? 'return_to_author' : $action));
        }
        add_shortcode('sc_press_room', array(__CLASS__, 'render'));
        add_shortcode('sc_press_inquiry', array(__CLASS__, 'inquiry_link'));
        add_filter('rank_math/sitemap/index', array(__CLASS__, 'sitemap_index'));
    }

    public static function enabled() {
        return defined('SCEC_MEDIA08_PUBLIC_RELEASE') && SCEC_MEDIA08_PUBLIC_RELEASE === true;
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
        // Not *-sitemap.xml: Rank Math's `([^/]+?)-sitemap.xml` rule would capture it.
        add_rewrite_rule('^press/releases\.xml$', 'index.php?scec_press_sitemap=1', 'top');
        // Flush once per version, only on a web request: under WP-CLI other plugins
        // (e.g. Rank Math's sitemap) do not register their rules, so a CLI flush drops them.
        if (get_option(self::REWRITE_OPTION) !== self::REWRITE_VERSION && !(defined('WP_CLI') && WP_CLI)) {
            flush_rewrite_rules(false);
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
     * content hash, author and reviewer differ, and any embargo has passed.
     */
    public static function public_state($p) {
        if (!self::launch_ready()) { return ''; }
        $state = (string)self::meta($p->ID, 'state');
        if (!in_array($state, array('released', 'withdrawn'), true)) { return ''; }
        $sha = self::current_sha($p);
        if (!hash_equals((string)self::meta($p->ID,'released_sha'), $sha) ||
            !hash_equals((string)self::meta($p->ID,'approved_sha'), $sha) ||
            !self::meta($p->ID,'reviewer_id') ||
            (int)self::meta($p->ID,'submitted_by') === (int)self::meta($p->ID,'reviewer_id')) {
            return '';
        }
        if (!self::embargo_passed((string)self::meta($p->ID,'embargo_until'), time())) { return ''; }
        return $state;
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

    public static function publication_gate($enabled, $state, $current_sha, $approved_sha, $author_id, $reviewer_id, $embargo, $now_utc) {
        if (!$enabled || $state !== 'approved' || !$approved_sha ||
            !hash_equals((string)$approved_sha, (string)$current_sha) ||
            !$author_id || !$reviewer_id || (int)$author_id === (int)$reviewer_id) {
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
        add_post_meta($id, self::META . 'event', wp_json_encode(array(
            'at' => gmdate('c'), 'action' => $action, 'user' => get_current_user_id(),
            'state' => (string)self::meta($id, 'state'),
            'sha256' => $p ? self::current_sha($p) : '',
            'note' => (string)$note,
        ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
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
        // Rank Math caches its sitemap index. Invalidate it directly (its watcher only runs
        // when the sitemap module is loaded, which is not the case under WP-CLI).
        if (class_exists('\\RankMath\\Sitemap\\Cache')) { \RankMath\Sitemap\Cache::invalidate_storage('1'); }
    }

    public static function save() {
        $id = absint($_POST['id'] ?? 0);
        self::admin_check('scec08_save', $id, self::CAP_AUTHOR);
        $p = self::post($id);
        if ($id && !$p) { self::back('not_found'); }
        if ($p && self::meta($id,'state','draft') !== 'draft') {
            self::back('locked', $id);
        }
        $title = sanitize_text_field(wp_unslash((string)($_POST['title'] ?? '')));
        $summary = sanitize_textarea_field(wp_unslash((string)($_POST['summary'] ?? '')));
        $body = wp_kses_post(wp_unslash((string)($_POST['body'] ?? '')));
        $kind = sanitize_key((string)($_POST['kind'] ?? ''));
        $source_url = esc_url_raw(wp_unslash((string)($_POST['source_url'] ?? '')));
        $embargo = sanitize_text_field(wp_unslash((string)($_POST['embargo_until'] ?? '')));
        if ($title === '' || $summary === '' || trim(wp_strip_all_tags($body)) === '' ||
            !isset(self::KINDS[$kind]) || strlen($title)>180 || strlen($summary)>900 ||
            strlen($body)>75000 || strlen($source_url)>600 ||
            ($source_url && (strpos($source_url, 'https://') !== 0 || !wp_http_validate_url($source_url))) ||
            ($embargo && !preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/D', $embargo))) {
            self::back('invalid',$id);
        }
        $created = !$p;
        if (!$p) {
            $id = wp_insert_post(array('post_type'=>self::TYPE,'post_status'=>'private',
                'post_title'=>$title,'post_author'=>get_current_user_id()),true);
            if (is_wp_error($id) || !$id) { self::back('save_failed'); }
        } else {
            $result = wp_update_post(array('ID'=>$id,'post_title'=>$title),true);
            if (is_wp_error($result)) { self::back('save_failed',$id); }
        }
        update_post_meta($id,self::META.'summary',$summary);
        update_post_meta($id,self::META.'body',wp_slash($body));
        update_post_meta($id,self::META.'kind',$kind);
        update_post_meta($id,self::META.'source_url',$source_url);
        update_post_meta($id,self::META.'embargo_until',$embargo);
        update_post_meta($id,self::META.'state','draft');
        update_post_meta($id,self::META.'draft_sha',self::current_sha(get_post($id)));
        update_post_meta($id,self::META.'revision',1+(int)self::meta($id,'revision',0));
        self::event($id, $created ? 'created' : 'saved', 'revision ' . (int)self::meta($id,'revision'));
        self::back('saved',$id);
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
        if (!$author || $author===$me || (int)$p->post_author===$me) { self::back('independent_review_required',$id); }
        if (!hash_equals((string)self::meta($id,'submitted_sha'),self::current_sha($p))) {
            self::back('source_changed',$id);
        }
        foreach (array_keys(self::ATTESTATIONS) as $check) {
            if (($_POST['check_'.$check] ?? '') !== '1') { self::back('review_incomplete',$id); }
        }
        update_post_meta($id,self::META.'approved_sha',self::current_sha($p));
        update_post_meta($id,self::META.'reviewer_id',$me);
        update_post_meta($id,self::META.'approved_at',gmdate('c'));
        update_post_meta($id,self::META.'attestations',implode(',', array_keys(self::ATTESTATIONS)));
        update_post_meta($id,self::META.'state','approved');
        self::event($id, 'approved', 'attested: ' . implode(', ', array_keys(self::ATTESTATIONS)));
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
            self::meta($id,'embargo_until'),time());
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

    /** Start a correction: a NEW private draft that must pass full independent review. */
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

    private static function meta_line($p) {
        $parts = array(esc_html(self::KINDS[(string)self::meta($p->ID,'kind')] ?? 'Institutional release'));
        if (self::meta($p->ID,'reference')) { $parts[] = esc_html((string)self::meta($p->ID,'reference')); }
        $parts[] = '<time datetime="' . esc_attr((string)self::meta($p->ID,'released_at')) . '">' .
            esc_html(self::date_label(self::meta($p->ID,'released_at'))) . '</time>';
        return '<p class="scec-press-release-meta">' . implode(' · ', $parts) . '</p>';
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
    private static function public_history($p) {
        $labels = array('approved'=>'Approved by an independent reviewer','released'=>'Released',
            'corrected'=>'Correction issued','withdrawn'=>'Withdrawn');
        $items = '';
        foreach (self::history($p->ID) as $e) {
            if (!isset($labels[$e['action']])) { continue; }
            $items .= '<li><time datetime="' . esc_attr((string)$e['at']) . '">' . esc_html(self::date_label($e['at'])) .
                '</time> — ' . esc_html($labels[$e['action']]) . '</li>';
        }
        $sha = self::current_sha($p);
        return '<section class="scec-press-history" aria-label="Release record"><h2>Release record</h2>' .
            ($items ? '<ul>' . $items . '</ul>' : '') .
            '<p>Content fingerprint (SHA-256): <code>' . esc_html($sha) . '</code></p>' .
            '<p>Releases are approved by a reviewer other than the author and are never edited after release. ' .
            'Corrections are published as separate releases; withdrawn releases keep a notice at this address.</p></section>';
    }

    public static function single($p) {
        $state = self::public_state($p);
        $room = self::press_page();
        $back = $room ? '<p class="scec-press-back"><a href="' . esc_url(get_permalink($room)) . '">← Press Room</a></p>' : '';
        if ($state === 'withdrawn') {
            return '<article class="scec-press scec-press-release scec-press-withdrawn">' . $back .
                '<h1>Withdrawn: ' . esc_html($p->post_title) . '</h1>' . self::meta_line($p) .
                '<p class="scec-press-notice scec-press-notice-withdrawn"><strong>This release was withdrawn on ' .
                esc_html(self::date_label(self::meta($p->ID,'withdrawn_at'))) . '.</strong> ' .
                esc_html((string)self::meta($p->ID,'withdrawal_reason')) . '</p>' .
                self::public_history($p) . '</article>';
        }
        $source = (string)self::meta($p->ID,'source_url');
        return '<article class="scec-press scec-press-release">' . $back .
            '<h1>' . esc_html($p->post_title) . '</h1>' . self::meta_line($p) . self::notices($p) .
            '<p class="scec-press-release-summary">' . esc_html((string)self::meta($p->ID,'summary')) . '</p>' .
            '<div class="scec-press-release-body">' . wp_kses_post((string)self::meta($p->ID,'body')) . '</div>' .
            ($source ? '<p><a href="' . esc_url($source) . '" rel="noopener noreferrer">Source and background</a></p>' : '') .
            self::public_history($p) . '</article>';
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
            self::notices($p) . '<p>' . esc_html((string)self::meta($p->ID,'summary')) . '</p>' .
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
        $modified = (string)self::meta($p->ID,'released_at');
        foreach (self::history($p->ID) as $e) { if ($e['action'] === 'corrected') { $modified = (string)$e['at']; } }
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
        $by = (int)self::meta($p->ID,'corrected_by');
        if ($by && ($c = self::post($by)) && self::public_state($c) === 'released') {
            $data['correction'] = array('@type' => 'CorrectionComment', 'url' => self::permalink($c->ID),
                'datePublished' => (string)self::meta($p->ID,'corrected_at'),
                'text' => 'Corrected by ' . (string)self::meta($c->ID,'reference'));
        }
        return $data;
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
            $lastmod = (string)self::meta($p->ID,'corrected_at') ?: (string)self::meta($p->ID,'released_at');
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
            if (self::public_state($p) === 'released') { $latest = max($latest, (string)self::meta($p->ID,'released_at')); }
        }
        if ($latest === '') { return $xml; }
        return $xml . '<sitemap><loc>' . esc_url(home_url('/press/releases.xml')) . '</loc><lastmod>' . esc_html($latest) . '</lastmod></sitemap>';
    }

    // ---------------------------------------------------------------- admin

    public static function menu() {
        add_menu_page('Press Room', 'Press Room', self::CAP_REVIEW, self::PAGE,
            array(__CLASS__, 'screen'), 'dashicons-megaphone', 58);
    }

    private static function form($action,$id,$label) {
        echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
        echo '<input type="hidden" name="action" value="'.esc_attr('scec08_'.$action).'">';
        echo '<input type="hidden" name="id" value="'.(int)$id.'">';
        wp_nonce_field('scec08_'.$action.'_'.$id);
        if ($action==='approve') {
            foreach (self::ATTESTATIONS as $check=>$name) {
                echo '<p><label><input type="checkbox" name="check_'.esc_attr($check).'" value="1" required> '.esc_html($name).' confirmed</label></p>';
            }
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
        echo '<p>Private institutional releases. Public release is disabled by default, requires approval by a reviewer other than the author, a published Press page, and explicit deployment authorization.</p>';
        echo '<p><strong>Public release gate:</strong> '.(self::enabled()?'Enabled by configuration — verify independent approval':'OFF — private authoring only').
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
        if ($state==='draft' && $author) {
            echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
            echo '<input type="hidden" name="action" value="scec08_save"><input type="hidden" name="id" value="'.(int)$id.'">';
            wp_nonce_field('scec08_save_'.$id);
            echo '<table class="form-table"><tbody>';
            echo '<tr><th><label for="sc08-title">Headline</label></th><td><input required class="regular-text" id="sc08-title" name="title" maxlength="180" value="'.esc_attr($p?$p->post_title:'').'"></td></tr>';
            echo '<tr><th>Release type</th><td><select name="kind">';
            foreach (self::KINDS as $k=>$label) {
                echo '<option value="'.esc_attr($k).'" '.selected((string)self::meta($id,'kind','press-release'),$k,false).'>'.esc_html($label).'</option>';
            }
            echo '</select></td></tr>';
            echo '<tr><th><label for="sc08-summary">Summary</label></th><td><textarea required id="sc08-summary" name="summary" rows="3" cols="75" maxlength="900">'.esc_textarea((string)self::meta($id,'summary')).'</textarea></td></tr>';
            echo '<tr><th><label for="sc08-body">Release body (allowed HTML)</label></th><td><textarea required id="sc08-body" name="body" rows="12" cols="80">'.esc_textarea((string)self::meta($id,'body')).'</textarea></td></tr>';
            echo '<tr><th><label for="sc08-source">Optional verified source URL</label></th><td><input class="regular-text" type="url" id="sc08-source" name="source_url" value="'.esc_attr((string)self::meta($id,'source_url')).'"></td></tr>';
            echo '<tr><th><label for="sc08-embargo">Embargo (UTC)</label></th><td><input type="datetime-local" id="sc08-embargo" name="embargo_until" value="'.esc_attr((string)self::meta($id,'embargo_until')).'"></td></tr>';
            echo '</tbody></table>';
            submit_button('Save private draft'); echo '</form>';
            if ($p) { self::form('submit',$id,'Submit for independent review'); }
        } elseif ($p) {
            echo '<p><strong>Headline:</strong> '.esc_html($p->post_title).'</p><p>'.esc_html((string)self::meta($id,'summary')).'</p>';
            echo '<div style="max-width:760px;padding:20px;background:#fff;border:1px solid #ddd">'.wp_kses_post((string)self::meta($id,'body')).'</div>';
            if ($state==='in_review' && self::can(self::CAP_REVIEW)) {
                $me = get_current_user_id();
                if ($me === (int)self::meta($id,'submitted_by') || $me === (int)$p->post_author) {
                    echo '<p><strong>Independent review required:</strong> you authored or submitted this release, so another reviewer must approve or return it.</p>';
                } else {
                    self::form('approve',$id,'Approve independently reviewed release');
                    self::form('return',$id,'Return to author');
                }
            }
            if ($state==='approved' && self::can(self::CAP_PUBLISH)) { self::form('release',$id,'Release to public Press Room (feature-gated)'); }
            if ($state==='released' && self::can(self::CAP_PUBLISH)) { self::form('withdraw',$id,'Withdraw release'); }
            if (in_array($state, array('released','withdrawn'), true) && $author && !self::meta($id,'corrected_by')) { self::form('correct',$id,'Start a correction (new reviewed release)'); }
            echo '<p>Changes to submitted content require a new release record/review. Editing approved revisions in place is blocked.</p>';
        }
        if ($p) {
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
