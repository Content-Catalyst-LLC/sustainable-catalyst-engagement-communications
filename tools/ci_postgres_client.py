#!/usr/bin/env python3
"""Use the existing CI PostgreSQL service's matching clients, without host package drift."""
import os,re,subprocess,sys
from pathlib import Path

if os.getenv('CI')!='true':raise SystemExit('CI service client only')
container=os.environ.get('PG_SERVICE_CONTAINER','')
if not re.fullmatch(r'[0-9a-f]{64}',container):raise SystemExit('Explicit CI service container required')
command,*args=sys.argv[1:]
if command not in ('psql','createdb','pg_dump','pg_restore'):raise SystemExit('Unsupported client')
source=None
if command=='psql' and '-f' in args:
    index=args.index('-f');source=Path(args[index+1]);del args[index:index+2]
elif command=='pg_restore' and args and Path(args[-1]).is_file():source=Path(args.pop())
call=['docker','exec','-i','-e','PGHOST=127.0.0.1','-e','PGPORT=5432','-e','PGUSER','-e','PGPASSWORD','-e','PGDATABASE',container,command,*args]
if source:
    with source.open('rb') as stream:result=subprocess.run(call,stdin=stream)
else:result=subprocess.run(call)
raise SystemExit(result.returncode)
