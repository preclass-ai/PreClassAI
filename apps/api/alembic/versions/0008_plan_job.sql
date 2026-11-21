-- Background reading of a lesson plan (one job per teacher at a time), and competency codes on MCQ and blocks. Additive only.
CREATE TABLE lesson_plan_job (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	owner_id UUID NOT NULL REFERENCES app_user (id),
	state TEXT DEFAULT 'queued' NOT NULL,
	file_name TEXT,
	error_code TEXT,
	error_title TEXT,
	plan_ids UUID[] DEFAULT '{}' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_plan_job_state CHECK (state IN ('queued', 'parsing', 'done', 'failed'))
)
-- split
CREATE INDEX ix_plan_job_owner ON lesson_plan_job (owner_id, created_at DESC)
-- split
ALTER TABLE extracted_mcq ADD COLUMN competency_code TEXT
-- split
ALTER TABLE content_block ADD COLUMN competency_code TEXT
-- split
ALTER TABLE content_block ADD COLUMN objective_id UUID REFERENCES objective (id)
-- split
ALTER TABLE lesson ADD COLUMN teach_date DATE
