"""Synthetic disposable PostgreSQL only. Never reads production DB/config."""
import subprocess,os,secrets,time,json,hashlib,sys,argparse,re
from pathlib import Path
from uuid import uuid4
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',required=True,help='Dedicated owner-approved staging repository')
parser.add_argument('--sha',required=True)
parser.add_argument('--image-id',required=True,help='Existing local immutable PostgreSQL 16 image ID')
args=parser.parse_args()
repo=Path(args.root).resolve();root=repo.parent
if not re.fullmatch(r'/home/catalystadmin/scec-v[0-9]+/repository',str(repo)):
 raise SystemExit('Dedicated user-owned staging checkout required')
if not re.fullmatch(r'[0-9a-f]{40}',args.sha) or not re.fullmatch(r'sha256:[0-9a-f]{64}',args.image_id):
 raise SystemExit('Exact source SHA and image ID required')
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==args.sha
assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
clean_env={k:os.environ[k] for k in ('PATH','HOME','LANG') if k in os.environ}
os.environ.clear();os.environ.update(clean_env)
runid=uuid4().hex[:10];name='scec-i15-pg-'+runid;network=name+'-net'
report={'scope':'synthetic PostgreSQL only; no production DB/config copied','checks':{},'production_restore_certified':False};report['source_sha']=args.sha;checks=report['checks'];started=False;net=False
password=secrets.token_urlsafe(36);secret=root/('pg-'+runid+'.env');secret.touch(mode=0o600);secret.write_text('POSTGRES_PASSWORD='+password+'\nPOSTGRES_DB=scec_engagement_fixture\n')
def cmd(args,**kw):return subprocess.run(args,check=True,capture_output=True,**kw)
def sql(query,db='scec_engagement_fixture'):return cmd(['docker','exec',name,'psql','-X','-v','ON_ERROR_STOP=1','-U','postgres','-d',db,'-At','-c',query]).stdout.decode().strip()
try:
 image=cmd(['docker','image','inspect',args.image_id,'--format','{{.Id}}']).stdout.decode().strip();report['postgres_image_id']=image;assert image==args.image_id
 cmd(['docker','network','create','--internal',network]);net=True
 cmd(['docker','run','-d','--name',name,'--network',network,'--memory','512m','--cpus','0.5','--tmpfs','/var/lib/postgresql/data:rw','--env-file',str(secret),image]);started=True
 fixture_host=json.loads(cmd(['docker','inspect',name]).stdout)[0]['NetworkSettings']['Networks'][network]['IPAddress'];port=5432
 for i in range(60):
  p=subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if p.returncode==0:break
  time.sleep(1)
 else:raise RuntimeError('Fixture database readiness timeout')
 sys.path.insert(0,str(repo/'backend'))
 os.environ.update({'SCEC_ENV':'development','SCEC_IDENTITY_MODE':'bound','SCEC_AUTH_MODE':'token','SCEC_IDENTITY_SIGNING_KEY':secrets.token_hex(32),'SCEC_PERSISTENCE_ENABLED':'1','SCEC_DATABASE_URL':f'postgresql+psycopg://postgres:{password}@{fixture_host}:{port}/scec_engagement_fixture','PYTHONPATH':str(repo/'backend')})
 org,other=uuid4(),uuid4();os.environ['SCEC_ALLOWED_ORGANIZATION_IDS']=str(org)+','+str(other)
 py=str(repo/'backend/.venv/bin/python')
 def migrate(target):
  r=cmd([py,'-m','alembic','-c','alembic.ini',*target],cwd=repo/'backend',env=os.environ)
  return r.stdout.decode()+r.stderr.decode()
 import psycopg
 for _ in range(30):
  try:
   with psycopg.connect(host=fixture_host,port=port,dbname='scec_engagement_fixture',user='postgres',password=password,connect_timeout=2):pass
   break
  except psycopg.OperationalError:time.sleep(1)
 else:raise RuntimeError('Host loopback fixture connection unavailable')
 migrate(['upgrade','head']);checks['migration_head']=sql('select version_num from alembic_version');assert checks['migration_head']=='850_001'
 migrate(['upgrade','head']);checks['migration_repeat_noop']=True
 from app.main import app
 from app.identity import mint_token
 from fastapi.testclient import TestClient
 client=TestClient(app)
 def headers(o,roles=['administrator']):return {'Authorization':'Bearer '+mint_token(subject='synthetic-fixture',organization_id=o,roles=roles,expires_at=int(time.time())+600,secret=os.environ['SCEC_IDENTITY_SIGNING_KEY']),'X-SCEC-Organization-ID':str(o)}
 for n,o in enumerate([org,other]):assert client.post('/v1/engagement/organizations',headers=headers(o),json={'id':str(o),'name':'Synthetic Organization '+str(n),'slug':'synthetic-'+str(n)}).status_code==201
 contact={'id':str(uuid4()),'organization_id':str(org),'display_name':'Synthetic fixture — no real person'}
 r=client.post('/v1/engagement/contacts',headers=headers(org),json=contact);assert r.status_code==201;checks['create']=201
 url='/v1/engagement/contacts/'+contact['id'];assert client.get(url,headers=headers(org)).status_code==200;checks['read']=200
 assert client.post('/v1/engagement/contacts',headers=headers(org),json=contact).status_code==409;checks['duplicate_conflict']=409
 assert client.post('/v1/engagement/contacts',headers=headers(org,['viewer']),json=contact).status_code==403;checks['viewer_write_denied']=403
 assert client.get(url,headers=headers(other)).status_code==404;checks['cross_tenant_read_denied']=404
 h=headers(org);h['X-SCEC-Organization-ID']=str(other);assert client.get(url,headers=h).status_code==403;checks['forged_tenant_header_denied']=403
 assert client.get(url).status_code==401;checks['unauthenticated_denied']=401
 payload={'organization_id':str(other),'display_name':'Synthetic mismatch'}
 assert client.post('/v1/engagement/contacts',headers=headers(org),json=payload).status_code==403;checks['cross_tenant_payload_denied']=403
 dump=root/('synthetic-postgres-fixture-'+runid+'.dump');dump.touch(mode=0o600,exist_ok=False)
 dump.write_bytes(cmd(['docker','exec',name,'pg_dump','-Fc','--no-owner','--no-acl','-U','postgres','scec_engagement_fixture']).stdout);dump.chmod(0o600)
 checks['dump_sha256']=hashlib.sha256(dump.read_bytes()).hexdigest();checks['dump_bytes']=dump.stat().st_size
 sql('CREATE DATABASE scec_engagement_restore',db='postgres')
 cmd(['docker','exec','-i',name,'pg_restore','--exit-on-error','--no-owner','--no-acl','-U','postgres','-d','scec_engagement_restore'],input=dump.read_bytes())
 count=sql('select count(*) from contacts');assert count==sql('select count(*) from contacts',db='scec_engagement_restore')=='1'
 checks['restore_contact_count']=1
 for table in ['organizations','contacts','engagement_audit_log']:
  query=f'SELECT row_to_json(t)::text FROM (SELECT * FROM {table} ORDER BY id) t'
  assert sql(query)==sql(query,db='scec_engagement_restore')
 checks['restored_fixture_rows_identical']=True
 os.environ['SCEC_DATABASE_URL']=os.environ['SCEC_DATABASE_URL'].replace('/scec_engagement_fixture','/scec_engagement_restore')
 try:
  migrate(['downgrade','base'])
  raise RuntimeError('Destructive downgrade unexpectedly permitted')
 except subprocess.CalledProcessError as refusal:
  assert b'Destructive downgrade forbidden' in refusal.stderr
  checks['destructive_downgrade_refused']=True
 migrate(['upgrade','head']);checks['restore_schema_remains_head']=True
 checks['limitations']='Existing endpoints support create/read and workflow transitions, not general update/delete. No production backup, real human SSO or production rollback exercised.'
 report['result']='PASS_SYNTHETIC_ONLY'
except Exception as e:
 report['result']='FAIL';report['error_type']=type(e).__name__
 if isinstance(e,subprocess.CalledProcessError):report['failed_command_program']=str(e.cmd[0]);report['returncode']=e.returncode;report['diagnostic']=(e.stderr or b'').decode(errors='replace').replace(password,'[REDACTED]')[-7000:]
finally:
 if started:report['fixture_container_removed']=subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL).returncode==0
 if net:report['fixture_network_removed']=subprocess.run(['docker','network','rm',network],stdout=subprocess.DEVNULL).returncode==0
 secret.unlink(missing_ok=True)
 (root/('postgres-rehearsal-'+runid+'.json')).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))

if report['result']!='PASS_SYNTHETIC_ONLY' or not report.get('fixture_container_removed') or not report.get('fixture_network_removed'):raise SystemExit(1)
