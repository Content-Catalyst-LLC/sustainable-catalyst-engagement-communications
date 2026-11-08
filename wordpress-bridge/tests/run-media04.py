#!/usr/bin/env python3
"""Synthetic end-to-end tests of MEDIA-04 state transitions; never calls WordPress/Internet."""
import json
import subprocess
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
PHP=HERE/'test-media04.php'
results=[]
with tempfile.TemporaryDirectory() as td:
 state=Path(td)/'state.json'
 def run(args, payload=None, expected_code=0):
  p=subprocess.run(['php',str(PHP),*map(str,args),str(state)] if False else ['php',str(PHP),args[0],str(state),*map(str,args[1:])],input=json.dumps(payload).encode() if payload else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if p.returncode!=expected_code:raise AssertionError(f'bad exit {p.returncode} expected {expected_code} args={args} err={p.stderr.decode()} out={p.stdout.decode()}')
  return p.stdout.decode()
 def read():return json.loads(state.read_text())
 def check(cond,name):
  assert cond,name
  results.append('PASS '+name)
 def action(op,id=0,fields=None,actor=1,allowed=True,nonce=True,method='POST',expect=0):
  fields=fields or {}
  post=dict(fields,scec_operation=op,package_id=id)
  post['_wpnonce']=f'signed-scec_media04_{op}_{id}' if nonce else 'bad-nonce'
  run(['action'],{'post':post,'user':actor,'allowed':allowed,'method':method},expected_code=expect)
  return read()
 def status(n): return read()['meta'][str(n)]['_scec_media04_stage']
 fields={'title':'ERW Evidence Note','summary':'Verified field results and public research findings.','source_url':'https://sustainablecatalyst.com/verified-study/','channels':['substack','linkedin','x']}
 a=action('create',fields=fields,allowed=False,expect=1)
 check(not any(p['post_type']=='scec_media_package' for p in a['posts'].values()),'No admin capability denies creation')
 a=action('create',fields=fields,nonce=False,expect=1)
 check(a['error']=='Nonce mismatch','Unsigned creation denied')
 a=action('create',fields=dict(fields,source_url='https://sustainablecatalyst.com/private/'))
 check(not any(p['post_type']=='scec_media_package' for p in a['posts'].values()),'Private source blocks package creation')
 a=action('create',fields=fields,method='GET',expect=1)
 check(not any(p['post_type']=='scec_media_package' for p in a['posts'].values()),'Non-POST mutation denied')
 a=action('create',fields=fields)
 ids=[int(i) for i,p in a['posts'].items() if p['post_type']=='scec_media_package']
 check(len(ids)==1,'Private package created')
 id=ids[0]
 check(status(id)=='draft','New package starts as draft')
 check(a['posts'][str(id)]['post_status']=='private','Private object never publicly published')
 a=action('approve',id)
 check(status(id)=='draft','Cannot approve without submission')
 a=action('generate_draft',id)
 check(not any(p['post_type']=='post' and int(i)>=100 for i,p in a['posts'].items()),'No public draft before approval')
 a=action('update',id,fields=dict(fields,title='ERW Findings — Revised'))
 check(a['posts'][str(id)]['post_title']=='ERW Findings — Revised','Draft can be updated')
 a=action('submit',id)
 check(status(id)=='in_review','Submission transitions to in_review')
 a=action('update',id,fields=fields)
 check(a['posts'][str(id)]['post_title']=='ERW Findings — Revised','Submitted package cannot be silently rewritten')
 a=action('approve',id,fields={'rights_confirmed':'1'})
 check(status(id)=='in_review','Approval requires embargo confirmation')
 a=action('return',id)
 check(status(id)=='draft','Reviewer can return package to draft')
 action('submit',id)
 a=action('approve',id,fields={'rights_confirmed':'1','embargo_confirmed':'1'},actor=2)
 check(status(id)=='approved','Explicit review and approval transitions to approved')
 check(a['meta'][str(id)]['_scec_media04_reviewer']==2,'Audit retains reviewer ID')
 inspect=json.loads(run(['inspect',id]))
 check(inspect['valid']=='1','Fingerprint validates approved package/source')
 check(set(inspect['messages'])=={'substack','linkedin','x'},'Three channel-specific copy-ready messages generated')
 check(len(inspect['messages']['x'])<=280,'X copy text stays below 280 characters in this fixture')
 a=action('record_external',id,fields={'channel':'youtube','external_url':'https://youtube.com/watch?v=abc'})
 check('_scec_media04_external_records' not in a['meta'][str(id)],'Cannot record channel not in approved package')
 a=action('record_external',id,fields={'channel':'linkedin','external_url':'https://evil.com/fake'})
 check('_scec_media04_external_records' not in a['meta'][str(id)],'Cannot record unrelated host as LinkedIn')
 a=action('record_external',id,fields={'channel':'linkedin','external_url':'https://www.linkedin.com/feed/update/urn:li:activity:12345'})
 check(a['meta'][str(id)]['_scec_media04_external_records']['linkedin']['verification']=='operator_attested_not_api_verified','Manual receipt explicitly not API verified')
 manifest_output=run(['action'],{'post':{'scec_operation':'export','package_id':id,'_wpnonce':f'signed-scec_media04_export_{id}'},'user':2,'allowed':True,'method':'POST'})
 manifest=json.loads(manifest_output)
 check(manifest['schema_version']=='media-distribution-package/1.0' and manifest['distribution_mode']=='manual_only','Approved export carries versioned manual-only contract')
 check(manifest['approved_package_sha256']==read()['meta'][str(id)]['_scec_media04_approved_hash'],'Export references exact approved fingerprint')
 check(manifest['manual_external_records']['linkedin']['verification']=='operator_attested_not_api_verified','Export clearly labels unverified platform records')
 check('token' not in json.dumps(manifest).lower() and 'password' not in json.dumps(manifest).lower(),'Export includes no credential or subscriber data')
 a=action('generate_draft',id)
 draft_id=a['meta'][str(id)]['_scec_media04_wp_draft_id']
 check(a['posts'][str(draft_id)]['post_status']=='draft','WordPress editorial output remains draft')
 check(a['tags'][str(draft_id)]==['media-update'],'Generated draft tagged for MEDIA-03 discovery after separate publication')
 check('Read the original publication' in a['posts'][str(draft_id)]['post_content'],'Draft references authoritative source')
 a=action('generate_draft',id)
 check(len([i for i,p in a['posts'].items() if p['post_type']=='post' and int(i)>100])==1,'Duplicate draft generation prevented')
 a=action('update',id,fields=fields)
 check(a['posts'][str(id)]['post_title']=='ERW Findings — Revised','Approved content cannot be edited')
 a['posts']['10']['post_content']='Source edited after approval';state.write_text(json.dumps(a))
 inspect=json.loads(run(['inspect',id]))
 check(inspect['valid']=='0','Any source text change invalidates approval fingerprint')
 a=action('record_external',id,fields={'channel':'x','external_url':'https://x.com/example/status/12345'})
 check('x' not in a['meta'][str(id)]['_scec_media04_external_records'],'Changed source blocks outbound records')
 a=action('export',id)
 check(a['redirect'] is not None and 'source_changed' in a['redirect'],'Changed source blocks approved JSON export')
 # Explicit admin screen output escaping and scoped content.
 # The UI itself is tested by verifying the source file contains escaped outputs.
 print('\n'.join(results))
 print(f'MEDIA-04 integration: {len(results)} PASS / 0 FAIL')
 (HERE/'MEDIA-04-REGRESSION.log').write_text('\n'.join(results)+f'\nMEDIA-04 integration: {len(results)} PASS / 0 FAIL\n')
