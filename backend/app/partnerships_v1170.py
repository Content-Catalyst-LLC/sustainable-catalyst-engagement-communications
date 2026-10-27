"""Synthetic partner routing decisions; no partner export or federation."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StrictBool, field_validator, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, opaque
from .offline_staging import scope, seal
from .research_distribution_v1100 import DistributionPreview, preview as distribution_preview

router=APIRouter(prefix='/v1/partnerships',tags=['partnerships-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_PARTNERS_STAGING_ENABLED')
BLOCKED_ACTIONS=('export','deliver','federate','token-exchange','link-identity','publish','send','activate','delete')
License=Literal['unknown','public-domain','cc-by','cc-by-sa','restricted']
Classification=Literal['public','internal','restricted']


class Partner(Fixture):
    partner_ref: str = Field(min_length=3,max_length=96)
    institution_ref: str = Field(min_length=3,max_length=96)
    kind: Literal['academic','research','policy','community']
    accepted_licenses: list[License] = Field(min_length=1,max_length=5)
    allowed_classifications: list[Classification] = Field(min_length=1,max_length=3)
    institutional_reviewed: StrictBool=False
    rights_reviewed: StrictBool=False
    suppressed: StrictBool=False

    @field_validator('partner_ref','institution_ref')
    @classmethod
    def refs(cls,v):return opaque(v)

    @field_validator('accepted_licenses','allowed_classifications')
    @classmethod
    def unique(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Duplicate policy value')
        return v


class Artifact(Fixture):
    object_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    object_kind: Literal['research-article','research-package','publication','dataset','methodology']
    source_refs: list[str] = Field(min_length=1,max_length=12)
    license: License='unknown'
    classification: Classification='restricted'
    rights_reviewed: StrictBool=False
    editorial_reviewed: StrictBool=False
    privacy_reviewed: StrictBool=False
    source_integrity_reviewed: StrictBool=False
    distribution_reviewed: StrictBool=False

    @field_validator('object_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('source_refs')
    @classmethod
    def sources(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Repeated source')
        return [opaque(x) for x in v]


class PartnerPackage(Fixture):
    package_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    institution_ref: str = Field(min_length=3,max_length=96)
    artifacts: list[Artifact] = Field(min_length=1,max_length=10)
    partners: list[Partner] = Field(min_length=1,max_length=30)

    @field_validator('package_ref','institution_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @model_validator(mode='after')
    def bounded(self):
        if any(x.organization_id!=self.organization_id for x in [*self.artifacts,*self.partners]):raise ValueError('Cross-tenant package')
        if len({x.object_ref for x in self.artifacts})!=len(self.artifacts):raise ValueError('Duplicate object')
        if len({x.partner_ref for x in self.partners})!=len(self.partners):raise ValueError('Duplicate partner')
        return self


def plan(package:PartnerPackage,tenant:str):
    if package.organization_id!=tenant:raise ValueError('Tenant mismatch')
    manifests=[]
    for a in sorted(package.artifacts,key=lambda x:x.object_ref):
        rights='open-license' if a.license in ('public-domain','cc-by','cc-by-sa') and a.rights_reviewed else 'not-reviewed'
        contract=DistributionPreview(object_ref=a.object_ref,revision=a.revision,object_kind=a.object_kind,targets=['institutional-newsroom'],source_refs=a.source_refs,rights_basis=rights,editorial_reviewed=a.editorial_reviewed,privacy_reviewed=a.privacy_reviewed,source_integrity_reviewed=a.source_integrity_reviewed,distribution_approved=a.distribution_reviewed)
        manifest=distribution_preview(contract,tenant)
        manifests.append({'object_ref':a.object_ref,'revision':a.revision,'license':a.license,'classification':a.classification,'source_manifest':manifest})
    decisions=[]
    for p in sorted(package.partners,key=lambda x:x.partner_ref):
        reasons=set()
        if p.suppressed:reasons.add('partner-suppressed')
        if not p.institutional_reviewed:reasons.add('institutional-review-required')
        if not p.rights_reviewed:reasons.add('partner-rights-review-required')
        for a in package.artifacts:
            if not all(getattr(a,g) for g in ('rights_reviewed','editorial_reviewed','privacy_reviewed','source_integrity_reviewed','distribution_reviewed')):reasons.add('artifact-review-required')
            if a.license=='unknown':reasons.add('license-unknown')
            if a.license not in p.accepted_licenses:reasons.add('license-not-accepted')
            if a.classification not in p.allowed_classifications:reasons.add('access-classification-denied')
            if a.classification=='restricted' or a.license=='restricted':reasons.add('restricted-artifact-no-routing')
            if p.institution_ref!=package.institution_ref and a.classification!='public':reasons.add('institution-boundary-denied')
        decisions.append({'partner_ref':p.partner_ref,'institution_ref':p.institution_ref,'kind':p.kind,'eligible_for_synthetic_plan_only':not reasons,'review_flags':sorted(reasons),'data_exported':False,'federation_authorized':False})
    normalized=package.model_dump(mode='json')
    normalized['artifacts'].sort(key=lambda x:x['object_ref']);normalized['partners'].sort(key=lambda x:x['partner_ref'])
    for a in normalized['artifacts']:a['source_refs'].sort()
    for p in normalized['partners']:p['accepted_licenses'].sort();p['allowed_classifications'].sort()
    return seal({'mode':'offline-synthetic-partner-routing','fixture':normalized,'distribution_manifests':manifests,'routing_decisions':decisions,'data_exported':False,'federation_authorized':False,'partner_delivery_enabled':False},tenant,'11.7.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-synthetic-partner-routing','data_exported':False,'partner_delivery_enabled':False},str(tenant),'11.7.0')


@router.post('/preview')
def preview(payload:PartnerPackage,tenant=Depends(_scope)):
    try:return plan(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/export')
@router.post('/deliver')
@router.post('/federate')
@router.post('/token-exchange')
@router.post('/link-identity')
@router.post('/publish')
@router.post('/send')
@router.post('/activate')
@router.post('/delete')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live partner operations disabled')
