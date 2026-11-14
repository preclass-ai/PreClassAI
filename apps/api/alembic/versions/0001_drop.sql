DROP TABLE IF EXISTS "student_attempt" CASCADE;
-- split
DROP TABLE IF EXISTS "validation_result" CASCADE;
-- split
DROP TABLE IF EXISTS "transformation_event" CASCADE;
-- split
DROP TABLE IF EXISTS "review_event" CASCADE;
-- split
DROP TABLE IF EXISTS "provenance_link" CASCADE;
-- split
DROP TABLE IF EXISTS "block_dependency" CASCADE;
-- split
DROP TABLE IF EXISTS "assignment" CASCADE;
-- split
DROP TABLE IF EXISTS "source_anchor" CASCADE;
-- split
DROP TABLE IF EXISTS "published_version" CASCADE;
-- split
DROP TABLE IF EXISTS "lesson_source" CASCADE;
-- split
DROP TABLE IF EXISTS "generation_job" CASCADE;
-- split
DROP TABLE IF EXISTS "content_block" CASCADE;
-- split
DROP TABLE IF EXISTS "source_revision" CASCADE;
-- split
DROP TABLE IF EXISTS "lesson_revision" CASCADE;
-- split
DROP TABLE IF EXISTS "lesson_reviewer" CASCADE;
-- split
DROP TABLE IF EXISTS "source_asset" CASCADE;
-- split
DROP TABLE IF EXISTS "session" CASCADE;
-- split
DROP TABLE IF EXISTS "lesson" CASCADE;
-- split
DROP TABLE IF EXISTS "class_member" CASCADE;
-- split
DROP TABLE IF EXISTS "audit_log" CASCADE;
-- split
DROP TABLE IF EXISTS "usage_daily" CASCADE;
-- split
DROP TABLE IF EXISTS "class" CASCADE;
-- split
DROP TABLE IF EXISTS "app_user" CASCADE;
-- split
DROP FUNCTION IF EXISTS pc_deny() CASCADE;
-- split
DROP FUNCTION IF EXISTS pc_source_immutable() CASCADE;
-- split
DROP FUNCTION IF EXISTS pc_block_guard() CASCADE;
-- split
DROP FUNCTION IF EXISTS pc_link_guard() CASCADE;
-- split
DROP FUNCTION IF EXISTS pc_lesson_source_guard() CASCADE;
-- split
DROP FUNCTION IF EXISTS pc_revision_transition() CASCADE;
-- split
DROP FUNCTION IF EXISTS pc_snapshot_guard() CASCADE;
-- split
DROP FUNCTION IF EXISTS pc_revision_is_locked(uuid) CASCADE;
