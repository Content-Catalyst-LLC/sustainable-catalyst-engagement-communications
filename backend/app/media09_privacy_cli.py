"""Manual privacy operator commands. No scheduled or real deletion is enabled by installation."""
import argparse,json,sys
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from .contact_service import config
from . import media09_privacy as privacy

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['preview','retention','restore-suppression','expire-backups','register-backup'])
    parser.add_argument('--organization',type=UUID,required=True)
    parser.add_argument('--apply',action='store_true',help='Explicitly authorize this configured operator mutation')
    parser.add_argument('--backup-id',type=UUID)
    parser.add_argument('--synthetic-only',action='store_true')
    args=parser.parse_args()
    try:
        url,allowed=config()
        if str(args.organization) not in allowed:raise HTTPException(403,'Organization not allowlisted')
        if args.operation!='preview' and not args.apply:raise HTTPException(409,'Use --apply for a reviewed operator mutation')
        privacy.enabled()
        engine=create_engine(url)
        try:
            with Session(engine) as db,db.begin():
                if args.operation=='preview':result=privacy.retention_preview(db,args.organization)
                elif args.operation=='retention':result=privacy.run_retention(db,args.organization)
                elif args.operation=='restore-suppression':result=privacy.apply_suppression(db,args.organization)
                elif args.operation=='expire-backups':result=privacy.expire_backups(db,args.organization)
                else:
                    if not args.backup_id:raise HTTPException(422,'Backup ID required')
                    result=privacy.register_backup(db,args.organization,args.backup_id,synthetic_only=args.synthetic_only)
            print(json.dumps(result,default=str))
        finally:engine.dispose()
    except HTTPException as exc:
        print(json.dumps({'status':exc.status_code,'detail':exc.detail}),file=sys.stderr);return 1
    except SQLAlchemyError:
        print(json.dumps({'status':503,'detail':'Privacy storage operation failed; reconcile suppression before serving'}),file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
