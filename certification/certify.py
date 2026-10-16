#!/usr/bin/env python3
"""Non-mutating v8.9.0 certification. Never handles keys or customer data."""
import argparse, json, os, re, subprocess, sys, urllib.error, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def check_source():
    data={}
    manifest=json.loads((ROOT/'RELEASE-MANIFEST.json').read_text())
    data['release_manifest_890']=manifest.get('version') in ('8.9.0','9.0.0','9.1.0','9.2.0','9.3.0','9.4.0','9.5.0','9.6.0','9.7.0','9.8.0','9.9.0','10.0.0','10.1.0','10.2.0','10.3.0')
    data['database_contract_unchanged']=manifest.get('schema_revision')=='850_001'
    data['writes_disabled_contract']=manifest.get('production_writes_default')=='disabled'
    data['independent_web_present']=all((ROOT/p).exists() for p in ('frontend/index.html','frontend/compose.yaml','frontend/nginx.conf'))
    data['web_local_only_compose']='127.0.0.1:8097:80' in (ROOT/'frontend/compose.yaml').read_text()
    html=(ROOT/'frontend/index.html').read_text()
    data['read_only_web_disclosure']='READ-ONLY PREVIEW' in html and 'NOT LIVE RECORDS' in html
    nginx=(ROOT/'frontend/nginx.conf').read_text()
    data['security_headers']='X-Frame-Options DENY' in nginx and 'Content-Security-Policy' in nginx and "connect-src 'none'" in nginx
    plugin=(ROOT/'wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php').read_text()
    data['wordpress_bridge_present']='sc_engagement_communications' in plugin
    data['wordpress_five_existing_links']=all("array('"+label+"'," in plugin for label in ['Contact','Feedback','Feature Suggestions','Channel','Support'])
    data['wordpress_no_forms_or_redirects']=not any(x in plugin for x in ['wp_insert_post(', 'wp_delete_post(', 'wp_redirect(', 'wp_remote_post('])
    return data

def http_get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SCEC-certification/8.9.0'}),timeout=5) as res:
            return res.status,res.read(65536).decode('utf-8','replace')
    except urllib.error.HTTPError as err:
        return err.code,''
    except Exception:
        return None,''

def check_live():
    data={}
    web='http://127.0.0.1:8097'
    backend='http://127.0.0.1:8816'
    status,body=http_get(web+'/healthz')
    data['web_healthz']=status==200 and body.strip()=='ok'
    status,body=http_get(web+'/')
    data['web_serves_870_shell']=status==200 and 'RELEASE 8.7.0' in body
    status,body=http_get(backend+'/health')
    try: obj=json.loads(body)
    except ValueError: obj={}
    data['backend_860_health']=status==200 and obj.get('version')=='8.6.0' and obj.get('status')=='ok'
    status,_=http_get(backend+'/v1/contracts/canonical')
    data['unauthenticated_rejected']=status==401
    data['web_port_bound_loopback']=False
    try:
        result=subprocess.run(['docker','inspect','--format','{{json .NetworkSettings.Ports}}','scec-engagement-web-v870'],capture_output=True,text=True,timeout=5)
        data['web_port_bound_loopback']=result.returncode==0 and '127.0.0.1' in result.stdout and '8097' in result.stdout
    except Exception: pass
    return data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='Read-only checks against local Contabo ports; no public network exposure')
    parser.add_argument('--json-out',help='Optional report destination')
    args=parser.parse_args()
    source=check_source(); live=check_live() if args.live else {}
    # Public HTTPS, browser acceptance, identity brokering and tenant-scope tests require separate evidence.
    pending=['public_https_dns_tls','wordpress_public_launcher_acceptance','authenticated_human_session','csrf_revocation_session_expiry','live_tenant_isolation_roles','privacy_retention_policy','staged_persistence_write_certification']
    passed=all(source.values()) and (not args.live or all(live.values()))
    report={'release':json.loads((ROOT/'RELEASE-MANIFEST.json').read_text())['version'],'source_checks':source,'live_checks':live,'gates_not_certified':pending,'preflight':'PASS' if passed else 'FAIL','production_certified':False,'production_writes_enabled':False}
    encoded=json.dumps(report,indent=2,sort_keys=True)
    print(encoded)
    if args.json_out: Path(args.json_out).write_text(encoded+'\n')
    return 0 if passed else 1
if __name__=='__main__': sys.exit(main())
