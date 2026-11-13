<?php
/* Synthetic WordPress smoke tests; does not exercise a live WordPress install. */
error_reporting(E_ALL);
ini_set('assert.exception','1');
define('ABSPATH', '/tmp/');
define('OBJECT', 'OBJECT');
$GLOBALS['sc_shortcodes']=array();
$GLOBALS['sc_options']=array();
$GLOBALS['sc_styles']=array();
$GLOBALS['sc_scripts']=array();
function add_action($hook,$callback){}
function add_shortcode($tag,$cb){$GLOBALS['sc_shortcodes'][$tag]=$cb;}
function wp_register_style($handle,$url,$deps,$ver){$GLOBALS['sc_styles'][$handle]=$url;}
function wp_register_script($handle,$url,$deps,$ver,$footer){$GLOBALS['sc_scripts'][$handle]=$url;}
function plugins_url($file,$base){return 'https://sustainablecatalyst.com/wp-content/plugins/engagement/'.$file;}
function wp_style_is($name,$status){return isset($GLOBALS['sc_styles'][$name]);}
function wp_enqueue_style($handle){}
function wp_enqueue_script($handle){$GLOBALS['sc_script_enqueued']=$handle;}
function get_option($name,$default=''){return $GLOBALS['sc_options'][$name]??$default;}
function wp_parse_url($value,$component=-1){return $component===-1?parse_url($value):parse_url($value,$component);}
function esc_url_raw($s){return filter_var($s,FILTER_SANITIZE_URL);}
function wp_http_validate_url($s){$u=parse_url($s);return ($u && ($u['scheme']??'')==='https' && !in_array($u['host']??'',array('127.0.0.1','localhost'),true))?$s:false;}
function esc_url($s){return htmlspecialchars((string)$s,ENT_QUOTES);}
function esc_html($s){return htmlspecialchars((string)$s,ENT_QUOTES);}
function esc_attr($s){return htmlspecialchars((string)$s,ENT_QUOTES);}
function wp_strip_all_tags($s){return strip_tags($s);}
function is_wp_error($s){return $s instanceof SC_Test_Error;}
function checked($a,$b,$echo=false){return (string)$a === (string)$b?'checked="checked"':'';}
function add_settings_error($option,$code,$message){$GLOBALS['sc_errors'][]=$code;}
function register_setting($group,$name,$opts){}
function add_settings_section($id,$label,$fn,$screen){}
function add_settings_field($id,$label,$cb,$screen,$section){}
function get_page_by_path($slug,$a,$b){
 if (isset($GLOBALS['sc_pages'][$slug]))return $GLOBALS['sc_pages'][$slug];
 if ($slug==='contact')return (object)array('post_status'=>'publish','slug'=>'contact','password'=>false);
 if ($slug==='press-releases')return (object)array('post_status'=>'draft','slug'=>'press-releases','password'=>false);
 if ($slug==='events')return (object)array('post_status'=>'publish','slug'=>'events','password'=>true);
 return null;
}
function post_password_required($page){return $page->password;}
function get_permalink($page){return $page->permalink ?? 'https://sustainablecatalyst.com/'.$page->slug.'/';}
function home_url($path='/'){return ($GLOBALS['sc_home_url']??'https://sustainablecatalyst.com/');}
function has_shortcode($content,$tag){return str_contains($content, '['.$tag.']');}
function is_admin(){return $GLOBALS['sc_is_admin']??false;}
function is_preview(){return $GLOBALS['sc_is_preview']??false;}
function wp_doing_ajax(){return $GLOBALS['sc_is_ajax']??false;}
function wp_safe_redirect($url,$code,$who){$GLOBALS['sc_redirects'][]=array($url,$code,$who);return false;}

class SC_Test_Error{}
class SC_Test_Item{private $link;private $title;function __construct($link,$title){$this->link=$link;$this->title=$title;}function get_permalink(){return $this->link;}function get_title(){return $this->title;}}
class SC_Test_Feed{function get_items($start,$count){return array(
 new SC_Test_Item('https://newsletter.sustainablecatalyst.com/p/latest','Research <b>update</b>'),
 new SC_Test_Item('https://danger.example.org/phishing','Offsite injection'),
 new SC_Test_Item('https://newsletter.sustainablecatalyst.com/p/next','Second edition')
 );}}
function fetch_feed($u){$GLOBALS['sc_feed_fetch_url']=$u;return new SC_Test_Feed;}
function expect($flag,$label){if(!$flag){fwrite(STDERR,'FAIL: '.$label."\n");exit(1);}echo 'PASS: '.$label."\n";}
require __DIR__.'/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php';
$all=array_keys($GLOBALS['sc_shortcodes']);
foreach(array('sc_media','sc_press','sc_engagement_communications','sc_engagement_public_links','sc_engagement_launch') as $name){expect(in_array($name,$all,true),'registered '.$name);}
$cls='SC_Engagement_Bridge_882';
$render=$GLOBALS['sc_shortcodes']['sc_media'];
$html=call_user_func($render);
expect(str_contains($html,'Media<span class="scec-media-red">.</span>'),'Media headline');
expect(str_contains($html,'https://newsletter.sustainablecatalyst.com/subscribe'),'Substack subscribe link');
expect(str_contains($html,'https://www.youtube.com/@SustainableCatalyst'),'YouTube channel link');
expect(str_contains($html,'id="scec-media-linkedin"') && str_contains($html,'id="scec-media-socials"'),'dedicated LinkedIn and social channels sections');
expect(!str_contains($html,'Connect on LinkedIn'),'unconfigured LinkedIn has no fabricated link');
expect(str_contains($html,'data-scec-kind="substack"'),'click-to-load Substack form');
expect(str_contains($html,'Research update')&&!str_contains($html,'<b>update</b>'),'escaped RSS title');
expect(!str_contains($html,'danger.example.org'),'feed suppresses off-domain links');
expect(!str_contains($html,'/press-releases/'),'draft press content suppressed');
expect(!str_contains($html,'/events/'),'password-protected events suppressed');
expect(str_contains($html,'https://sustainablecatalyst.com/contact/'),'approved contact link');
expect($GLOBALS['sc_script_enqueued']==='sc-ec-media','load script for deferred embeds');
expect($GLOBALS['sc_feed_fetch_url']==='https://newsletter.sustainablecatalyst.com/feed','fetch Substack feed from official domain');
expect(call_user_func($GLOBALS['sc_shortcodes']['sc_press'])===$html,'legacy sc_press aliases Media');
$fn = new ReflectionMethod($cls,'video_embed_url');$fn->setAccessible(true);
expect($fn->invoke(null,'https://www.youtube.com/watch?v=dQw4w9WgXcQ')==='https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ','privacy-enhanced YouTube video URL');
expect($fn->invoke(null,'https://evil.example.org/watch?v=dQw4w9WgXcQ')==='','reject malicious video host');
expect($fn->invoke(null,'http://www.youtube.com/watch?v=dQw4w9WgXcQ')==='','reject insecure video URL');
expect($fn->invoke(null,'https://www.youtube.com/playlist?list=PL123456789ABC')==='https://www.youtube-nocookie.com/embed/videoseries?list=PL123456789ABC','supported YouTube playlist');
$validated=$cls::sanitize_media_settings(array('substack_url'=>'http://localhost','youtube_url'=>'https://evil.example.org/@fake','featured_video_url'=>'https://evil.example.org/video','show_feed'=>'0'));
expect($validated['substack_url']==='' && $validated['youtube_url']==='' && $validated['featured_video_url']==='','invalid media settings rejected');
expect($validated['show_feed']==='0'&&$validated['show_subscribe_embed']==='0','checkbox off state preserved');

$profiles=array(
  'linkedin_url'=>'https://www.linkedin.com/company/sustainable-catalyst/',
  'social_x_url'=>'https://x.com/SustCatalyst',
  'social_instagram_url'=>'https://www.instagram.com/sustainablecatalyst/',
  'social_facebook_url'=>'https://www.facebook.com/sustainablecatalyst',
  'social_threads_url'=>'https://www.threads.net/@sustainablecatalyst',
  'social_bluesky_url'=>'https://bsky.app/profile/sustainablecatalyst.bsky.social',
  'social_mastodon_url'=>'https://mastodon.social/@sustainablecatalyst',
  'social_github_url'=>'https://github.com/Content-Catalyst-LLC',
  'social_tiktok_url'=>'https://www.tiktok.com/@sustainablecatalyst'
);
$accepted=$cls::sanitize_media_settings(array_merge(array('substack_url'=>'', 'youtube_url'=>''), $profiles));
foreach($profiles as $key=>$link){expect(($accepted[$key]??'')===rtrim($link,'/'), 'accepted valid public '.$key);}
$GLOBALS['sc_options'][$cls::MEDIA_OPTION]=array_merge($accepted,array('show_feed'=>'0', 'show_subscribe_embed'=>'0'));
$with_socials=call_user_func($render);
expect(str_contains($with_socials,'Connect on LinkedIn') && str_contains($with_socials,'https://www.linkedin.com/company/sustainable-catalyst'), 'LinkedIn call to action links to configured page');
expect(str_contains($with_socials,'Follow Sustainable Catalyst') && str_contains($with_socials,'Visit channel'), 'social links rendered');
foreach(array('X / Twitter', 'Instagram', 'Facebook', 'Threads', 'Bluesky', 'Mastodon', 'GitHub', 'TikTok') as $channel){expect(str_contains($with_socials,'>'.$channel.'</strong>'),'linked '.$channel);}
$bad=$cls::sanitize_media_settings(array('linkedin_url'=>'https://linkedin.com.evil.example/company/foo','social_x_url'=>'https://x.com.evil.example/handle','social_mastodon_url'=>'https://localhost/@user','social_github_url'=>'javascript:alert(1)','social_instagram_url'=>'https://instagram.com/p/malicious'));
expect($bad['linkedin_url']==='' && $bad['social_x_url']==='' && $bad['social_mastodon_url']==='' && $bad['social_github_url']==='' && $bad['social_instagram_url']==='', 'invalid or deceptive social URLs blocked');
$GLOBALS['sc_options'][$cls::MEDIA_OPTION]=array('linkedin_url'=>'','social_github_url'=>'','show_feed'=>'0','show_subscribe_embed'=>'0');
$blank=call_user_func($render);
expect(!str_contains($blank,'scec-media-social-link') && !str_contains($blank,'Connect on LinkedIn'), 'empty social channels show no active links');

$GLOBALS['sc_options'][$cls::MEDIA_OPTION]=array('substack_url'=>'','youtube_url'=>'','featured_video_url'=>'','show_feed'=>'0','show_subscribe_embed'=>'0');
$off=call_user_func($render);
expect(!str_contains($off,'data-scec-kind="substack"')&&!str_contains($off,'data-scec-kind="youtube"'),'no third-party embeds without config');
expect(str_contains($off,'not been configured'),'graceful unconfigured state');
echo "Synthetic smoke test suite passed.\n";

// MEDIA-02 acceptance fixtures: verify fail-closed readiness and safe 301 opt-in.
$media=(object)array('post_status'=>'publish','slug'=>'media','password'=>false,'post_content'=>'[sc_media]');
$GLOBALS['sc_pages']['media']=$media;
$GLOBALS['sc_options'][$cls::REDIRECT_OPTION]='0';
$checks=$cls::media_readiness_checks();
expect($checks['media_public'] && $checks['shortcode'] && $checks['same_site_url'], 'published /media/ page and shortcode detected');
expect($checks['press_clear'] && $checks['channel_clear'], 'no existing legacy pages collide');
expect(!$checks['redirect_opt_in'], 'legacy redirects OFF by default');
ob_start();$cls::field_media_redirect();$redirect_input=ob_get_clean();
expect(str_contains($redirect_input,'type="hidden"') && str_contains($redirect_input,'value="0"'), 'unchecked redirect setting can be disabled again');
expect($cls::sanitize_media_redirect_option('true')==='0' && $cls::sanitize_media_redirect_option('1')==='1', 'redirect option accepts only explicit 1');
$_SERVER['REQUEST_METHOD']='GET'; $_SERVER['REQUEST_URI']='/channel/';
$GLOBALS['sc_redirects']=array();
$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===0, 'disabled redirect sends nothing');
$GLOBALS['sc_options'][$cls::REDIRECT_OPTION]='1';
$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===1 && $GLOBALS['sc_redirects'][0][0]==='https://sustainablecatalyst.com/media/' && $GLOBALS['sc_redirects'][0][1]===301, 'enabled redirect uses canonical same-site 301');
foreach(array('/channel-notes/','/blog/press/','/media/','/press/page/2/','/press/?foo=bar','/channel/%2fother/') as $request){
  $_SERVER['REQUEST_URI']=$request; $GLOBALS['sc_redirects']=array(); $cls::maybe_legacy_media_redirect();
  expect(count($GLOBALS['sc_redirects'])===0,'unrelated/unsafe path left alone: '.$request);
}
$_SERVER['REQUEST_URI']='/press/';
foreach(array('POST','PUT') as $method){$_SERVER['REQUEST_METHOD']=$method;$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();expect(count($GLOBALS['sc_redirects'])===0,'non-idempotent method '.$method.' unaffected');}
$_SERVER['REQUEST_METHOD']='HEAD'; $GLOBALS['sc_redirects']=array(); $cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===1,'HEAD redirect allowed');
$_SERVER['REQUEST_METHOD']='GET';
foreach(array('sc_is_admin','sc_is_preview','sc_is_ajax') as $gate){$GLOBALS[$gate]=true;$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();expect(count($GLOBALS['sc_redirects'])===0,$gate.' bypasses redirects');$GLOBALS[$gate]=false;}
$GLOBALS['sc_pages']['press']=(object)array('post_status'=>'publish','slug'=>'press','password'=>false,'post_content'=>'Original');
$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===0,'existing Press page is never hijacked');
unset($GLOBALS['sc_pages']['press']);
$media->post_content='[some_other_shortcode]';$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===0,'missing Media shortcode disables redirect');
$media->post_content='[sc_press]';$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===1,'legacy shortcode remains compatible as target');
$media->password=true;$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===0,'password-protected Media disables redirect');
$media->password=false; $media->post_status='draft';$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===0,'unpublished Media disables redirect');
$media->post_status='publish';$media->post_content='[sc_media]';
$media->permalink='https://malicious.example/media/';$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===0,'external Media permalink disables redirect');
unset($media->permalink);
$GLOBALS['sc_home_url']='https://sustainablecatalyst.com/site/';
$media->permalink='https://sustainablecatalyst.com/site/media/';
$_SERVER['REQUEST_URI']='/site/channel/';$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===1 && $GLOBALS['sc_redirects'][0][0]==='https://sustainablecatalyst.com/site/media/','subdirectory WordPress install supported');
$_SERVER['REQUEST_URI']='/channel/';$GLOBALS['sc_redirects']=array();$cls::maybe_legacy_media_redirect();
expect(count($GLOBALS['sc_redirects'])===0,'subdirectory does not hijack site-root path');
ob_start();$cls::render_media_readiness_admin();$diagnostics=ob_get_clean();
expect(str_contains($diagnostics,'MEDIA-02') && str_contains($diagnostics,'Launch readiness') && str_contains($diagnostics,'shortcode'), 'admin readiness screen renders');
$GLOBALS['sc_pages']['channel']=(object)array('post_status'=>'draft','slug'=>'channel','password'=>false,'post_content'=>'Old channel');
$checks=$cls::media_readiness_checks();
expect(!$checks['channel_clear'],'even unpublished legacy page is preserved');
expect(count($GLOBALS['sc_redirects'])===0,'redirect cache remains clean');
echo "MEDIA-02 acceptance suite passed.\n";
