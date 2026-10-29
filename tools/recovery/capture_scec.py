#!/usr/bin/env python3
"""Future approved read-only capture. NEVER pauses writers or changes services.
Approval binds fixed paths, DB profile/identity, image ID and free-space budget.
No production execution is authorized by shipping this tool.
"""
import argparse, configparser, json, os, re, shutil, subprocess as sp, tempfile
from pathlib import Path
from scec_recovery import authorize, backup, digest, require, run


def capture(plan_path, approval_path):
    p = json.loads(plan_path.read_text())
    require(p['mode'] == 'production', 'production capture plan required')
    authorize(p, plan_path, approval_path)
    require(p['database'] == 'scec_engagement_v820' and p['revision'] == '850_001', 'unexpected database/revision')
    require(re.fullmatch('sha256:[a-f0-9]{64}', p['image']), 'immutable image ID required')
    output = Path(p['output'])
    require(not output.exists() and output.parent.is_dir(), 'fresh output required')
    require(output.parent.stat().st_mode & 0o077 == 0, 'restricted output directory required')
    require(shutil.disk_usage(output.parent).free >= p['minimum_free_bytes'], 'capture capacity insufficient')
    pgfile = Path(p['pgservicefile'])
    require(pgfile.is_file() and not pgfile.is_symlink() and pgfile.stat().st_mode & 0o077 == 0, 'restricted PostgreSQL service file required')
    cfg = configparser.ConfigParser(interpolation=None); cfg.read(pgfile)
    service = cfg[p['pgservice']]
    require(service.get('dbname') == p['database'], 'service file database mismatch')
    require(service.get('host') == p['db_host'] and service.get('port', '5432') == str(p['db_port']), 'service endpoint mismatch')
    # Restrict libpq environment; no inherited alternate connection or credential settings.
    env = {k:v for k,v in os.environ.items() if not k.startswith('PG')}
    env['PGSERVICEFILE'] = str(pgfile)
    dbarg = 'service=' + p['pgservice']
    def sql(q):
        return run(['psql', '-X', '-w', '--dbname', dbarg, '-At', '-v', 'ON_ERROR_STOP=1', '-c', q], env=env).stdout.decode().strip()
    ident = json.loads(sql("BEGIN READ ONLY; SELECT json_build_object('database',current_database(),'user',current_user,'version',current_setting('server_version_num'),'revision',(SELECT version_num FROM public.alembic_version)); ROLLBACK;").splitlines()[1])
    require(ident['database'] == p['database'] and ident['user'] == p['db_user'] and ident['revision'] == p['revision'] and str(ident['version']).startswith('16'), 'runtime DB identity/version mismatch')
    # Paths are fixed, absolute, individually hashed; no globbing or shell interpolation.
    files = []
    for item in p['capture_files']:
        path = Path(item['path'])
        require(path.is_absolute() and path.is_file() and not path.is_symlink(), 'capture regular file required')
        require(digest(path) == item['sha256'], 'capture baseline drift')
        files.append(dict(item))
    # Approved source archive must already exist and be pinned; no live tar of PG data directories.
    require(p['source_archive_name'] in {x['name'] for x in files}, 'pinned source archive missing')
    require(p['roles_metadata_name'] in {x['name'] for x in files}, 'scoped role/grant recovery metadata missing')
    with tempfile.TemporaryDirectory(prefix='.scec-capture-', dir=output.parent) as temp:
        stage = Path(temp)
        def stream_to(args, path, env=None):
            with open(path, 'xb') as f:
                sp.run(args, env=env, stdout=f, stderr=sp.PIPE, check=True)
                f.flush(); os.fsync(f.fileno())
        db = stage/'database.dump'
        stream_to(['pg_dump', '-w', '--dbname', dbarg, '--format=custom', '--lock-wait-timeout=10s'], db, env)
        run(['pg_restore', '--list', str(db)])
        image = stage/'frontend-image.tar'; stream_to(['docker', 'image', 'save', p['image']], image)
        for name, path in [('database.dump',db), ('frontend-image.tar',image)]:
            files.append({'name':name,'path':str(path),'sha256':digest(path)})
        # Derived inventory is bound to approved fixed inputs; receipt explicitly retains original authority hash.
        derived = dict(p, files=files)
        dp = stage/'bundle-plan.json'; dp.write_text(json.dumps(derived))
        approval = json.loads(Path(approval_path).read_text())
        approval['derived_from_plan_sha256'] = digest(plan_path)
        approval['plan_sha256'] = digest(dp)
        ap = stage/'derived-approval.json'; ap.write_text(json.dumps(approval))
        result = backup(dp, str(ap)); result['approved_capture_plan_sha256'] = digest(plan_path)
        result['database_identity'] = ident
        return result

if __name__ == '__main__':
    os.umask(0o077)
    ap = argparse.ArgumentParser(); ap.add_argument('--plan', type=Path, required=True); ap.add_argument('--approval', type=Path, required=True)
    args = ap.parse_args()
    try: print(json.dumps(capture(args.plan, str(args.approval))))
    except Exception as exc:
        print(json.dumps({'result':'FAIL','reason':str(exc) if not isinstance(exc,sp.CalledProcessError) else 'capture subprocess failed (details suppressed)'})); raise SystemExit(1)
