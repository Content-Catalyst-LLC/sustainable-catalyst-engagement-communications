<?php
/** Media-04 synthetic WordPress harness; no real WordPress, API or outbound requests. */
error_reporting(E_ALL);
set_error_handler(function($severity,$message){ if (error_reporting() & $severity) { throw new ErrorException($message,0,$severity); } return false; });
define('ABSPATH','/synthetic/');
define('SCEC_MEDIA05_ENABLED', true);
define('SCEC_MEDIA05_API_ORIGIN', 'https://media-api.sustainablecatalyst.com');
define('SCEC_MEDIA05_ORGANIZATION_ID', '00000000-0000-4000-8000-000000000001');
define('SCEC_MEDIA05_SERVICE_BEARER', 'synthetic.test.signed_token_not_a_real_secret_0123456789');
class SC_Engagement_Bridge_882 { const VERSION='8.8.9'; const MEDIA_OPTION='sc_ec_media_settings'; }
class WP_Error { public $message; public function __construct($msg){$this->message=$msg;} }
$GLOBALS['state_file'] = $argv[2] ?? tempnam(sys_get_temp_dir(),'scec-media05-');
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

function wp_http_validate_url($url){return strpos($url, 'https://media-api.sustainablecatalyst.com/')===0 ? $url : false;}
function update_option($key, $value, $autoload=false){$GLOBALS['state']['options'][$key]=$value;return true;}
function wp_safe_remote_get($url,$args){$GLOBALS['requests'][]=['method'=>'GET','url'=>$url,'args'=>$args];return $GLOBALS['mock_response'];}
function wp_safe_remote_post($url,$args){$GLOBALS['requests'][]=['method'=>'POST','url'=>$url,'args'=>$args];return $GLOBALS['mock_response'];}
function wp_remote_retrieve_response_code($resp){return (int)($resp['response']['code']??0);}
function wp_remote_retrieve_body($resp){return (string)($resp['body']??'');}

require dirname(__DIR__).'/sustainable-catalyst-engagement-communications/includes/media04-workflow.php';
require dirname(__DIR__).'/sustainable-catalyst-engagement-communications/includes/media05-bridge.php';
function ok($bool,$name){if(!$bool){fwrite(STDERR,"FAIL: $name\n");exit(2);}echo "PASS: $name\n";}
function mock_reply($payload, $code=200){$GLOBALS['mock_response']=['response'=>['code'=>$code], 'body'=>json_encode($payload)];}
$org=SCEC_MEDIA05_ORGANIZATION_ID;
$ready=SC_Media05_Bridge::readiness();
ok(count(array_filter($ready))===4,'All four config gates valid');
ok(SC_Media05_Bridge::approved_origin('http://media-api.sustainablecatalyst.com')==='', 'Reject HTTP destination');
ok(SC_Media05_Bridge::approved_origin('https://localhost')==='', 'Reject localhost');
ok(SC_Media05_Bridge::approved_origin('https://127.0.0.1')==='', 'Reject IP address');
ok(SC_Media05_Bridge::approved_origin('https://example.com:8443')==='', 'Reject custom port');
ok(SC_Media05_Bridge::approved_origin('https://good.example.com@evil.example')==='', 'Reject credentials');
ok(SC_Media05_Bridge::approved_origin('https://media-api.sustainablecatalyst.com/extra')==='', 'Reject unapproved path');
ok(SC_Media05_Bridge::approved_origin(SCEC_MEDIA05_API_ORIGIN)==='https://media-api.sustainablecatalyst.com','Pinned HTTPS origin');
$source=get_post(10);
$package_id=wp_insert_post(['post_type'=>SC_Media04_Workflow::POST_TYPE,'post_status'=>'private','post_title'=>'Synthetic field report','post_author'=>1]);
$k='_scec_media04_';
update_post_meta($package_id,$k.'summary','Public factual summary');
update_post_meta($package_id,$k.'source_url',$source->permalink);
update_post_meta($package_id,$k.'channels',['substack','linkedin']);
update_post_meta($package_id,$k.'stage','approved');
update_post_meta($package_id,$k.'approved_utc','2026-11-08T00:10:00+00:00');
$package=get_post($package_id);
update_post_meta($package_id,$k.'approved_hash',SC_Media04_Workflow::fingerprint($package));
$envelope=SC_Media05_Bridge::envelope($package);
ok(is_array($envelope) && $envelope['package_ref']==='wp-media:'.$package_id,'Approved package only produces envelope');
ok($envelope['channels']===['substack','linkedin'],'Channel choices retained');
ok(!isset($envelope['summary'])&&!isset($envelope['copy_ready_messages'])&&!isset($envelope['subscribers']),'Minimal metadata only');
ok($envelope['source_content_sha256']===hash('sha256',$source->ID."\n".$source->post_title."\n".$source->post_content."\n".$source->post_modified_gmt),'Source hash matches MEDIA-04 definition');
$GLOBALS['requests']=[];
mock_reply(['release'=>'MEDIA-05','organization_id'=>$org,'mode'=>'private-metadata-preview','publishing_enabled'=>false,'sending_enabled'=>false,'persistence_enabled'=>false,'production_certified'=>false]);
$status=SC_Media05_Bridge::request_backend('status');
ok($status['ok']===true,'Accept bounded read-only backend status');
ok($GLOBALS['requests'][0]['method']==='GET'&&$GLOBALS['requests'][0]['url']==='https://media-api.sustainablecatalyst.com/v1/media-bridge/status','Status uses approved endpoint');
ok($GLOBALS['requests'][0]['args']['redirection']===0 && $GLOBALS['requests'][0]['args']['sslverify']===true && $GLOBALS['requests'][0]['args']['reject_unsafe_urls']===true,'Fail closed redirects and TLS');
ok($GLOBALS['requests'][0]['args']['headers']['Authorization']==='Bearer '.SCEC_MEDIA05_SERVICE_BEARER,'Server-side bearer passed only via request header');
mock_reply(['release'=>'MEDIA-05','organization_id'=>$org,'mode'=>'private-metadata-preview','publishing_enabled'=>true,'sending_enabled'=>false,'persistence_enabled'=>false,'production_certified'=>false]);
ok(SC_Media05_Bridge::request_backend('status')['ok']===false,'Reject unsafe backend publishing claim');
mock_reply(['release'=>'MEDIA-05','organization_id'=>'00000000-0000-4000-8000-000000000002','publishing_enabled'=>false,'sending_enabled'=>false,'persistence_enabled'=>false,'production_certified'=>false]);
ok(SC_Media05_Bridge::request_backend('status')['ok']===false,'Reject tenant mismatch');
mock_reply(['release'=>'MEDIA-05','organization_id'=>$org,'package_ref'=>$envelope['package_ref'],'approved_package_sha256'=>$envelope['approved_package_sha256'],'receipt_sha256'=>str_repeat('a',64),'preview_only'=>true,'delivery_enabled'=>false,'auto_post_enabled'=>false,'persistence_enabled'=>false]);
$preview=SC_Media05_Bridge::request_backend('preview',$envelope);
ok($preview['ok']===true,'Accept safe nonpublishing preview');
$last=end($GLOBALS['requests']);
ok($last['method']==='POST'&&$last['url']==='https://media-api.sustainablecatalyst.com/v1/media-bridge/preview','Preview posts only to private backend');
$sent=json_decode($last['args']['body'],true);
ok($sent['export_mode']==='metadata_preview_only'&&!isset($sent['password'])&&!isset($sent['message_body']),'No private content or credentials in request body');
mock_reply(['release'=>'MEDIA-05','organization_id'=>$org,'package_ref'=>$envelope['package_ref'],'approved_package_sha256'=>$envelope['approved_package_sha256'],'receipt_sha256'=>str_repeat('a',64),'preview_only'=>true,'delivery_enabled'=>true,'auto_post_enabled'=>false,'persistence_enabled'=>false]);
ok(SC_Media05_Bridge::request_backend('preview',$envelope)['ok']===false,'Reject unsafe delivery backend');
mock_reply(['release'=>'MEDIA-05','organization_id'=>$org,'package_ref'=>$envelope['package_ref'],'approved_package_sha256'=>str_repeat('0',64),'receipt_sha256'=>str_repeat('a',64),'preview_only'=>true,'delivery_enabled'=>false,'auto_post_enabled'=>false,'persistence_enabled'=>false]);
ok(SC_Media05_Bridge::request_backend('preview',$envelope)['ok']===false,'Reject stale approval hash reply');
mock_reply(['release'=>'MEDIA-05','organization_id'=>$org],307);
ok(SC_Media05_Bridge::request_backend('status')['ok']===false,'Never follow backend redirect');
update_post_meta(10,'_test_change','x');
$GLOBALS['state']['posts']['10']['post_content']='revised source';
ok(SC_Media05_Bridge::envelope($package)===null,'Changed source invalidates approval and blocks transfer');
$GLOBALS['state']['posts']['10']['post_status']='private';
ok(SC_Media05_Bridge::envelope($package)===null,'Private source blocks transfer');
ok(SC_Media05_Bridge::envelope(null)===null,'No package cannot transmit');
echo "MEDIA-05 WordPress suite passed.\n";
