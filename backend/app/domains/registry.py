from ..contracts.models import Domain, DomainDescriptor

DOMAINS = (
    DomainDescriptor(name=Domain.support, status='legacy_adapter_pending', owner='support', legacy_source='support-feedback v7.8.1', notes='Existing FastAPI remains authoritative'),
    DomainDescriptor(name=Domain.contacts, status='migration_pending', owner='contacts', legacy_source='engagement-intake v2.0.2', notes='Private WordPress inquiries remain authoritative'),
    DomainDescriptor(name=Domain.advisory, status='migration_pending', owner='advisory', legacy_source='engagement-intake v2.0.2', notes='Preserve proposals, billing and access control'),
    DomainDescriptor(name=Domain.newsletters, status='planned_v9', owner='newsletters', notes='Substack-friendly export contract'),
    DomainDescriptor(name=Domain.forms, status='planned_v10', owner='forms', legacy_source='support-feedback survey modules'),
    DomainDescriptor(name=Domain.tests, status='planned_v11', owner='tests'),
    DomainDescriptor(name=Domain.assessments, status='planned_v12', owner='assessments'),
    DomainDescriptor(name=Domain.analytics, status='planned_v13', owner='analytics'),
    DomainDescriptor(name=Domain.integrations, status='foundation', owner='integrations'),
)
