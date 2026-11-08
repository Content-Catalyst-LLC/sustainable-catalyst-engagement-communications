"""MEDIA-06: fail-closed, tenant-scoped editorial operations (no delivery).
Separate from MEDIA-05. Source and human identities are WordPress attestations;
there is no federated user authentication in this candidate.
"""
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
from dataclasses import dataclass
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (JSON, Column, MetaData, String, Table, UniqueConstraint,
                        create_engine, select, insert, update)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import jwt
from .media_bridge_v1250 import MediaBridgePackage, assessed_preview
from .newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS

meta = MetaData()
packages = Table('media06_packages', meta,
    Column('id', String(36), primary_key=True),
    Column('organization_id', String(36), nullable=False, index=True),
    Column('package_ref', String(32), nullable=False),
    Column('approved_hash', String(64), nullable=False),
    Column('source_hash', String(64), nullable=False),
    Column('input_hash', String(64), nullable=False),
    Column('idempotency_key', String(64), nullable=False),
    Column('submitted_by', String(64), nullable=False),
    Column('state', String(20), nullable=False),
    Column('payload', JSON, nullable=False),
    Column('created_at', String(40), nullable=False),
    UniqueConstraint('organization_id', 'idempotency_key', name='uq_media06_idempotency'),
    UniqueConstraint('organization_id', 'package_ref', 'approved_hash', name='uq_media06_revision'),
)
reviews = Table('media06_reviews', meta,
    Column('id', String(36), primary_key=True),
    Column('organization_id', String(36), nullable=False),
    Column('package_id', String(36), nullable=False),
    Column('actor_ref', String(64), nullable=False),
    Column('decision', String(12), nullable=False),
    Column('created_at', String(40), nullable=False),
    UniqueConstraint('organization_id', 'package_id', 'actor_ref', name='uq_media06_reviewer'),
)
audit = Table('media06_audit', meta,
    Column('id', String(36), primary_key=True),
    Column('organization_id', String(36), nullable=False),
    Column('package_id', String(36), nullable=False),
    Column('action', String(30), nullable=False),
    Column('actor_ref', String(64), nullable=False),
    Column('created_at', String(40), nullable=False),
    Column('details', JSON, nullable=False),
)
ACTOR_RE = re.compile(r'^wp:user:[1-9][0-9]{0,11}$')
HEX = re.compile(r'^[a-f0-9]{64}$')
KEY_ID = re.compile(r'^[A-Za-z0-9_-]{3,60}$')

class SafeRoute(APIRoute):
    def get_route_handler(self):
        delegate = super().get_route_handler()
        async def sanitized(request):
            try:
                return await delegate(request)
            except RequestValidationError:
                raise HTTPException(422, 'Invalid Media operations request') from None
        return sanitized

router = APIRouter(prefix='/v1/media-ops', tags=['media06-private-operations'], route_class=SafeRoute)

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def canonical_org(value):
    try:
        org = UUID(value)
        if org.int == 0 or str(org) != value:
            raise ValueError()
        return value
    except (TypeError, ValueError):
        raise HTTPException(403, 'Invalid organization') from None

def active():
    if os.getenv('SCEC_MEDIA06_ENABLED', '0') != '1' or os.getenv('SCEC_ENV') != 'staging':
        raise HTTPException(503, 'MEDIA-06 staging disabled')
    if any(os.getenv(flag, '0') != '0' for flag in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS)):
        raise HTTPException(503, 'Unsafe production feature flag')
    if os.getenv('SCEC_IDENTITY_MODE') != 'bound':
        raise HTTPException(503, 'Bound identity mode required')

@dataclass(frozen=True)
class Service:
    organization_id: str
    subject: str

async def signed_service(request: Request, authorization: str | None = Header(default=None),
                         x_scec_organization_id: str | None = Header(default=None)) -> Service:
    active()
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Signed service assertion required')
    token = authorization[7:]
    if len(token) > 8192:
        raise HTTPException(401, 'Invalid assertion')
    keyfile = os.getenv('SCEC_MEDIA06_PUBLIC_KEYS_FILE', '')
    issuer = os.getenv('SCEC_MEDIA06_ISSUER', '')
    if not keyfile.startswith('/') or not issuer.startswith('https://') or not issuer.endswith('.com'):
        raise HTTPException(503, 'Service identity not provisioned')
    try:
        path = Path(keyfile)
        if not path.is_file() or path.stat().st_mode & 0o022:
            raise ValueError()
        keys = json.loads(path.read_text())
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
        if header.get('alg') != 'RS256' or not isinstance(kid, str) or not KEY_ID.fullmatch(kid):
            raise ValueError()
        if not isinstance(keys, dict) or kid not in keys or len(keys) > 5:
            raise ValueError()
        claims = jwt.decode(token, keys[kid], algorithms=['RS256'],
                            audience='scec-media06', issuer=issuer,
                            options={'require': ['iss','aud','sub','org','iat','nbf','exp','jti','method','path','body_sha256']},
                            leeway=5)
        current = int(time.time())
        if type(claims['iat']) is not int or type(claims['exp']) is not int or type(claims['nbf']) is not int:
            raise ValueError()
        if not (current - 60 <= claims['iat'] <= current + 5 and
                claims['exp'] - claims['iat'] <= 120 and claims['nbf'] <= claims['iat']):
            raise ValueError()
        if claims['sub'] != 'wordpress:media-ops' or not isinstance(claims['jti'], str) or len(claims['jti']) > 64:
            raise ValueError()
        org = canonical_org(claims['org'])
        allow = {s.strip() for s in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',')}
        if org not in allow or x_scec_organization_id != org:
            raise HTTPException(403, 'Organization not authorized')
        target = request.url.path + ('?' + request.url.query if request.url.query else '')
        digest = hashlib.sha256(await request.body()).hexdigest()
        if claims['method'] != request.method or claims['path'] != target or claims['body_sha256'] != digest:
            raise ValueError()
        return Service(org, claims['sub'])
    except HTTPException:
        raise
    except (OSError, ValueError, KeyError, TypeError, jwt.PyJWTError):
        raise HTTPException(401, 'Invalid or expired service assertion') from None

def require_storage():
    if os.getenv('SCEC_MEDIA06_STORAGE_ENABLED', '0') != '1':
        raise HTTPException(503, 'MEDIA-06 persistence disabled')
    url = os.getenv('SCEC_MEDIA06_DATABASE_URL', '')
    if not url.startswith('postgresql+psycopg://') or '/scec_engagement_' not in url.split('?',1)[0]:
        raise HTTPException(503, 'Dedicated Engagement PostgreSQL required')
    return url

def database():
    url = require_storage()
    engine = create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=0)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()

class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    package: MediaBridgePackage
    submitted_by: str = Field(min_length=9, max_length=64, pattern=r'^wp:user:[1-9][0-9]{0,11}$')
    idempotency_key: str = Field(min_length=64, max_length=64, pattern=r'^[a-f0-9]{64}$')

class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    actor_ref: str = Field(min_length=9, max_length=64, pattern=r'^wp:user:[1-9][0-9]{0,11}$')
    decision: str = Field(pattern=r'^(approve|reject)$')
    approved_package_sha256: str = Field(min_length=64, max_length=64, pattern=r'^[a-f0-9]{64}$')

def record_audit(db, org, pkg_id, action, actor, details):
    db.execute(insert(audit).values(id=str(uuid4()), organization_id=org, package_id=pkg_id,
                action=action, actor_ref=actor, created_at=now_utc(), details=details))

def safe_package(row):
    return {'release':'MEDIA-06', 'organization_id':row['organization_id'],
            'package_id':row['id'], 'package_ref':row['package_ref'],
            'approved_package_sha256':row['approved_hash'],
            'state':row['state'], 'submitted_by_attested':row['submitted_by'],
            'created_at_utc':row['created_at'],
            'publishing_enabled':False, 'sending_enabled':False, 'production_certified':False,
            'wordpress_actor_identity_independently_verified':False}

def find_package(db, org, pkg_id):
    result = db.execute(select(packages).where(
        packages.c.id==pkg_id,packages.c.organization_id==org)).mappings().first()
    if result is None:
        raise HTTPException(404, 'Media package not found')
    return result

def register(db: Session, org: str, submission: Submission):
    if submission.package.organization_id != org:
        raise HTTPException(403, 'Organization mismatch')
    try:
        receipt = assessed_preview(submission.package, org)
    except ValueError:
        raise HTTPException(422, 'Invalid Media package authority') from None
    pkg = submission.package
    current = db.execute(select(packages).where(
        packages.c.organization_id==org,
        packages.c.idempotency_key==submission.idempotency_key)).mappings().first()
    if current:
        if current['input_hash']==receipt['input_sha256'] and current['submitted_by']==submission.submitted_by:
            return safe_package(current)
        raise HTTPException(409, 'Idempotency key reused for different package')
    duplicate = db.execute(select(packages).where(
        packages.c.organization_id==org,packages.c.package_ref==pkg.package_ref,
        packages.c.approved_hash==pkg.approved_package_sha256)).mappings().first()
    if duplicate:
        raise HTTPException(409, 'Revision exists with different idempotency key')
    pkg_id = str(uuid4())
    with db.begin_nested():
        previous = db.execute(select(packages).where(
            packages.c.organization_id==org,packages.c.package_ref==pkg.package_ref,
            packages.c.state.in_(['in_review','approved']))).mappings().all()
        for p in previous:
            db.execute(update(packages).where(packages.c.id==p['id']).values(state='superseded'))
            record_audit(db,org,p['id'],'superseded',submission.submitted_by,{'by_digest':pkg.approved_package_sha256})
        db.execute(insert(packages).values(id=pkg_id,organization_id=org,
            package_ref=pkg.package_ref,approved_hash=pkg.approved_package_sha256,
            source_hash=pkg.source_content_sha256,input_hash=receipt['input_sha256'],
            idempotency_key=submission.idempotency_key,submitted_by=submission.submitted_by,
            state='in_review',payload=pkg.model_dump(mode='json'),created_at=now_utc()))
        record_audit(db,org,pkg_id,'registered',submission.submitted_by,
                     {'input_sha256':receipt['input_sha256']})
    db.commit()
    return safe_package(find_package(db,org,pkg_id))

def review(db: Session, org: str, pkg_id: str, decision: Decision):
    row = find_package(db,org,pkg_id)
    if row['state'] != 'in_review':
        raise HTTPException(409, 'Package not in review')
    if row['approved_hash'] != decision.approved_package_sha256:
        raise HTTPException(409, 'Review fingerprint does not match')
    if decision.actor_ref == row['submitted_by']:
        raise HTTPException(403, 'Submitter cannot review their own package')
    prior = db.execute(select(reviews).where(reviews.c.organization_id==org,
        reviews.c.package_id==pkg_id,reviews.c.actor_ref==decision.actor_ref)).first()
    if prior:
        raise HTTPException(409, 'Reviewer already decided')
    with db.begin_nested():
        db.execute(insert(reviews).values(id=str(uuid4()),organization_id=org,
            package_id=pkg_id,actor_ref=decision.actor_ref,decision=decision.decision,
            created_at=now_utc()))
        count = db.execute(select(reviews.c.actor_ref).where(
            reviews.c.organization_id==org,reviews.c.package_id==pkg_id,
            reviews.c.decision=='approve')).all()
        state = 'rejected' if decision.decision == 'reject' else ('approved' if len(count)>=2 else 'in_review')
        if state != 'in_review':
            db.execute(update(packages).where(packages.c.id==pkg_id,packages.c.organization_id==org).values(state=state))
        record_audit(db,org,pkg_id,'reviewed',decision.actor_ref,
                     {'decision':decision.decision,'result_state':state,'approval_count':len(count)})
    db.commit()
    return safe_package(find_package(db,org,pkg_id))

@router.get('/status')
def status(svc: Service=Depends(signed_service)):
    return {'release':'MEDIA-06','organization_id':svc.organization_id,
            'mode':'staging-operational-review', 'persistence_enabled':os.getenv('SCEC_MEDIA06_STORAGE_ENABLED')=='1',
            'signed_request_identity':True,'human_identity_federated':False,
            'publishing_enabled':False,'sending_enabled':False,'production_certified':False}

@router.post('/packages',status_code=201)
def create_package(submission: Submission, svc: Service=Depends(signed_service), db:Session=Depends(database)):
    try:
        return register(db,svc.organization_id,submission)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Conflicting Media package registration') from None

@router.get('/packages/{package_id}')
def read_package(package_id:str,svc:Service=Depends(signed_service),db:Session=Depends(database)):
    return safe_package(find_package(db,svc.organization_id,package_id))

@router.post('/packages/{package_id}/reviews')
def decide(package_id:str,decision:Decision,svc:Service=Depends(signed_service),db:Session=Depends(database)):
    try:
        return review(db,svc.organization_id,package_id,decision)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Conflicting Media review') from None

@router.get('/packages/{package_id}/audit')
def history(package_id:str,svc:Service=Depends(signed_service),db:Session=Depends(database)):
    find_package(db,svc.organization_id,package_id)
    rows=db.execute(select(audit).where(audit.c.organization_id==svc.organization_id,
        audit.c.package_id==package_id).order_by(audit.c.created_at,audit.c.id).limit(100)).mappings().all()
    return {'release':'MEDIA-06','organization_id':svc.organization_id,'package_id':package_id,
            'items':[{'action':r['action'],'actor_attested':r['actor_ref'],
                     'at_utc':r['created_at'],'details':r['details']} for r in rows],
            'human_identity_federated':False}

@router.get('/packages/{package_id}/reconcile')
def reconcile(package_id:str,approved_sha256:str,svc:Service=Depends(signed_service),db:Session=Depends(database)):
    if not HEX.fullmatch(approved_sha256):
        raise HTTPException(422,'SHA-256 required')
    row=find_package(db,svc.organization_id,package_id)
    match=row['approved_hash']==approved_sha256
    return {'release':'MEDIA-06','organization_id':svc.organization_id,
            'package_id':package_id,'fingerprint_matches':match,
            'state':row['state'],'requires_new_review':not match or row['state']!='approved',
            'source_independently_verified':False,'external_delivery_enabled':False}

@router.post('/publish')
@router.post('/send')
@router.post('/schedule')
@router.post('/enqueue')
def blocked(svc: Service=Depends(signed_service)):
    raise HTTPException(503,'MEDIA-06 external delivery unavailable')
