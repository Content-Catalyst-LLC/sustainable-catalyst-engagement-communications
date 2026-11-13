<?php
/* Synthetic WordPress integration tests for MEDIA-03: no production network access. */
define('MINUTE_IN_SECONDS', 60);
define('HOUR_IN_SECONDS', 3600);
define('DAY_IN_SECONDS', 86400);
$GLOBALS['sc_http_calls'] = array();
$GLOBALS['sc_transients'] = array();
$GLOBALS['sc_mock_http'] = 'ok';
function get_transient($key){return $GLOBALS['sc_transients'][$key]??false;}
function set_transient($key,$data,$ttl){$GLOBALS['sc_transients'][$key]=$data;$GLOBALS['sc_ttl'][$key]=$ttl;return true;}
function wp_safe_remote_get($url,$args){
    $GLOBALS['sc_http_calls'][]=array($url,$args);
    if ($GLOBALS['sc_mock_http'] === 'bad')return array('status'=>500,'body'=>'');
    if ($GLOBALS['sc_mock_http'] === 'doctype')return array('status'=>200,'body'=>'<!DOCTYPE foo><rss/>');
    if (strpos($url, '/xml/feeds/videos.xml')!==false)return array('status'=>200,'body'=>'YT_GOOD');
    if (strpos($url, 'www.youtube.com/feeds/')!==false)return array('status'=>404,'body'=>'');
    return array('status'=>200,'body'=>'RSS_GOOD');
}
function wp_remote_retrieve_response_code($res){return (int)($res['status']??0);}
function wp_remote_retrieve_body($res){return $res['body']??'';}
function wp_date($fmt,$ts){return gmdate($fmt,$ts);}
function get_posts($opts){
  $GLOBALS['sc_get_posts_opts']=$opts;
  return array(
   (object)array('post_status'=>'publish','slug'=>'public-note','password'=>false,'post_date_gmt'=>'2026-11-03 12:00:00','title'=>'A public <i>announcement</i>'),
   (object)array('post_status'=>'draft','slug'=>'internal-draft','password'=>false,'post_date_gmt'=>'2026-11-03 12:00:00','title'=>'DO NOT EXPOSE DRAFT'),
   (object)array('post_status'=>'publish','slug'=>'secret-note','password'=>true,'post_date_gmt'=>'2026-11-03 12:00:00','title'=>'DO NOT EXPOSE SECRET'),
  );
}
function get_the_title($post){return $post->title;}
class SC_XMLNode {
 private $text;private $attrs;
 function __construct($text,$attrs=array()){$this->text=$text;$this->attrs=$attrs;}
 function attributes(){return $this->attrs;}
 function __toString(){return $this->text;}
}
class SC_XMLItem {
 private $kind;private $title;private $url;private $video;private $channel;private $date;
 function __construct($kind,$title,$url,$date,$video='',$channel=''){$this->kind=$kind;$this->title=$title;$this->url=$url;$this->date=$date;$this->video=$video;$this->channel=$channel;}
 function xpath($expr){
   if(strpos($expr,'"title"')!==false)return array(new SC_XMLNode($this->title));
   if(strpos($expr,'"pubDate"')!==false)return array(new SC_XMLNode($this->date));
   if(strpos($expr,'"videoId"')!==false)return $this->video ? array(new SC_XMLNode($this->video)):array();
   if(strpos($expr,'"channelId"')!==false)return $this->channel ? array(new SC_XMLNode($this->channel)):array();
   if(strpos($expr,'"link"')!==false)return array(new SC_XMLNode($this->url));
   return array();
 }
}
class SC_XMLDoc {
 private $kind;
 function __construct($kind){$this->kind=$kind;}
 function getName(){return $this->kind==='yt'?'feed':'rss';}
 function xpath($expr){
   if($this->kind==='yt')return array(
     new SC_XMLItem('yt','YouTube research explainer','', '2026-11-04T12:00:00Z','dQw4w9WgXcQ','UCAAAAAAAAAAAAAAAAAAAAAA'),
     new SC_XMLItem('yt','Foreign channel item','', '2026-11-05T12:00:00Z','dQw4w9WgXcQ','UCBBBBBBBBBBBBBBBBBBBBBB'),
   );
   return array(
    new SC_XMLItem('rss','Climate & carbon review','https://newsletter.sustainablecatalyst.com/p/review','2026-11-05T12:00:00Z'),
    new SC_XMLItem('rss','PHISHING','https://phish.example/p/phishing','2026-11-05T12:00:00Z'),
    new SC_XMLItem('rss','Climate & carbon review','https://newsletter.sustainablecatalyst.com/p/review','2026-11-05T12:00:00Z'),
   );
 }
}
if(!function_exists('simplexml_load_string')){
  function simplexml_load_string($body,$cls,$options){return new SC_XMLDoc($body==='YT_GOOD'?'yt':'rss');}
}
require __DIR__.'/test-media02.php'; // Full MEDIA-02 regression suite.
$cls='SC_Engagement_Bridge_882';
function sc_expect($flag,$name){if(!$flag){fwrite(STDERR,"FAILED MEDIA-03: $name\n");exit(2);}echo "PASS MEDIA-03: $name\n";}
$defaults=$cls::media_defaults();
sc_expect($defaults['enable_discovery']==='0','discovery default off');
sc_expect($defaults['youtube_channel_id']==='' && $defaults['show_wp_updates']==='1','safe default source configuration');
$bad=$cls::sanitize_media_settings(array('youtube_channel_id'=>'http://evil.local','enable_discovery'=>'1','show_wp_updates'=>'1'));
sc_expect($bad['youtube_channel_id']==='' && $bad['enable_discovery']==='1','reject malformed channel ID');
$id='UC'.str_repeat('A',22);
$good=$cls::sanitize_media_settings(array('substack_url'=>'https://newsletter.sustainablecatalyst.com/','youtube_url'=>'https://www.youtube.com/@SustainableCatalyst','youtube_channel_id'=>$id,'show_feed'=>'1','enable_discovery'=>'1','show_wp_updates'=>'1'));
sc_expect($good['youtube_channel_id']===$id,'accept valid YouTube channel ID');
$GLOBALS['sc_options'][$cls::MEDIA_OPTION]=$good;
$GLOBALS['sc_http_calls']=array();$GLOBALS['sc_transients']=array();
$html=$cls::render_media();
sc_expect(str_contains($html,'Latest from our channels'),'stream section present');
sc_expect(str_contains($html,'Climate &amp; carbon review'),'Substack headline escaped');
sc_expect(str_contains($html,'YouTube research explainer'),'YouTube video present');
sc_expect(str_contains($html,'https://www.youtube.com/watch?v=dQw4w9WgXcQ'),'YouTube video deep link');
sc_expect(str_contains($html,'A public announcement'),'selected published WordPress note shown');
sc_expect(!str_contains($html,'PHISHING')&&!str_contains($html,'DO NOT EXPOSE'),'off-domain or unpublished items excluded');
sc_expect(substr_count($html,'Climate &amp; carbon review')===1,'duplicate Substack item collapsed');
sc_expect(strpos($html,'Climate &amp; carbon review') < strpos($html,'YouTube research explainer'),'sorted newest-first');
sc_expect(($GLOBALS['sc_get_posts_opts']['tag']??'')==='media-update' && ($GLOBALS['sc_get_posts_opts']['post_status']??'')==='publish','WordPress source strictly tagged and published');
sc_expect(count($GLOBALS['sc_http_calls'])===3,'two YouTube URLs attempted only on first fetch');
foreach($GLOBALS['sc_http_calls'] as $entry){
 sc_expect(($entry[1]['redirection']??null)===0 && ($entry[1]['timeout']??99)<=5 && ($entry[1]['limit_response_size']??999999)<=262144,'safe HTTP request limits');
}
$cached=count($GLOBALS['sc_http_calls']);$cls::render_media();
sc_expect(count($GLOBALS['sc_http_calls'])===$cached,'cache suppresses subsequent HTTP requests');
$ttl=array_values($GLOBALS['sc_ttl']);
sc_expect(in_array(3600,$ttl,true) && in_array(600,$ttl,true),'success and negative TTLs configured');
$GLOBALS['sc_options'][$cls::MEDIA_OPTION]=array_merge($good,array('enable_discovery'=>'0'));
$GLOBALS['sc_http_calls']=array();$no=$cls::render_media();
sc_expect(!str_contains($no,'Latest from our channels'),'discovery opt-out removes stream');
sc_expect(count($GLOBALS['sc_http_calls'])===0,'opt-out makes no MEDIA-03 HTTP requests');
$GLOBALS['sc_options'][$cls::MEDIA_OPTION]=array_merge($good,array('show_wp_updates'=>'0','youtube_channel_id'=>'','show_feed'=>'0'));
$GLOBALS['sc_http_calls']=array();$unconfigured=$cls::render_media();
sc_expect(str_contains($unconfigured,'No public updates are available'),'empty enabled sources degrade visibly without fabrication');
sc_expect(count($GLOBALS['sc_http_calls'])===0,'no external sources means no HTTP calls');
// Missing SimpleXML extension on this test runtime is mocked above; real WordPress XML parsing requires hosting extension.
echo "MEDIA-03 synthetic regression suite passed.\n";
