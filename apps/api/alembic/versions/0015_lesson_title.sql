-- Teachers can rename a lesson (lesson.title, mutable) and give one assignment its own student-facing name (assignment.display_title).
-- The published snapshot stays immutable: students read display_title, else the snapshot title. Every rename is logged (rename_log, append-only).
ALTER TABLE assignment ADD COLUMN display_title TEXT
-- split
ALTER TABLE lesson ADD COLUMN lesson_plan_id UUID REFERENCES lesson_plan (id)
-- split
CREATE TABLE rename_log (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	target_type TEXT NOT NULL CHECK (target_type IN ('lesson', 'assignment')),
	target_id UUID NOT NULL,
	field TEXT NOT NULL,
	before TEXT,
	after TEXT,
	actor_id UUID REFERENCES app_user (id),
	actor_label TEXT,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	PRIMARY KEY (id)
)
-- split
CREATE INDEX ix_rename_log_target ON rename_log (target_type, target_id, created_at DESC)
-- split
CREATE TRIGGER tg_append_only BEFORE UPDATE OR DELETE ON rename_log FOR EACH ROW EXECUTE FUNCTION pc_deny()
-- split
UPDATE lesson l SET lesson_plan_id = p.id FROM lesson_plan p
	JOIN lesson_revision r ON TRUE
	JOIN lesson_source s ON s.lesson_revision_id = r.id AND s.source_revision_id = p.source_revision_id
	WHERE r.lesson_id = l.id AND l.author_id = p.owner_id AND l.title = left('Chuẩn bị: ' || p.title, 200)
