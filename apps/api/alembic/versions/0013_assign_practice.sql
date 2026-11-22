-- Teacher can cancel an assignment (soft: attempts and CSV history stay), and students can practise an item again after the first attempt.
ALTER TABLE assignment ADD COLUMN cancelled_at TIMESTAMP WITH TIME ZONE
-- split
CREATE TABLE practice_attempt (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	assignment_id UUID NOT NULL REFERENCES assignment (id),
	student_id UUID NOT NULL REFERENCES app_user (id),
	item_block_id UUID NOT NULL REFERENCES content_block (id),
	answer JSONB NOT NULL,
	is_correct BOOLEAN,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	PRIMARY KEY (id)
)
-- split
CREATE INDEX ix_practice_assignment ON practice_attempt (assignment_id, student_id, item_block_id)
-- split
CREATE TRIGGER tg_append_only BEFORE UPDATE OR DELETE ON practice_attempt FOR EACH ROW EXECUTE FUNCTION pc_deny()
