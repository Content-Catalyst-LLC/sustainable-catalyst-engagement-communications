<?php
/** Media-04 synthetic WordPress harness; no real WordPress, API or outbound requests. */
error_reporting(E_ALL);
set_error_handler(function($severity,$message){ if (error_reporting() & $severity) { throw new ErrorException($message,0,$severity); } return false; });
define('ABSPATH','/synthetic/');
class SC_Engagement_Bridge_882 { const VERSION='8.8.8'; const MEDIA_OPTION='sc_ec_media_settings'; }
class WP_Error { public $message; public function __construct($msg){$this->message=$msg;} }
$GLOBALS['state_file'] = $argv[2] ?? '/tmp/sc_media04_test.json';
$GLOBALS['state'] = file_exists($GLOBALS['state_file']) ? json_decode(file_get_contents($GLOBALS['state_file']),true) : array();
if (!$GLOBALS['state']) {
 $GLOBALS['state'] = array('next_id'=>100, 'posts'=>array(
   '10'=>array('ID'=>10,'post_type'=>'post','post_status'=>'publish','post_title'=>'Public source','post_content'=>'Original science','post_modified_gmt'=>'2026-11-08 05:00:00','post_password'=>'', 'post_author'=>2,'permalink'=>'https://sustainablecatalyst.com/verified-study/'),
   '11'=>array('ID'=>11,'post_type'=>'post','post_status'=>'private','post_title'=>'Unreleased paper','post_content'=>'Private','post_modified_gmt'=>'2026-11-08 05:00:00','post_password'=>'', 'post_author'=>2,'permalink'=>'https://sustainablecatalyst.com/private/'),
   '12'=>array('ID'=>12,'post_type'=>'page','post_status'=>'publish','post_title'=>'Protected page','post_content'=>'Private','post_modified_gmt'=>'2026-11-08 05:00:00','post_password'=>'secret', 'post_author'=>2,'permalink'=>'https://sustainablecatalyst.com/password/'),
  ),'meta'=>array(),'options'=>array('sc_ec_media_settings'=>array('substack_url'=>'https://newsletter.sustainablecatalyst.com/')),'tags'=>array(), 'user'=>1,'allowed'=>true, 'redirect'=>null);
}
register_shutdown_function(function(){ file_put_contents($GLOBALS['state_file'],json_encode($GLOBALS['state'],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)); });
function add_action(...$args){}
function register_post_type($name,$args){$GLOBALS['post_type_def']=$args;}
function add_submenu_page(...$args){}
function wp_enqueue_style(...$args){}
function wp_enqueue_script(...$args){}
function plugins_url($url,$file){return 'https://sustainablecatalyst.com/wp-content/plugins/sc/'.ltrim($url,'/');}
function current_user_can($cap){return !empty($GLOBALS['state']['allowed']) && $cap==='manage_options';}
function get_current_user_id(){return $GLOBALS['state']['user'];}
function wp_parse_url($url,$component=-1){return parse_url($url,$component);}
function home_url($path='/'){return 'https://sustainablecatalyst.com'.($path[0]=='/'?'':'/').$path;}
function url_to_postid($url){foreach($GLOBALS['state']['posts'] as $p){if(rtrim($p['permalink']??'', '/')===rtrim($url,'/'))return (int)$p['ID'];}return 0;}
function get_post($id){return isset($GLOBALS['state']['posts'][(string)$id])?(object)$GLOBALS['state']['posts'][(string)$id]:null;}
function get_permalink($post){$id=is_object($post)?$post->ID:$post;return $GLOBALS['state']['posts'][(string)$id]['permalink']??false;}
function post_password_required($post){return !empty($post->post_password);}
function get_post_meta($id,$key,$single=true){return $GLOBALS['state']['meta'][(string)$id][$key]??'';}
function update_post_meta($id,$key,$val){$GLOBALS['state']['meta'][(string)$id][$key]=$val;return true;}
function get_option($key,$fallback=null){return $GLOBALS['state']['options'][$key]??$fallback;}
function wp_insert_post($data,$wp_error=false){
  if(!empty($GLOBALS['state']['insert_error']))return new WP_Error('failed');
  $id=++$GLOBALS['state']['next_id'];
  $GLOBALS['state']['posts'][(string)$id]=array_merge(array('ID'=>$id,'post_type'=>'post','post_status'=>'draft','post_title'=>'','post_content'=>'','post_modified_gmt'=>'2026-11-08 05:00:00','post_password'=>'','permalink'=>'https://sustainablecatalyst.com/post-'.$id.'/'),$data);
  return $id;
}
function wp_update_post($data,$err=false){$id=$data['ID'];if(!isset($GLOBALS['state']['posts'][(string)$id]))return new WP_Error('notfound');$GLOBALS['state']['posts'][(string)$id]=array_merge($GLOBALS['state']['posts'][(string)$id],$data);return $id;}
function wp_set_post_tags($id,$tags,$append=false){$GLOBALS['state']['tags'][(string)$id]=$tags;return $tags;}
function is_wp_error($v){return $v instanceof WP_Error;}
function admin_url($path=''){return 'https://sustainablecatalyst.com/wp-admin/'.$path;}
function add_query_arg($args,$url){return $url.'?'.http_build_query($args);}
function wp_safe_redirect($url){$GLOBALS['state']['redirect']=$url;}
function wp_die($message,$title='',$status=400){$GLOBALS['state']['error']=$message;$GLOBALS['state']['error_status']=$status;exit(1);}
function check_admin_referer($action){if(($_POST['_wpnonce']??'')!=='signed-'.$action)wp_die('Nonce mismatch','',403);}
function sanitize_key($str){return preg_replace('/[^a-z0-9_-]/','',strtolower((string)$str));}
function absint($x){return abs((int)$x);}
function sanitize_text_field($s){return trim(strip_tags((string)$s));}
function sanitize_textarea_field($s){return trim(strip_tags((string)$s));}
function esc_url_raw($url){return trim((string)$url);}
function wp_unslash($value){return $value;}
function wp_json_encode($value,$flags=0){return json_encode($value,$flags);}
function esc_html($v){return htmlspecialchars((string)$v,ENT_QUOTES,'UTF-8');}
function esc_attr($v){return esc_html($v);}
function esc_url($v){return esc_html($v);}
function esc_textarea($v){return esc_html($v);}
function checked($a,$b,$echo=true){return $a===$b?'checked="checked"':'';}
function wp_nonce_field($action){echo '<input type="hidden" name="_wpnonce" value="signed-'.$action.'">';}
function get_edit_post_link($id){return admin_url('post.php?post='.$id.'&action=edit');}
function get_posts($args){$r=array();foreach($GLOBALS['state']['posts'] as $p){if($p['post_type']===$args['post_type']&&$p['post_status']===$args['post_status'])$r[]=(object)$p;}return $r;}
function nocache_headers(){}
require dirname(__DIR__).'/sustainable-catalyst-engagement-communications/includes/media04-workflow.php';
function ok($condition,$msg){if(!$condition){fwrite(STDERR,"FAIL: $msg\n");exit(2);}echo "PASS: $msg\n";}
$mode=$argv[1]??'unit';
if($mode==='unit'){
 SC_Media04_Workflow::register_type();
 $r=$GLOBALS['post_type_def'];
 ok($r['public']===false&&$r['publicly_queryable']===false&&$r['show_in_rest']===false,'Private, non-REST package type');
 ok($r['capabilities']['edit_posts']==='manage_options','Admin-only object editing');
 ok(SC_Media04_Workflow::source_post('https://sustainablecatalyst.com/verified-study/')->ID===10,'Accept canonical published post');
 ok(SC_Media04_Workflow::source_post('https://sustainablecatalyst.com/private/')===null,'Reject private source');
 ok(SC_Media04_Workflow::source_post('https://sustainablecatalyst.com/password/')===null,'Reject password-protected source');
 ok(SC_Media04_Workflow::source_post('https://evil.example/verified-study/')===null,'Reject external source');
 ok(SC_Media04_Workflow::source_post('http://sustainablecatalyst.com/verified-study/')===null,'Reject HTTP source');
 ok(SC_Media04_Workflow::source_post('https://sustainablecatalyst.com/verified-study/?secret=1')===null,'Reject query source');
 ok(SC_Media04_Workflow::channels(array('x','unknown','linkedin','x'))===array('linkedin','x'),'Allowlisted stable deduplicated channels');
 ok(SC_Media04_Workflow::external_url('https://www.linkedin.com/feed/update/urn:li:activity:12345','linkedin'),'Accept LinkedIn publication URL');
 ok(!SC_Media04_Workflow::external_url('http://www.linkedin.com/feed/update/123','linkedin'),'Reject HTTP external URL');
 ok(!SC_Media04_Workflow::external_url('https://localhost/foo','mastodon'),'Reject localhost federated URL');
 ok(!SC_Media04_Workflow::external_url('https://evil.com/foo','linkedin'),'Reject unrelated host');
 ok(SC_Media04_Workflow::external_url('https://newsletter.sustainablecatalyst.com/p/public-piece','substack'),'Accept configured Substack publication');
 ok(!SC_Media04_Workflow::external_url('https://different.substack.com/p/something','substack'),'Reject other Substack publication');
 ok(!SC_Media04_Workflow::external_url('https://www.linkedin.com/','linkedin'),'Reject profile root as publication');
 echo "UNIT PASS\n";
 exit;
}
if($mode==='action'){
 $payload=json_decode(file_get_contents('php://stdin'),true);
 $_POST=$payload['post']??array();
 $_SERVER['REQUEST_METHOD']=$payload['method']??'POST';
 $GLOBALS['state']['user']=$payload['user']??$GLOBALS['state']['user'];
 $GLOBALS['state']['allowed']=$payload['allowed']??true;
 $GLOBALS['state']['redirect']=null;
 $GLOBALS['state']['error']=null;
 SC_Media04_Workflow::handle_action();
 exit;
}
if($mode==='inspect'){
 $id=(int)($argv[3]??0);
 $p=SC_Media04_Workflow::get_package($id);
 if(!$p){echo "NOT_FOUND\n";exit;}
 $status=get_post_meta($id,'_scec_media04_stage',true);
 $valid=SC_Media04_Workflow::approved($p)?'1':'0';
 echo json_encode(array('id'=>$id,'status'=>$status,'valid'=>$valid,'fingerprint'=>SC_Media04_Workflow::fingerprint($p),'messages'=>SC_Media04_Workflow::messages($p)));
 exit;
}
