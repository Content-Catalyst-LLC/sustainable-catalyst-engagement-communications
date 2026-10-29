#!/usr/bin/env python3
"""Guarded GPG recovery bundles. No network, writer/service operations or key creation.
Plan/approval are operator attestations, not substitutes for independent authorization.
"""
import argparse, datetime as dt, hashlib, io, json, os, re, shutil, socket
import subprocess as sp, tarfile, tempfile
from pathlib import Path


def digest(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()


def require(ok, why):
    if not ok: raise ValueError(why)


def run(args, **kw):
    return sp.run(args, check=True, stdout=sp.PIPE, stderr=sp.PIPE, **kw)


def key(gpg_home, fingerprint, secret=False):
    require(re.fullmatch(r'[A-F0-9]{40}|[A-F0-9]{64}', fingerprint), 'full uppercase fingerprint required')
    require(gpg_home.is_dir() and not gpg_home.is_symlink(), 'existing dedicated keyring required')
    require(gpg_home.stat().st_mode & 0o077 == 0, 'keyring permissions must be 0700')
    lines = run(['gpg', '--homedir', str(gpg_home), '--batch', '--no-auto-key-retrieve',
                 '--with-colons', '--list-secret-keys' if secret else '--list-keys', fingerprint]).stdout.decode().splitlines()
    rows = [x.split(':') for x in lines]
    require(any(x[0] == 'fpr' and x[9] == fingerprint for x in rows), 'fingerprint absent')
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    require(any(x[0] in ('pub', 'sub', 'sec', 'ssb') and 'e' in x[11].lower()
                and x[1] not in ('r', 'e', 'd') and (not x[6] or int(x[6]) > now)
                for x in rows), 'no valid encryption key')


def authorize(plan, plan_path, approval_path):
    if plan['mode'] == 'synthetic':
        require(plan['label'].startswith('SYNTHETIC-'), 'synthetic label required')
        return
    require(plan['mode'] == 'production', 'invalid mode')
    require(approval_path, 'production approval file required')
    approval = json.loads(Path(approval_path).read_text())
    require(approval['plan_sha256'] == digest(plan_path), 'approval/plan mismatch')
    require(approval['operation'] == 'SCEC_BACKUP_ONLY', 'backup approval required')
    require(approval['hostname'] == socket.gethostname() == plan['hostname'], 'wrong host')
    expiry = dt.datetime.fromisoformat(approval['expires_utc'].replace('Z', '+00:00'))
    require(expiry > dt.datetime.now(dt.timezone.utc), 'approval expired')
    for field in ['owner_approval_record', 'independent_verifier', 'scope_complete',
                  'consistency_checkpoint', 'custody_verified', 'destination_approved']:
        require(approval.get(field), 'missing approval prerequisite: ' + field)
    require(approval['independent_verifier'] != approval['owner_approval_record'], 'distinct verifier required')


def backup(plan_path, approval_path):
    p = json.loads(plan_path.read_text())
    authorize(p, plan_path, approval_path)
    home = Path(p['gpg_home']); key(home, p['recipient'])
    target = Path(p['output'])
    require(target.is_absolute() and target.parent.is_dir() and not target.exists(), 'new absolute output required')
    require(not target.is_symlink() and target.parent.stat().st_mode & 0o077 == 0, 'restricted destination required')
    require(not Path(str(target) + '.sha256').exists(), 'checksum collision')
    entries = []; names = set()
    for item in p['files']:
        source = Path(item['path']); name = item['name']
        require(re.fullmatch(r'[A-Za-z0-9_.-]+', name) and name not in ('.', '..', 'manifest.json'), 'unsafe name')
        require(name not in names, 'duplicate name'); names.add(name)
        require(source.is_absolute() and source.is_file() and not source.is_symlink(), 'regular absolute source required')
        require(digest(source) == item['sha256'], 'source drift: ' + name)
        entries.append(dict(item, size=source.stat().st_size))
    require(entries, 'empty scope')
    # Allow at least two uncompressed equivalents plus reserve; no compression assumption.
    required = 2 * sum(x['size'] for x in entries) + 16 * 1024 * 1024
    require(shutil.disk_usage(target.parent).free >= required, 'insufficient space')
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    proc = None; success = False
    try:
        with os.fdopen(fd, 'wb') as output, tempfile.TemporaryFile() as error:
            proc = sp.Popen(['gpg', '--homedir', str(home), '--batch', '--no-auto-key-retrieve',
                             '--trust-model', 'always', '--recipient', p['recipient'], '--encrypt'],
                            stdin=sp.PIPE, stdout=output, stderr=error)
            # Trust is supplied only by the exact independently approved fingerprint above;
            # never keyserver discovery/short-ID/automatic recipient selection.
            with tarfile.open(fileobj=proc.stdin, mode='w|') as tar:
                manifest = json.dumps({'format': 1, 'label': p['label'], 'mode': p['mode'],
                                       'plan_sha256': digest(plan_path), 'files': entries}, sort_keys=True).encode()
                info = tarfile.TarInfo('manifest.json'); info.size = len(manifest); info.mode = 0o600
                tar.addfile(info, io.BytesIO(manifest))
                for item in entries:
                    with open(item['path'], 'rb') as f:
                        info = tarfile.TarInfo(item['name']); info.size = item['size']; info.mode = 0o600
                        tar.addfile(info, f)
            proc.stdin.close()
            require(proc.wait() == 0, 'GPG encryption failed')
            output.flush(); os.fsync(output.fileno())
        for item in entries: require(digest(item['path']) == item['sha256'], 'source changed during backup')
        checksum = digest(target)
        checksum_path = Path(str(target) + '.sha256')
        with open(checksum_path, 'x') as f: f.write(checksum + '\n')
        os.chmod(checksum_path, 0o600)
        success = True
        return {'result': 'PASS', 'ciphertext_sha256': checksum, 'ciphertext_bytes': target.stat().st_size,
                'files': len(entries), 'label': p['label']}
    finally:
        if proc and proc.poll() is None: proc.kill(); proc.wait()
        if not success: target.unlink(missing_ok=True)


def restore(bundle, expected, home, recipient, target, max_bytes):
    require(re.fullmatch('[a-f0-9]{64}', expected), 'independently retained ciphertext hash required')
    require(digest(bundle) == expected, 'ciphertext checksum mismatch')
    require(target.is_absolute() and target.parent.is_dir() and not target.exists(), 'fresh absolute restore target required')
    require(not target.is_symlink(), 'symlink restore target forbidden')
    key(home, recipient, secret=True)
    require(shutil.disk_usage(target.parent).free >= max_bytes + 16*1024*1024, 'restore capacity insufficient')
    target.mkdir(mode=0o700); success = False
    try:
        # Decrypt fully before parsing, so integrity failure cannot promote extracted files.
        # Restricted temporary plaintext is erased on normal/error exit, not secure-erased on SSD.
        with tempfile.TemporaryDirectory(prefix='.scec-restore-', dir=target.parent) as stage:
            plain = Path(stage)/'bundle.tar'
            with open(plain, 'xb') as f:
                proc = sp.Popen(['gpg', '--homedir', str(home), '--batch', '--no-auto-key-retrieve',
                                 '--decrypt', str(bundle)], stdout=sp.PIPE, stderr=sp.DEVNULL)
                total = 0
                try:
                    while True:
                        block = proc.stdout.read(1024*1024)
                        if not block: break
                        total += len(block); require(total <= max_bytes, 'restore size limit exceeded'); f.write(block)
                    require(proc.wait() == 0, 'GPG decryption/integrity failure')
                finally:
                    proc.stdout.close()
                    if proc.poll() is None: proc.kill(); proc.wait()
            with tarfile.open(plain) as tar:
                members = tar.getmembers()
                require(all(x.isfile() and re.fullmatch(r'[A-Za-z0-9_.-]+', x.name)
                            and x.name not in ('.', '..') for x in members), 'unsafe archive member')
                require(len({x.name for x in members}) == len(members), 'duplicate archive member')
                require('manifest.json' in {x.name for x in members}, 'missing manifest')
                mi = tar.getmember('manifest.json'); require(mi.size <= 1024*1024, 'manifest too large')
                manifest = json.load(tar.extractfile(mi)); require(manifest['format'] == 1, 'format unsupported')
                require(len({x['name'] for x in manifest['files']}) == len(manifest['files']), 'duplicate manifest file')
                expected_names = {'manifest.json'} | {x['name'] for x in manifest['files']}
                require(expected_names == {x.name for x in members}, 'manifest membership mismatch')
                for item in manifest['files']:
                    member = tar.getmember(item['name']); require(member.size == item['size'], 'size mismatch')
                    dest = target/item['name']
                    with open(dest, 'xb') as f: shutil.copyfileobj(tar.extractfile(member), f)
                    os.chmod(dest, 0o600)
                    require(digest(dest) == item['sha256'], 'restored checksum mismatch')
            success = True
            return {'result': 'PASS', 'label': manifest['label'], 'files_verified': len(manifest['files'])}
    finally:
        if not success: shutil.rmtree(target)


def main():
    os.umask(0o077)
    ap = argparse.ArgumentParser(); subs = ap.add_subparsers(dest='command', required=True)
    b = subs.add_parser('backup'); b.add_argument('--plan', type=Path, required=True); b.add_argument('--approval')
    r = subs.add_parser('restore'); r.add_argument('--bundle', type=Path, required=True)
    r.add_argument('--sha256', required=True); r.add_argument('--gpg-home', type=Path, required=True)
    r.add_argument('--recipient', required=True); r.add_argument('--target', type=Path, required=True)
    r.add_argument('--max-bytes', type=int, required=True)
    args = ap.parse_args()
    try:
        result = backup(args.plan, args.approval) if args.command == 'backup' else restore(
            args.bundle, args.sha256, args.gpg_home, args.recipient, args.target, args.max_bytes)
        print(json.dumps(result))
    except Exception as exc:
        # Do not print subprocess stderr that might contain sensitive metadata.
        print(json.dumps({'result': 'FAIL', 'reason': str(exc) if not isinstance(exc, sp.CalledProcessError)
                          else 'subprocess failed (details suppressed)'})); raise SystemExit(1)

if __name__ == '__main__': main()
