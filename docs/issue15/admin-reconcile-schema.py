"""Read-only structural reconciliation and SCEC runtime/role metadata. No mutation."""
import sys
sys.dont_write_bytecode=True
import os,json,subprocess,contextlib,io,runpy,re,hashlib
from pathlib import Path
from urllib.parse import urlsplit,unquote
if os.geteuid()!=0:raise SystemExit('Authorized administrator execution required')
base=Path(__file__).resolve().parent;sys.path.insert(0,str(base))
from compare_schema import compare,digest
expected=json.loads((base/'expected-schema-from-synthetic-restore.json').read_text())
assert digest(expected['schema'])=='38f1a9fa093e72785551064e5749a7d8e3b819c5b97da3073524e6b56ee97704','Expected schema changed'
with contextlib.redirect_stdout(io.StringIO()) as capture:
 namespace=runpy.run_path(str(base/'admin-schema-and-writers.py'))
inventory=json.loads(capture.getvalue());query=namespace['query'];db=inventory['database']
report={'scope':'READ ONLY; no migrations, grants, records, service operations or deployment','comparison':compare(expected,inventory),'production_inventory':inventory,'expected_tested_source':expected['source_sha'],'merged_target':'381a5a382c9b613136c091d0c1f235f36907c037'}
report['reported_fingerprint_reproduced']=inventory['schema_sha256']=='08a7bd472d4239c374ba655b2ade1844d216c3acd8a2cc1fd4fe61db885cb381'
report['production_version_settings']=json.loads(query(db,"SELECT json_object_agg(name,setting) FROM pg_settings WHERE name IN ('server_version','server_version_num','server_encoding','lc_collate','lc_ctype','search_path','standard_conforming_strings')"))
report['producer_versions']={'query_sha256':hashlib.sha256((base/'schema-fingerprint.sql').read_bytes()).hexdigest(),'comparer_sha256':hashlib.sha256((base/'compare_schema.py').read_bytes()).hexdigest(),'expected_schema_sha256':expected['schema_sha256'],'canonical_serialization':'json.dumps(sort_keys=True,separators=(comma,colon)); named collections additionally sorted for ordering diagnosis; SQL text untouched'}
# Effective table privileges are metadata, not evidence that a role is the app actor.
report['effective_table_grants']=json.loads(query(db,"SELECT COALESCE(json_agg(json_build_object('role',r.rolname,'login',r.rolcanlogin,'superuser',r.rolsuper,'table',c.relname,'owner',pg_get_userbyid(c.relowner),'select',has_table_privilege(r.oid,c.oid,'SELECT'),'insert',has_table_privilege(r.oid,c.oid,'INSERT'),'update',has_table_privilege(r.oid,c.oid,'UPDATE'),'delete',has_table_privilege(r.oid,c.oid,'DELETE'),'truncate',has_table_privilege(r.oid,c.oid,'TRUNCATE')) ORDER BY r.rolname,c.relname),'[]'::json) FROM pg_roles r CROSS JOIN pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') AND (r.rolsuper OR r.rolname IN ('scec_engagement_migrator','pg_write_all_data'))"))
report['role_memberships']=json.loads(query(db,"SELECT COALESCE(json_agg(json_build_object('granted_role',p.rolname,'member',m.rolname,'member_can_login',m.rolcanlogin,'admin_option',a.admin_option) ORDER BY p.rolname,m.rolname),'[]'::json) FROM pg_auth_members a JOIN pg_roles p ON p.oid=a.roleid JOIN pg_roles m ON m.oid=a.member WHERE p.rolname IN ('scec_engagement_migrator','pg_write_all_data') OR m.rolname='scec_engagement_migrator'"))
def command(args):return subprocess.run(args,text=True,capture_output=True)
def target(value):
 try:
  u=urlsplit(value)
  if not u.scheme:return {'parse_status':'not_a_url'}
  return {'scheme':u.scheme,'host':u.hostname,'port':u.port,'database':u.path.lstrip('/'),'database_role_identifier':unquote(u.username) if u.username else None}
 except ValueError:return {'parse_status':'unresolved'}
report['units']=[]
for line in command(['systemctl','list-unit-files','--no-legend','--no-pager','scec*.service']).stdout.splitlines():
 unit=line.split()[0]
 if not re.fullmatch(r'scec[-\w]+\.service',unit):continue
 p=command(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID','-p','User','-p','WorkingDirectory','-p','FragmentPath','-p','EnvironmentFiles'])
 d=dict(v.split('=',1) for v in p.stdout.splitlines() if '=' in v);d['unit']=unit;d['enabled_state']=command(['systemctl','is-enabled',unit]).stdout.strip()
 pid=d.get('MainPID','0');env={}
 if pid!='0':
  try:env=dict(v.decode(errors='replace').split('=',1) for v in Path('/proc/'+pid+'/environ').read_bytes().split(b'\0') if b'=' in v)
  except (OSError,ValueError):d['runtime_environment_inspection_failed']=True
 d['runtime_configuration_names']=sorted(k for k in env if k.startswith('SCEC_') or k in ('DATABASE_URL','PGUSER','PGDATABASE','PGSERVICE'))
 d['persistence_flag']=env.get('SCEC_PERSISTENCE_ENABLED','unset') if env.get('SCEC_PERSISTENCE_ENABLED','unset') in ('0','1','unset') else 'nonstandard-configured-value'
 d['runtime_database_targets']=[dict(variable=k,**target(env[k])) for k in ('SCEC_DATABASE_URL','DATABASE_URL') if env.get(k)]
 d['runtime_database_identity_observed']=bool(d['runtime_database_targets'])
 source=Path(d.get('WorkingDirectory','/nonexistent'))/'app/main.py'
 if source.is_file():
  text=source.read_text();d['main_source_sha256']=hashlib.sha256(text.encode()).hexdigest();d['persistent_handler_references_present']=any(v in text for v in ('put_record(', 'create_case(', 'transition_case(', 'create_engagement('))
 d['writer_assessment']='candidate only; inspect handler dependencies, enabled state, flags, DB target and role before classifying; no connection is not inactivity proof'
 report['units'].append(d)
report['protected_configuration_database_targets']=[]
for path in ('/etc/sustainable-catalyst/engagement/v800.env','/etc/sustainable-catalyst/engagement/v860.env'):
 p=Path(path);d={'path':path}
 try:
  raw=p.read_bytes();d['sha256']=hashlib.sha256(raw).hexdigest();d['targets']=[]
  for line in raw.decode().splitlines():
   m=re.match(r'(?:export\s+)?(SCEC_DATABASE_URL|DATABASE_URL)\s*=\s*(.*)',line.strip())
   if m:d['targets'].append(dict(variable=m[1],**target(m[2].strip().strip('"\''))))
 except (OSError,UnicodeError):d['inspection_failed']=True
 report['protected_configuration_database_targets'].append(d)
report['recommendation']='NO_GO_PENDING_SCHEMA_WRITER_RECOVERY_IDENTITY_PRIVACY_SECURITY_REVIEW'
report['limitations']=['Schema naming or PostgreSQL rendering differences require review; no blanket compatibility verdict from hashes.','No production data restored or modified; historical databases preserved.','Same-person primary/deputy is not independent approval.','No changes authorized by this read-only report; do not run migrations or alter grants.']
print(json.dumps(report,indent=2))
