"""Synthetic-only backup, forward migration and snapshot rollback acceptance."""
from pathlib import Path
import hashlib,json,os,subprocess
from uuid import uuid4
root=Path(__file__).resolve().parents[1]
private=Path(os.environ['MEDIA09_RECEIPT']).resolve().parent
suffix=uuid4().hex[:8]
container='sc-media09-acceptance-20261113-db'
def cmd(args,**kwargs):return subprocess.run(args,check=True,capture_output=True,**kwargs).stdout

def sql(query,db='postgres'):
 return cmd(['docker','exec',container,'psql','-X','-v','ON_ERROR_STOP=1','-U','postgres','-d',db,'-At','-c',query]).decode().strip()
original=os.environ['SCEC_DATABASE_URL']
assert original.split('?')[0].endswith('/scec_engagement_media09_acceptance')
assert os.environ.get('SCEC_ENV')=='development'
def migrate(db,target):
 env=os.environ|{'PYTHONPATH':str(root/'backend'),'SCEC_DATABASE_URL':original.rsplit('/',1)[0]+'/'+db}
 cmd([str(root/'.venv/bin/alembic'),'upgrade',target],cwd=root/'backend',env=env)
def dump(db,name):
 path=private/name;path.touch(mode=0o600,exist_ok=False)
 path.write_bytes(cmd(['docker','exec',container,'pg_dump','-Fc','--no-owner','--no-acl','-U','postgres',db]))
 return path
# Independent pre-MEDIA09 baseline, with existing canonical schema.
sql(f'CREATE DATABASE scec_engagement_media09_baseline_{suffix}')
migrate(f'scec_engagement_media09_baseline_{suffix}','850_001')
baseline=dump(f'scec_engagement_media09_baseline_{suffix}',f'before-media09-{suffix}.dump')
migrate(f'scec_engagement_media09_baseline_{suffix}','head')
assert sql('SELECT version_num FROM alembic_version',f'scec_engagement_media09_baseline_{suffix}')=='media09_1_003'
# Restore rollback snapshot into a different disposable database. Never drop production tables.
sql(f'CREATE DATABASE scec_engagement_media09_rollback_{suffix}')
cmd(['docker','exec','-i',container,'pg_restore','--exit-on-error','--no-owner','--no-acl','-U','postgres','-d',f'scec_engagement_media09_rollback_{suffix}'],input=baseline.read_bytes())
assert sql('SELECT version_num FROM alembic_version',f'scec_engagement_media09_rollback_{suffix}')=='850_001'
assert sql("SELECT count(*) FROM information_schema.tables WHERE table_name='media09_press_inquiries'",f'scec_engagement_media09_rollback_{suffix}')=='0'
post=dump('scec_engagement_media09_acceptance',f'accepted-media09-{suffix}.dump')
sql(f'CREATE DATABASE scec_engagement_media09_restore_{suffix}')
cmd(['docker','exec','-i',container,'pg_restore','--exit-on-error','--no-owner','--no-acl','-U','postgres','-d',f'scec_engagement_media09_restore_{suffix}'],input=post.read_bytes())
for table in ['organizations','contacts','inquiries','media09_press_inquiries','engagement_audit_log']:
 query=f'SELECT row_to_json(t)::text FROM (SELECT * FROM {table} ORDER BY id) t'
 assert sql(query,'scec_engagement_media09_acceptance')==sql(query,f'scec_engagement_media09_restore_{suffix}')
report={'pre_migration_backup':True,'forward_migration':True,'rollback_snapshot_restored':True,'accepted_rows_restored_identically':True,
 'before_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(post.read_bytes()).hexdigest(),
 'scope':'isolated synthetic PostgreSQL only; no production database accessed'}
(private/'backup-final-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
