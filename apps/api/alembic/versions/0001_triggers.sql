-- Invariants enforced in the database (D-001 #5). Statements are separated by a marker line.
-- Error messages start with a stable prefix the service layer maps to API codes.

CREATE INDEX ix_content_block_revision ON content_block (revision_id, position) WHERE deleted_at IS NULL;
-- split
CREATE INDEX ix_content_block_parent ON content_block (parent_id);
-- split
CREATE INDEX ix_provenance_link_block ON provenance_link (block_id);
-- split
CREATE INDEX ix_provenance_link_anchor ON provenance_link (anchor_id);
-- split
CREATE INDEX ix_block_dependency_target ON block_dependency (depends_on_block_id);
-- split
CREATE INDEX ix_review_event_block ON review_event (block_id, created_at DESC);
-- split
CREATE INDEX ix_validation_result_block ON validation_result (block_id, created_at DESC);
-- split
CREATE INDEX ix_transformation_event_block ON transformation_event (block_id, created_at DESC);
-- split
CREATE INDEX ix_source_anchor_revision ON source_anchor (source_revision_id);
-- split
CREATE INDEX ix_attempt_assignment ON student_attempt (assignment_id, student_id);
-- split
CREATE INDEX ix_audit_log_created ON audit_log (created_at DESC);
-- split
CREATE INDEX ix_session_user ON session (user_id);
-- split
-- one running job per revision (D-001 #10)
CREATE UNIQUE INDEX ux_generation_job_active ON generation_job (revision_id) WHERE status IN ('QUEUED', 'RUNNING');
-- split

CREATE FUNCTION pc_deny() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'APPEND_ONLY: % on % is not allowed', TG_OP, TG_TABLE_NAME;
END $$;
-- split
CREATE TRIGGER tg_append_only BEFORE UPDATE OR DELETE ON transformation_event FOR EACH ROW EXECUTE FUNCTION pc_deny();
-- split
CREATE TRIGGER tg_append_only BEFORE UPDATE OR DELETE ON validation_result FOR EACH ROW EXECUTE FUNCTION pc_deny();
-- split
CREATE TRIGGER tg_append_only BEFORE UPDATE OR DELETE ON review_event FOR EACH ROW EXECUTE FUNCTION pc_deny();
-- split
CREATE TRIGGER tg_append_only BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION pc_deny();
-- split
CREATE TRIGGER tg_append_only BEFORE UPDATE OR DELETE ON student_attempt FOR EACH ROW EXECUTE FUNCTION pc_deny();
-- split

-- Sources are immutable once stored (anchors fully; revisions except extract_status / locked_at).
CREATE FUNCTION pc_source_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'IMMUTABLE_SOURCE: delete on % is not allowed', TG_TABLE_NAME;
  END IF;
  IF TG_TABLE_NAME = 'source_anchor' THEN
    RAISE EXCEPTION 'IMMUTABLE_SOURCE: update on % is not allowed', TG_TABLE_NAME;
  END IF;
  -- plpgsql does not short-circuit OR, so the source_revision-only fields are checked after the exit above
  IF (NEW.asset_id, NEW.version, NEW.sha256, NEW.mime, NEW.file_uri)
     IS DISTINCT FROM (OLD.asset_id, OLD.version, OLD.sha256, OLD.mime, OLD.file_uri) THEN
    RAISE EXCEPTION 'IMMUTABLE_SOURCE: update on % is not allowed', TG_TABLE_NAME;
  END IF;
  RETURN NEW;
END $$;
-- split
CREATE TRIGGER tg_immutable BEFORE UPDATE OR DELETE ON source_revision FOR EACH ROW EXECUTE FUNCTION pc_source_immutable();
-- split
CREATE TRIGGER tg_immutable BEFORE UPDATE OR DELETE ON source_anchor FOR EACH ROW EXECUTE FUNCTION pc_source_immutable();
-- split

-- Published / superseded revisions are frozen: no change to blocks, links or lesson sources.
CREATE FUNCTION pc_revision_is_locked(rid uuid) RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT COALESCE((SELECT state IN ('PUBLISHED', 'SUPERSEDED') FROM lesson_revision WHERE id = rid), false)
$$;
-- split
CREATE FUNCTION pc_block_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE last_event record;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'NO_HARD_DELETE: use deleted_at on content_block';
  END IF;
  IF pc_revision_is_locked(NEW.revision_id) OR (TG_OP = 'UPDATE' AND pc_revision_is_locked(OLD.revision_id)) THEN
    RAISE EXCEPTION 'REVISION_LOCKED: revision is not editable';
  END IF;
  -- APPROVED <=> the latest review event is an APPROVE for the block's current content_hash
  IF NEW.review_status = 'APPROVED' THEN
    SELECT action, content_hash INTO last_event
      FROM review_event WHERE block_id = NEW.id ORDER BY created_at DESC LIMIT 1;
    IF NOT FOUND OR last_event.action <> 'APPROVE' OR last_event.content_hash <> NEW.content_hash THEN
      RAISE EXCEPTION 'APPROVAL_INVALID: no matching APPROVE review_event for current content_hash';
    END IF;
  END IF;
  RETURN NEW;
END $$;
-- split
CREATE TRIGGER tg_block_guard BEFORE INSERT OR UPDATE OR DELETE ON content_block FOR EACH ROW EXECUTE FUNCTION pc_block_guard();
-- split
CREATE FUNCTION pc_link_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid uuid;
BEGIN
  SELECT revision_id INTO rid FROM content_block WHERE id = COALESCE(NEW.block_id, OLD.block_id);
  IF pc_revision_is_locked(rid) THEN
    RAISE EXCEPTION 'REVISION_LOCKED: revision is not editable';
  END IF;
  -- PR-06: a VERIFIED link must point at an anchor of a source attached to the block's revision
  IF TG_OP <> 'DELETE' AND NEW.status = 'VERIFIED' AND NOT EXISTS (
       SELECT 1 FROM source_anchor a JOIN lesson_source ls ON ls.source_revision_id = a.source_revision_id
        WHERE a.id = NEW.anchor_id AND ls.lesson_revision_id = rid) THEN
    RAISE EXCEPTION 'ANCHOR_NOT_IN_LESSON: anchor does not belong to the lesson sources';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
-- split
CREATE TRIGGER tg_link_guard BEFORE INSERT OR UPDATE OR DELETE ON provenance_link FOR EACH ROW EXECUTE FUNCTION pc_link_guard();
-- split
CREATE FUNCTION pc_lesson_source_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF pc_revision_is_locked(COALESCE(NEW.lesson_revision_id, OLD.lesson_revision_id)) THEN
    RAISE EXCEPTION 'REVISION_LOCKED: revision is not editable';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
-- split
CREATE TRIGGER tg_lesson_source_guard BEFORE INSERT OR UPDATE OR DELETE ON lesson_source FOR EACH ROW EXECUTE FUNCTION pc_lesson_source_guard();
-- split

-- State never goes backwards once published.
CREATE FUNCTION pc_revision_transition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (OLD.state = 'PUBLISHED' AND NEW.state NOT IN ('PUBLISHED', 'SUPERSEDED'))
     OR (OLD.state = 'SUPERSEDED' AND NEW.state <> 'SUPERSEDED') THEN
    RAISE EXCEPTION 'INVALID_STATE_TRANSITION: % -> %', OLD.state, NEW.state;
  END IF;
  RETURN NEW;
END $$;
-- split
CREATE TRIGGER tg_transition BEFORE UPDATE ON lesson_revision FOR EACH ROW EXECUTE FUNCTION pc_revision_transition();
-- split

-- PR-05: snapshot is immutable; only state / withdraw_reason may change, and withdrawal is final.
CREATE FUNCTION pc_snapshot_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'SNAPSHOT_IMMUTABLE: delete is not allowed';
  END IF;
  IF (NEW.snapshot, NEW.snapshot_hash, NEW.lesson_revision_id, NEW.published_by)
     IS DISTINCT FROM (OLD.snapshot, OLD.snapshot_hash, OLD.lesson_revision_id, OLD.published_by) THEN
    RAISE EXCEPTION 'SNAPSHOT_IMMUTABLE: snapshot cannot be changed';
  END IF;
  IF OLD.state = 'WITHDRAWN' AND NEW.state <> 'WITHDRAWN' THEN
    RAISE EXCEPTION 'INVALID_STATE_TRANSITION: withdrawn version cannot be reactivated';
  END IF;
  RETURN NEW;
END $$;
-- split
CREATE TRIGGER tg_snapshot BEFORE UPDATE OR DELETE ON published_version FOR EACH ROW EXECUTE FUNCTION pc_snapshot_guard();
-- split

-- Two DB roles (D-001 #5). Created NOLOGIN; ops sets LOGIN/PASSWORD (see RUNBOOK).
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'preclass_migrator') THEN CREATE ROLE preclass_migrator NOLOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'preclass_app') THEN CREATE ROLE preclass_app NOLOGIN; END IF;
END $$;
-- split
GRANT USAGE ON SCHEMA public TO preclass_app;
-- split
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO preclass_app;
-- split
REVOKE ALL ON alembic_version FROM preclass_app;
-- split
REVOKE UPDATE, DELETE ON transformation_event, validation_result, review_event, audit_log, source_anchor, student_attempt FROM preclass_app;
-- split
REVOKE DELETE ON content_block, source_revision, published_version FROM preclass_app;
