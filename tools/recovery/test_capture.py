"""Focused collector tests; subprocesses mocked, production never contacted."""
import datetime as dt
import json
import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import capture_scec as c


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name); os.chmod(self.root,0o700)
        self.source = self.root/'source.zip'; self.source.write_bytes(b'SYNTHETIC source')
        self.roles = self.root/'roles.json'; self.roles.write_bytes(b'SYNTHETIC scoped grants')
        self.service = self.root/'pgservice.conf'; self.service.write_text('[test]\nhost=127.0.0.1\nport=5432\ndbname=scec_engagement_v820\n');self.service.chmod(0o600)
        self.plan = {'mode':'production','hostname':socket.gethostname(),'label':'TEST-MOCKED-CAPTURE',
                     'database':'scec_engagement_v820','revision':'850_001','db_host':'127.0.0.1','db_port':5432,
                     'db_user':'synthetic','pgservice':'test','pgservicefile':str(self.service),
                     'image':'sha256:'+'a'*64,'minimum_free_bytes':1,'output':str(self.root/'output.gpg'),
                     'source_archive_name':'source.zip','roles_metadata_name':'roles.json','capture_files':[
                         {'name':'source.zip','path':str(self.source),'sha256':c.digest(self.source)},
                         {'name':'roles.json','path':str(self.roles),'sha256':c.digest(self.roles)}]}
        self.pp=self.root/'plan.json';self.ap=self.root/'approval.json'
        self.approval={'operation':'SCEC_BACKUP_ONLY','hostname':socket.gethostname(),
                       'expires_utc':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),
                       'owner_approval_record':'SYNTHETIC OWNER','independent_verifier':'SYNTHETIC DISTINCT VERIFIER',
                       'scope_complete':True,'consistency_checkpoint':'SYNTHETIC','custody_verified':True,'destination_approved':True}
        self.save()
    def save(self):
        self.pp.write_text(json.dumps(self.plan));self.approval['plan_sha256']=c.digest(self.pp);self.ap.write_text(json.dumps(self.approval))
    def tearDown(self): self.temp.cleanup()
    def test_missing_approval(self):
        with self.assertRaises(FileNotFoundError):c.capture(self.pp,str(self.root/'absent'))
    def test_expired_approval(self):
        self.approval['expires_utc']='2000-01-01T00:00:00+00:00';self.save()
        with self.assertRaisesRegex(ValueError,'expired'):c.capture(self.pp,str(self.ap))
    def test_wrong_host(self):
        self.plan['hostname']='not-this-host';self.save()
        with self.assertRaisesRegex(ValueError,'wrong host'):c.capture(self.pp,str(self.ap))
    def test_wrong_database(self):
        self.plan['database']='unrelated';self.save()
        with self.assertRaisesRegex(ValueError,'unexpected database'):c.capture(self.pp,str(self.ap))
    def test_endpoint_mismatch(self):
        self.plan['db_host']='other';self.save()
        with self.assertRaisesRegex(ValueError,'endpoint mismatch'):c.capture(self.pp,str(self.ap))
    def mocked_run(self,args,**kw):
        if args[0]=='psql':return subprocess.CompletedProcess(args,0,b'BEGIN\n'+json.dumps({'database':'scec_engagement_v820','user':'synthetic','version':'160015','revision':'850_001'}).encode()+b'\nROLLBACK\n',b'')
        return subprocess.CompletedProcess(args,0,b'',b'')
    def test_source_drift(self):
        self.source.write_bytes(b'changed')
        with patch.object(c,'run',side_effect=self.mocked_run),self.assertRaisesRegex(ValueError,'baseline drift'):c.capture(self.pp,str(self.ap))
    def test_success_preserves_authority_and_cleanup(self):
        def stream(args,**kw):
            kw['stdout'].write(b'SYNTHETIC dump or image');return subprocess.CompletedProcess(args,0,b'',b'')
        def bundle(pp,ap):
            derived=json.loads(pp.read_text());receipt=json.loads(Path(ap).read_text())
            self.assertEqual(receipt['derived_from_plan_sha256'],c.digest(self.pp))
            self.assertEqual(receipt['plan_sha256'],c.digest(pp));self.assertEqual(len(derived['files']),4)
            for item in derived['files']:self.assertEqual(c.digest(item['path']),item['sha256'])
            return {'result':'PASS_MOCKED_CAPTURE'}
        with patch.object(c,'run',side_effect=self.mocked_run),patch.object(c.sp,'run',side_effect=stream),patch.object(c,'backup',side_effect=bundle):
            self.assertEqual(c.capture(self.pp,str(self.ap))['result'],'PASS_MOCKED_CAPTURE')
        self.assertFalse(list(self.root.glob('.scec-capture-*')))
    def test_dump_failure_cleans_staging(self):
        with patch.object(c,'run',side_effect=self.mocked_run),patch.object(c.sp,'run',side_effect=subprocess.CalledProcessError(1,['MOCK pg_dump'])):
            with self.assertRaises(subprocess.CalledProcessError):c.capture(self.pp,str(self.ap))
        self.assertFalse(list(self.root.glob('.scec-capture-*')));self.assertFalse((self.root/'output.gpg').exists())

if __name__=='__main__':unittest.main()
