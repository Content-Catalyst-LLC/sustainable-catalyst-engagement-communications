#!/usr/bin/env python3
"""Read-only gap inventory; emits metadata only. Requires authorized administrator.
No record bodies, passwords, raw job commands, private key contents or writes.
"""
import hashlib,json,os,re,subprocess
from pathlib import Path
from urllib.parse import urlsplit
if os.geteuid()!=0:raise SystemExit('Authorized administrator access required; no mutation attempted')
r={'scope':'read-only metadata gaps only; not backup or permission to execute backup','protected_configuration':[]}
for name in ['/etc/sustainable-catalyst/engagement/v800.env','/etc/sustainable-catalyst/engagement/v860.env']:
 p=Path(name);s=p.stat();raw=p.read_bytes();d={'path':name,'bytes':s.st_size,'mode':oct(s.st_mode&0o777),'uid':s.st_uid,'gid':s.st_gid,'sha256':hashlib.sha256(raw).hexdigest(),'variable_names':[],'safe_storage_identifiers':{}}
 for line in raw.decode().splitlines():
  m=re.match(r'(?:export\s+)?([A-Z][A-Z0-9_]+)\s*=\s*(.*)',line.strip())
  if not m:continue
  k,v=m[1],m[2].strip().strip('"\'');d['variable_names'].append(k)
  if k in ['SCEC_HUMAN_SESSION_DB','SCEC_STORAGE_DIR','SCEC_ARTIFACT_DIR']:
   d['safe_storage_identifiers'][k]=v if v.startswith('/') and not any(c in v for c in ['\n','?','#','@']) else 'configured; restricted review required'
  if k in ['SCEC_DATABASE_URL','DATABASE_URL']:
   u=urlsplit(v);d['safe_storage_identifiers'][k]={'host':u.hostname,'port':u.port,'database':u.path.lstrip('/')} if u.scheme and u.hostname else {'parse_status':'restricted non-URL review required'}
 r['protected_configuration'].append(d)
# Candidate job references only; wrappers with no literal reference remain a scope limitation.
r['candidate_jobs']=[]
paths=[Path('/etc/crontab')]
for directory in ['/etc/cron.d','/etc/cron.daily','/etc/cron.hourly','/etc/cron.weekly','/etc/cron.monthly','/var/spool/cron/crontabs','/etc/systemd/system','/usr/lib/systemd/system']:
 p=Path(directory)
 if p.exists():paths.extend(x for x in p.iterdir() if x.is_file() and x.stat().st_size<1000000)
for p in paths:
 raw=p.read_bytes();text=raw.decode(errors='replace');matches=[i for i,line in enumerate(text.splitlines(),1) if re.search(r'scec|scec_engagement|engagement-communications',line,re.I)]
 if matches:r['candidate_jobs'].append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'matching_line_numbers':matches,'raw_commands_excluded':True})
def query(sql):
 p=subprocess.run(['runuser','-u','postgres','--','psql','-X','-q','-v','ON_ERROR_STOP=1','-d','scec_engagement_v820','-At','-c','BEGIN READ ONLY; SET LOCAL search_path=pg_catalog,public; '+sql+'; ROLLBACK;'],check=True,capture_output=True,text=True)
 return json.loads(p.stdout)
r['extensions']=query("SELECT COALESCE(json_agg(json_build_object('name',extname,'version',extversion)),'[]'::json) FROM pg_extension")
r['noninternal_triggers']=query("SELECT COALESCE(json_agg(json_build_object('table',c.relname,'trigger',t.tgname,'enabled',t.tgenabled,'definition_md5',md5(pg_get_triggerdef(t.oid)))),'[]'::json) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal AND n.nspname='public'")
r['event_triggers']=query("SELECT COALESCE(json_agg(json_build_object('name',evtname,'enabled',evtenabled)),'[]'::json) FROM pg_event_trigger")
r['subscriptions']=query("SELECT COALESCE(json_agg(json_build_object('name',subname,'enabled',subenabled)),'[]'::json) FROM pg_subscription WHERE subdbid=(SELECT oid FROM pg_database WHERE datname=current_database())")
r['publications']=query("SELECT COALESCE(json_agg(json_build_object('name',pubname,'all_tables',puballtables)),'[]'::json) FROM pg_publication")
r['cron_job_table_present']=query("SELECT to_json(to_regclass('cron.job') IS NOT NULL)")
if r['cron_job_table_present']:
 r['database_jobs']=query("SELECT COALESCE(json_agg(json_build_object('jobid',jobid,'database',database,'username',username,'active',active,'command_md5',md5(command))),'[]'::json) FROM cron.job WHERE database=current_database()")
r['tls_storage_metadata']=[]
for name in ['/var/lib/caddy/.local/share/caddy','/var/lib/caddy/.config/caddy']:
 p=Path(name)
 if p.exists():
  z=subprocess.run(['du','-sb',name],capture_output=True,text=True)
  r['tls_storage_metadata'].append({'path':name,'apparent_bytes':int(z.stdout.split()[0]) if z.returncode==0 else None,'private_key_contents_not_read':True})
r['limitations']=['Literal job references do not prove absence of indirect/manual/external writers.','Database ownership and historical purposes still need operator attestation.','TLS recovery scope must exclude unrelated sites; aggregate Caddy size is not permission to archive it.','No keys or plaintext credentials emitted; no backup, data change or service operation.']
print(json.dumps(r,indent=2))
