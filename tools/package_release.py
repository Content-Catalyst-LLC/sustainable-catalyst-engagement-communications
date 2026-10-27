#!/usr/bin/env python3
"""Build and audit a complete credential-free release archive from admitted Git files."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(destination):
    output=Path(destination).resolve()
    if output==ROOT or ROOT in output.parents:
        raise ValueError('Archive output must be outside the repository')
    output.mkdir(parents=True,exist_ok=True)
    version=json.loads((ROOT/'RELEASE-MANIFEST.json').read_text())['version']
    checksum_name='RELEASE-CHECKSUMS-v'+version+'.json'
    paths=set(subprocess.check_output(['git','-C',str(ROOT),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0'))-{''}
    files={}
    for name in sorted(paths):
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or any(s in ('.git','.venv','__pycache__','.pytest_cache') for s in p.parts):
            raise ValueError('Unsafe release member')
        if any(s.startswith('.env') and not s.endswith('.example') for s in p.parts):
            raise ValueError('Private environment file in release inputs')
        if name==checksum_name:
            continue
        source=ROOT/name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Nonregular release input')
        files[name]=source.read_bytes()
    manifest={'algorithm':'SHA-256','release':version,'files':{name:digest(data) for name,data in files.items()}}
    (ROOT/checksum_name).write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    files[checksum_name]=(ROOT/checksum_name).read_bytes()
    archive=output/('sustainable-catalyst-engagement-communications-v'+version+'.zip')
    prefix='sustainable-catalyst-engagement-communications/'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as bundle:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(prefix+name,date_time=(2026,10,27,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            bundle.writestr(info,data)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None or set(bundle.namelist())!={prefix+n for n in files}:
            raise ValueError('Archive membership/integrity failure')
        for name,data in files.items():
            if digest(bundle.read(prefix+name))!=digest(data):
                raise ValueError('Bundled file differs: '+name)
    report={'release':version,'source_file_count':len(manifest['files']), 'bundled_file_count':len(files),
            'all_bundled_files_verified':True,'zip':archive.name,'zip_sha256':digest(archive.read_bytes()),
            'checksum_manifest_sha256':digest(files[checksum_name])}
    (output/('ARTIFACT-AUDIT-v'+version+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output_directory')
    build(parser.parse_args().output_directory)
