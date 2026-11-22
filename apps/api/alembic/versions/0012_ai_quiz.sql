-- AI-drafted quiz questions and quick-review cards per lesson plan, and the student's review progress. Additive only.
ALTER TABLE lesson_plan ADD COLUMN ai_state TEXT DEFAULT 'none' NOT NULL
-- split
ALTER TABLE lesson_plan ADD COLUMN ai_stats JSONB
-- split
ALTER TABLE lesson_plan ADD COLUMN ai_tokens INTEGER DEFAULT 0 NOT NULL
-- split
ALTER TABLE lesson_plan ADD COLUMN ai_at TIMESTAMP WITH TIME ZONE
-- split
ALTER TABLE lesson_plan ADD CONSTRAINT ck_ai_state CHECK (ai_state IN ('none', 'queued', 'running', 'done', 'failed', 'skipped'))
-- split
CREATE TABLE plan_ai_item (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	lesson_plan_id UUID NOT NULL REFERENCES lesson_plan (id),
	kind TEXT NOT NULL,
	position INTEGER NOT NULL,
	status TEXT DEFAULT 'draft' NOT NULL,
	origin TEXT DEFAULT 'ai_generated' NOT NULL,
	payload JSONB NOT NULL,
	source_quote TEXT NOT NULL,
	needs_confirmation BOOLEAN DEFAULT true NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_ai_item_kind CHECK (kind IN ('quiz', 'review')),
	CONSTRAINT ck_ai_item_status CHECK (status IN ('draft', 'approved', 'rejected'))
)
-- split
CREATE INDEX ix_plan_ai_item_plan ON plan_ai_item (lesson_plan_id, kind, position)
-- split
CREATE TABLE review_progress (
	assignment_id UUID NOT NULL REFERENCES assignment (id),
	student_id UUID NOT NULL REFERENCES app_user (id),
	choice TEXT,
	seen_ids UUID[] DEFAULT '{}' NOT NULL,
	checks JSONB DEFAULT '{}' NOT NULL,
	reviewed BOOLEAN DEFAULT false NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	PRIMARY KEY (assignment_id, student_id),
	CONSTRAINT ck_review_choice CHECK (choice IS NULL OR choice IN ('not_yet', 'done'))
)
-- split
ALTER TABLE chat_message DROP CONSTRAINT ck_chat_hint
-- split
ALTER TABLE chat_message ADD CONSTRAINT ck_chat_hint CHECK (hint_level BETWEEN 0 AND 30)
