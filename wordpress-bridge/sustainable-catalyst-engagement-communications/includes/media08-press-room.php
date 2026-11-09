<?php
/**
 * MEDIA-08: dedicated institutional Press Room, private editorial objects,
 * and an approved-only public projection. No email/outreach/remote publishing.
 *
 * Publication is disabled unless separately enabled in wp-config and a
 * distinct human administrator approves the immutable submitted revision.
 */
if (!defined('ABSPATH')) { exit; }

final class SC_Media08_Press_Room {
    const TYPE = 'scec_press_release';
    const META = '_scec_media08_';
    const PAGE = 'scec-media08';
    const KINDS = array(
        'press-release' => 'Press release',
        'announcement' => 'Institutional announcement',
        'statement' => 'Official statement',
        'research-update' => 'Research announcement',
        'event-notice' => 'Event notice',
    );

    public static function boot() {
        add_action('init', array(__CLASS__, 'register_type'));
        add_action('admin_menu', array(__CLASS__, 'menu'));
        add_action('admin_post_scec08_save', array(__CLASS__, 'save'));
        add_action('admin_post_scec08_submit', array(__CLASS__, 'submit'));
        add_action('admin_post_scec08_approve', array(__CLASS__, 'approve'));
        add_action('admin_post_scec08_release', array(__CLASS__, 'release'));
        add_shortcode('sc_press_room', array(__CLASS__, 'render'));
    }

    public static function enabled() {
        return defined('SCEC_MEDIA08_PUBLIC_RELEASE') && SCEC_MEDIA08_PUBLIC_RELEASE === true;
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

    public static function menu() {
        add_submenu_page('options-general.php', 'Press Room', 'Press Room (MEDIA-08)',
            'manage_options', self::PAGE, array(__CLASS__, 'screen'));
    }

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
        return !$embargo || strtotime((string)$embargo) <= (int)$now_utc;
    }

    private static function current_sha($p) {
        return self::digest($p->post_title,
            (string)self::meta($p->ID, 'summary'),
            (string)self::meta($p->ID, 'body'),
            (string)self::meta($p->ID, 'kind'),
            (string)self::meta($p->ID, 'source_url'),
            (string)self::meta($p->ID, 'embargo_until'));
    }

    private static function admin_check($action, $id) {
        if (!current_user_can('manage_options')) { wp_die('Not authorized', '', 403); }
        if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') { wp_die('POST only', '', 405); }
        check_admin_referer($action . '_' . $id);
    }

    private static function back($notice, $id = 0) {
        wp_safe_redirect(add_query_arg(array('page'=>self::PAGE,'notice'=>$notice,'id'=>$id),
            admin_url('options-general.php')));
        exit;
    }

    private static function post_url($id) {
        $args = array('page'=>self::PAGE);
        if ($id) { $args['id'] = $id; }
        return add_query_arg($args, admin_url('options-general.php'));
    }

    public static function save() {
        $id = absint($_POST['id'] ?? 0);
        self::admin_check('scec08_save', $id);
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
            ($source_url && !wp_http_validate_url($source_url)) ||
            ($embargo && !preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/D', $embargo))) {
            self::back('invalid',$id);
        }
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
        self::back('saved',$id);
    }

    public static function submit() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_submit',$id);
        $p=self::post($id);
        if (!$p || self::meta($id,'state','draft')!=='draft') { self::back('invalid_state',$id); }
        if (!self::meta($id,'summary') || !self::meta($id,'body')) { self::back('invalid',$id); }
        $sha=self::current_sha($p);
        update_post_meta($id,self::META.'submitted_sha',$sha);
        update_post_meta($id,self::META.'state','in_review');
        update_post_meta($id,self::META.'submitted_by',get_current_user_id());
        update_post_meta($id,self::META.'submitted_at',gmdate('c'));
        self::back('submitted',$id);
    }

    public static function approve() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_approve',$id);
        $p=self::post($id);
        if (!$p || self::meta($id,'state')!=='in_review') { self::back('invalid_state',$id); }
        $author=(int)self::meta($id,'submitted_by',0);
        if (!$author || $author===get_current_user_id()) { self::back('independent_review_required',$id); }
        if (!hash_equals((string)self::meta($id,'submitted_sha'),self::current_sha($p))) {
            self::back('source_changed',$id);
        }
        foreach (array('rights','source','privacy','institutional') as $check) {
            if (($_POST['check_'.$check] ?? '') !== '1') { self::back('review_incomplete',$id); }
        }
        update_post_meta($id,self::META.'approved_sha',self::current_sha($p));
        update_post_meta($id,self::META.'reviewer_id',get_current_user_id());
        update_post_meta($id,self::META.'approved_at',gmdate('c'));
        update_post_meta($id,self::META.'state','approved');
        self::back('approved',$id);
    }

    /** Explicitly feature gated. No auto-send, social, API or cross-post. */
    public static function release() {
        $id=absint($_POST['id'] ?? 0);
        self::admin_check('scec08_release',$id);
        $p=self::post($id);
        if (!$p) { self::back('not_found',$id); }
        // Require an actual public Press page with the dedicated shortcode.
        $page=get_page_by_path('press',OBJECT,'page');
        if (!$page || $page->post_status!=='publish' || post_password_required($page) ||
            !has_shortcode($page->post_content,'sc_press_room')) {
            self::back('press_page_missing',$id);
        }
        $eligible=self::publication_gate(self::enabled(),
            self::meta($id,'state'),self::current_sha($p),
            self::meta($id,'approved_sha'),(int)self::meta($id,'submitted_by',0),
            (int)self::meta($id,'reviewer_id',0),
            self::meta($id,'embargo_until'),time());
        if (!$eligible) { self::back('release_blocked',$id); }
        update_post_meta($id,self::META.'state','released');
        update_post_meta($id,self::META.'released_sha',self::current_sha($p));
        update_post_meta($id,self::META.'released_at',gmdate('c'));
        update_post_meta($id,self::META.'released_by',get_current_user_id());
        self::back('released',$id);
    }

    private static function public_item($p) {
        if (!self::enabled() || self::meta($p->ID,'state')!=='released' ||
            !hash_equals((string)self::meta($p->ID,'released_sha'),self::current_sha($p)) ||
            (int)self::meta($p->ID,'submitted_by') === (int)self::meta($p->ID,'reviewer_id') ||
            !self::meta($p->ID,'reviewer_id')) {
            return '';
        }
        $embargo=self::meta($p->ID,'embargo_until');
        if ($embargo && strtotime((string)$embargo)>time()) { return ''; }
        $kind=(string)self::meta($p->ID,'kind');
        $source=(string)self::meta($p->ID,'source_url');
        $html='<article class="scec-press-release" id="press-release-'.(int)$p->ID.'">';
        $html.='<p class="scec-press-release-meta">'.esc_html(self::KINDS[$kind] ?? 'Institutional release').
            ' · '.esc_html(substr((string)self::meta($p->ID,'released_at'),0,10)).'</p>';
        $html.='<h3>'.esc_html($p->post_title).'</h3><p>'.esc_html((string)self::meta($p->ID,'summary')).'</p>';
        $html.='<details><summary>Read release</summary><div class="scec-press-release-body">'.
            wp_kses_post((string)self::meta($p->ID,'body')).'</div>';
        if ($source) {
            $html.='<p><a href="'.esc_url($source).'" rel="noopener noreferrer">Source and background</a></p>';
        }
        $html.='</details></article>';
        return $html;
    }

    public static function render($atts=array()) {
        // Reuse the reviewed institutional Press renderer from PR #24, not a second
        // public design or a substitute for the Media hub.
        $base=SC_Engagement_Bridge_882::render_press($atts);
        $items=get_posts(array('post_type'=>self::TYPE,'post_status'=>'private',
            'numberposts'=>30,'orderby'=>'date','order'=>'DESC',
            'meta_query'=>array(array('key'=>self::META.'state','value'=>'released'))));
        $archive='';
        foreach ($items as $p) { $archive.=self::public_item($p); }
        $archive=$archive ?: '<p>No approved public press releases are available yet.</p>';
        return $base.'<section class="scec-press scec-press-archive" aria-labelledby="scec-press-archive-title">'.
            '<div class="scec-press-section"><h2 id="scec-press-archive-title">Official releases &amp; announcements</h2>'.
            $archive.'</div></section>';
    }

    private static function form($action,$id,$label) {
        echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
        echo '<input type="hidden" name="action" value="'.esc_attr('scec08_'.$action).'">';
        echo '<input type="hidden" name="id" value="'.(int)$id.'">';
        wp_nonce_field('scec08_'.$action.'_'.$id);
        if ($action==='approve') {
            foreach (array('rights'=>'Rights and attribution','source'=>'Source integrity',
                'privacy'=>'Privacy/public suitability','institutional'=>'Institutional authority') as $check=>$name) {
                echo '<p><label><input type="checkbox" name="check_'.esc_attr($check).'" value="1" required> '.esc_html($name).' confirmed</label></p>';
            }
        }
        submit_button($label,'secondary','submit',true);
        echo '</form>';
    }

    public static function screen() {
        if (!current_user_can('manage_options')) { wp_die('Forbidden','',403); }
        $id=absint($_GET['id'] ?? 0);
        $p=self::post($id);
        $state=$p ? self::meta($id,'state','draft') : 'draft';
        $notice=sanitize_key((string)($_GET['notice'] ?? ''));
        echo '<div class="wrap"><h1>MEDIA-08 · Press Room</h1>';
        echo '<p>Private institutional releases. Public release is disabled by default, requires a separate administrator approval, a reviewed press page, and explicit deployment authorization.</p>';
        echo '<p><strong>Public release gate:</strong> '.(self::enabled()?'Enabled by configuration — verify independent approval':'OFF — private authoring only').'</p>';
        if ($notice) { echo '<div class="notice notice-info"><p>'.esc_html(str_replace('_',' ',$notice)).'</p></div>'; }
        echo '<p>For a dedicated public Press Room, create or verify a published WordPress page at <code>/press/</code> with <code>[sc_press_room]</code>. Existing <code>[sc_press]</code> still renders the Media hub for compatibility. Review Bluehost/SEO redirects before changing any page.</p>';
        echo '<h2>Press objects</h2><p><a class="button" href="'.esc_url(self::post_url(0)).'">New press release</a> ';
        echo '<a class="button" href="'.esc_url(admin_url('options-general.php?page=scec-media07')).'">Newsletter Studio</a></p>';
        $posts=get_posts(array('post_type'=>self::TYPE,'post_status'=>'private','numberposts'=>60,
            'orderby'=>'modified','order'=>'DESC'));
        echo '<table class="widefat striped"><thead><tr><th>Title</th><th>Kind</th><th>Editorial state</th></tr></thead><tbody>';
        foreach ($posts as $item) {
            echo '<tr><td><a href="'.esc_url(self::post_url($item->ID)).'">'.esc_html($item->post_title).'</a></td><td>'.
                esc_html(self::KINDS[self::meta($item->ID,'kind')] ?? '—').'</td><td>'.
                esc_html((string)self::meta($item->ID,'state','draft')).'</td></tr>';
        }
        echo '</tbody></table><h2>'.($p?'Review press record':'Create press draft').'</h2>';
        if ($p) { echo '<p><strong>Status:</strong> '.esc_html($state).' · Revision '.(int)self::meta($id,'revision',1).'</p>'; }
        if ($state==='draft') {
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
        } else {
            echo '<p><strong>Headline:</strong> '.esc_html($p->post_title).'</p><p>'.esc_html((string)self::meta($id,'summary')).'</p>';
            echo '<div style="max-width:760px;padding:20px;background:#fff;border:1px solid #ddd">'.wp_kses_post((string)self::meta($id,'body')).'</div>';
            if ($state==='in_review') { self::form('approve',$id,'Approve independently reviewed release'); }
            if ($state==='approved') { self::form('release',$id,'Release to public Press Room (feature-gated)'); }
            echo '<p>Changes to submitted content require a new release record/review. Editing approved revisions in place is blocked.</p>';
        }
        echo '</div>';
    }
}
