"""Read-only main SCEC schema and writer-candidate metadata. No row data/secrets."""
import os,json,subprocess,hashlib,re
from pathlib import Path
if os.geteuid()!=0:raise SystemExit('Authorized administrator sudo execution required')
base=Path(__file__).resolve().parent;sql=(base/'schema-fingerprint.sql').read_text()
def query(db,statement):
 p=subprocess.run(['runuser','-u','postgres','--','psql','-X','-q','-v','ON_ERROR_STOP=1','-U','postgres','-d',db,'-At','-c','BEGIN READ ONLY; SET LOCAL search_path=pg_catalog,public; '+statement+'; ROLLBACK;'],text=True,capture_output=True)
 if p.returncode:raise RuntimeError('Read-only metadata query failed; inspect locally without sharing credentials')
 return p.stdout.strip()
r={'scope':'read-only schema and candidate writer metadata; no personal rows or query texts','database':'scec_engagement_v820'}
schema=json.loads(query(r['database'],sql));r['schema']=schema;r['schema_sha256']=hashlib.sha256(json.dumps(schema,sort_keys=True,separators=(',',':')).encode()).hexdigest();r['table_count']=len(schema['tables'])
r['revision']=query(r['database'],'SELECT version_num FROM public.alembic_version')
r['databases']=json.loads(query('postgres',"SELECT COALESCE(json_agg(json_build_object('name',datname,'owner',pg_get_userbyid(datdba),'bytes',pg_database_size(oid)) ORDER BY datname),'[]'::json) FROM pg_database WHERE datname ~* '(scec|engagement)' AND datallowconn"))
r['write_privileged_roles']=json.loads(query(r['database'],"SELECT COALESCE(json_agg(json_build_object('role',rolname,'login',rolcanlogin,'superuser',rolsuper) ORDER BY rolname),'[]'::json) FROM pg_roles r WHERE rolsuper OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') AND has_table_privilege(r.oid,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE'))"))
r['connections']=json.loads(query(r['database'],"SELECT COALESCE(json_agg(json_build_object('application_name',application_name,'role',usename,'state',state,'backend_type',backend_type)),'[]'::json) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"))
r['storage']=json.loads(query(r['database'],"SELECT json_object_agg(name,setting) FROM pg_settings WHERE name IN ('data_directory','port','listen_addresses','ssl')"))
r['candidate_scheduled_files']=[]
paths=[Path('/etc/crontab')]
for directory in ['/etc/cron.d','/var/spool/cron/crontabs','/etc/systemd/system']:
 p=Path(directory)
 if p.exists():paths.extend(f for f in p.iterdir() if f.is_file() and f.stat().st_size<1000000)
for p in paths:
 try:
  raw=p.read_bytes();text=raw.decode(errors='replace')
  lines=[i for i,line in enumerate(text.splitlines(),1) if re.search(r'scec|scec_engagement|engagement-communications',line,re.I)]
  if lines:r['candidate_scheduled_files'].append({'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'matching_line_numbers':lines,'command_text_excluded':True})
 except OSError:continue
r['limitations']=['Candidate privileges/jobs are not proof of active writes or an exhaustive external writer inventory.','No production data/config/service changed.','Preserve all historical databases; names alone do not establish ownership or disposition.']
print(json.dumps(r,indent=2))
