#!/usr/bin/env python3
"""Owned-process, loopback-only smoke and source checks for isolated SCEC staging."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def verify(root, expected_sha, version, phase, port, route):
    root = Path(root).resolve()
    if not re.fullmatch(r'/opt/scec-v[0-9]+/repository', str(root)):
        raise ValueError('Only isolated /opt/scec-vNNNN/repository checkouts are allowed')
    if not 8838 <= port <= 8868 or not route.startswith('/v1/'):
        raise ValueError('Unexpected staging port or status route')
    actual = subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'], text=True).strip()
    if actual != expected_sha:
        raise ValueError('Checkout differs from reviewed commit')
    if subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip():
        raise ValueError('Staging checkout is dirty')
    probe = socket.socket()
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', port))
    finally:
        probe.close()
    flags = set()
    for source in (root/'backend/app').rglob('*.py'):
        flags.update(re.findall(r'SCEC_[A-Z0-9_]*ENABLED', source.read_text()))
    env = {'PATH':os.environ['PATH'], 'HOME':os.environ['HOME'], 'LANG':'C.UTF-8',
           'PYTHONPATH':str(root/'backend'), 'PYTHONDONTWRITEBYTECODE':'1',
           'SCEC_ENV':'development', 'SCEC_AUTH_MODE':'token',
           'SCEC_SERVICE_TOKEN':secrets.token_hex(32), **{flag:'0' for flag in flags}}
    result = {'commit':actual, 'version':version, 'port':port, 'disabled_flags':sorted(flags)}
    python = str(root/'backend/.venv/bin/python')
    process = None
    with tempfile.TemporaryFile() as log:
        try:
            process = subprocess.Popen([python,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
                                       cwd=root/'backend', env=env, stdout=log, stderr=log)
            deadline = time.monotonic()+30
            while True:
                if process.poll() is not None:
                    raise RuntimeError('Owned temporary app exited during startup')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1) as response:
                        health = json.load(response)
                    break
                except OSError:
                    if time.monotonic()>deadline:
                        raise RuntimeError('Temporary health check timed out') from None
                    time.sleep(.2)
            if health.get('version')!=version or health.get('phase')!=phase:
                raise RuntimeError('Health release identity mismatch')
            result['health'] = {'http_status':200,'body':health}
            for name, headers in [('unauthenticated',{}), ('ephemeral_service_authenticated',{'Authorization':'Bearer '+env['SCEC_SERVICE_TOKEN']})]:
                try:
                    with urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}{route}',headers=headers),timeout=5) as response:
                        status = response.status
                except urllib.error.HTTPError as error:
                    status = error.code
                result[name+'_disabled_status'] = status
                if status not in (401,503):
                    raise RuntimeError('Disabled endpoint unexpectedly available')
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()  # Only this verifier's owned child, never another service.
                    process.wait(timeout=5)
                    raise RuntimeError('Owned staging app required forced shutdown')
    result['temporary_process_exit_code'] = process.returncode
    if subprocess.check_output(['ss','-H','-ltn',f'sport = :{port}'],text=True).strip():
        raise RuntimeError('Staging LISTEN socket remains')
    result['port_released'] = True
    cert = subprocess.run([python,str(root/'certification/certify.py')],cwd=root,env=env,capture_output=True,text=True,check=True)
    report = json.loads(cert.stdout)
    if report['preflight']!='PASS' or report['production_certified'] is not False or report['production_writes_enabled'] is not False or report['live_checks']!={} or len(report['gates_not_certified'])!=7:
        raise RuntimeError('Source certification or safety state failed')
    result['certification'] = report
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('root','sha','version','phase','route'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.root,args.sha,args.version,args.phase,args.port,args.route),indent=2))
