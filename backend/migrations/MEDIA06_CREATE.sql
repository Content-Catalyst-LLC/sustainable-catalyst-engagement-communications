-- MEDIA-06 reviewed metadata only. Operator-applied, dedicated Engagement PostgreSQL only.
-- Preconditions: backed up dedicated DB, approved migration, standby rollback.
-- No automatic application; leaves existing Engagement tables untouched.
BEGIN;
DO $gate$
BEGIN
    IF current_database() NOT LIKE 'scec\_engagement\_%' ESCAPE '\' THEN
        RAISE EXCEPTION 'MEDIA-06 refuses non-dedicated Engagement database';
    END IF;
END $gate$;

CREATE TABLE media06_packages (
    id varchar(36) PRIMARY KEY,
    organization_id varchar(36) NOT NULL,
    package_ref varchar(32) NOT NULL,
    approved_hash varchar(64) NOT NULL,
    source_hash varchar(64) NOT NULL,
    input_hash varchar(64) NOT NULL,
    idempotency_key varchar(64) NOT NULL,
    submitted_by varchar(64) NOT NULL,
    state varchar(20) NOT NULL,
    payload jsonb NOT NULL,
    created_at varchar(40) NOT NULL,
    CONSTRAINT uq_media06_idempotency UNIQUE (organization_id, idempotency_key),
    CONSTRAINT uq_media06_revision UNIQUE (organization_id, package_ref, approved_hash),
    CONSTRAINT uq_media06_pkg_org_id UNIQUE (organization_id, id),
    CONSTRAINT ck_media06_state CHECK (state IN ('in_review','approved','rejected','superseded'))
);
CREATE INDEX ix_media06_packages_organization_id ON media06_packages (organization_id);
CREATE INDEX ix_media06_pkg_reference ON media06_packages (organization_id, package_ref);

CREATE TABLE media06_reviews (
    id varchar(36) PRIMARY KEY,
    organization_id varchar(36) NOT NULL,
    package_id varchar(36) NOT NULL,
    actor_ref varchar(64) NOT NULL,
    decision varchar(12) NOT NULL,
    created_at varchar(40) NOT NULL,
    CONSTRAINT fk_media06_review_package FOREIGN KEY (organization_id, package_id)
        REFERENCES media06_packages (organization_id, id) ON DELETE RESTRICT,
    CONSTRAINT uq_media06_reviewer UNIQUE (organization_id, package_id, actor_ref),
    CONSTRAINT ck_media06_decision CHECK (decision IN ('approve','reject'))
);
CREATE INDEX ix_media06_review_package ON media06_reviews (organization_id, package_id);

CREATE TABLE media06_audit (
    id varchar(36) PRIMARY KEY,
    organization_id varchar(36) NOT NULL,
    package_id varchar(36) NOT NULL,
    action varchar(30) NOT NULL,
    actor_ref varchar(64) NOT NULL,
    created_at varchar(40) NOT NULL,
    details jsonb NOT NULL,
    CONSTRAINT fk_media06_audit_package FOREIGN KEY (organization_id, package_id)
        REFERENCES media06_packages (organization_id, id) ON DELETE RESTRICT
);
CREATE INDEX ix_media06_audit_package ON media06_audit (organization_id, package_id, created_at);

-- Harden operator-managed audit/reviewer evidence against mutation by the app role.
CREATE FUNCTION media06_reject_evidence_mutation() RETURNS trigger LANGUAGE plpgsql AS $
BEGIN
    RAISE EXCEPTION 'MEDIA-06 evidence is append-only';
END $;
CREATE TRIGGER media06_audit_immutable BEFORE UPDATE OR DELETE ON media06_audit
    FOR EACH ROW EXECUTE FUNCTION media06_reject_evidence_mutation();
CREATE TRIGGER media06_reviews_immutable BEFORE UPDATE OR DELETE ON media06_reviews
    FOR EACH ROW EXECUTE FUNCTION media06_reject_evidence_mutation();

COMMIT;
