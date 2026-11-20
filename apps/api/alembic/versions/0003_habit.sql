-- Habit (chat + study habit). Additive only; chat_message is append-only like the other event tables.
CREATE TABLE chat_session (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id UUID NOT NULL REFERENCES assignment(id),
  student_id UUID NOT NULL REFERENCES app_user(id),
  item_block_id UUID REFERENCES content_block(id),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
)
-- split
CREATE UNIQUE INDEX uq_chat_session ON chat_session (assignment_id, student_id, COALESCE(item_block_id, '00000000-0000-0000-0000-000000000000'::uuid))
-- split
CREATE TABLE chat_message (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES chat_session(id),
  role TEXT NOT NULL CONSTRAINT ck_chat_role CHECK (role IN ('user', 'assistant')),
  action TEXT NOT NULL CONSTRAINT ck_chat_action CHECK (action IN ('hint', 'ask', 'explain')),
  text TEXT NOT NULL,
  hint_level SMALLINT CONSTRAINT ck_chat_hint CHECK (hint_level BETWEEN 0 AND 3),
  mode TEXT NOT NULL CONSTRAINT ck_chat_mode CHECK (mode IN ('rule', 'llm')),
  blocked_reason TEXT,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  request_id UUID,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT clock_timestamp()
)
-- split
CREATE UNIQUE INDEX uq_chat_request ON chat_message (session_id, request_id) WHERE role = 'assistant'
-- split
CREATE INDEX ix_chat_message_session ON chat_message (session_id, created_at)
-- split
CREATE TRIGGER tg_append_only BEFORE UPDATE OR DELETE ON chat_message FOR EACH ROW EXECUTE FUNCTION pc_deny()
-- split
CREATE TABLE study_activity (
  student_id UUID NOT NULL REFERENCES app_user(id),
  day DATE NOT NULL,
  items_answered INTEGER NOT NULL DEFAULT 0,
  hints_used INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (student_id, day)
)
