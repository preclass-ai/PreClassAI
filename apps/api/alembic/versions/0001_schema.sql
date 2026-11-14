-- Frozen DDL generated from app/db/models.py at baseline. Later changes: explicit migrations.
CREATE TABLE app_user (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	email TEXT, 
	login_code TEXT, 
	display_name TEXT NOT NULL, 
	role TEXT NOT NULL, 
	password_hash TEXT NOT NULL, 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_role CHECK (role IN ('TEACHER', 'REVIEWER', 'STUDENT', 'ADMIN')), 
	CONSTRAINT ck_user_identity CHECK (email IS NOT NULL OR login_code IS NOT NULL), 
	UNIQUE (email), 
	UNIQUE (login_code)
);
-- split
CREATE TABLE class (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	code TEXT NOT NULL, 
	grade INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_class_grade CHECK (grade IN (10, 11)), 
	UNIQUE (code)
);
-- split
CREATE TABLE usage_daily (
	day TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	tokens BIGINT DEFAULT 0 NOT NULL, 
	PRIMARY KEY (day)
);
-- split
CREATE TABLE audit_log (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	actor_id UUID, 
	action TEXT NOT NULL, 
	resource_type TEXT NOT NULL, 
	resource_id UUID, 
	metadata JSONB DEFAULT '{}' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES app_user (id)
);
-- split
CREATE TABLE class_member (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	class_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	role_in_class TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (class_id, user_id), 
	CONSTRAINT ck_role_in_class CHECK (role_in_class IN ('TEACHER', 'STUDENT')), 
	FOREIGN KEY(class_id) REFERENCES class (id), 
	FOREIGN KEY(user_id) REFERENCES app_user (id)
);
-- split
CREATE TABLE lesson (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	author_id UUID NOT NULL, 
	subject TEXT DEFAULT 'GEOGRAPHY' NOT NULL, 
	grade INTEGER NOT NULL, 
	title TEXT NOT NULL, 
	goal TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_lesson_grade CHECK (grade IN (10, 11)), 
	CONSTRAINT ck_subject CHECK (subject IN ('GEOGRAPHY')), 
	FOREIGN KEY(author_id) REFERENCES app_user (id)
);
-- split
CREATE TABLE session (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	token_hash TEXT NOT NULL, 
	user_id UUID NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (token_hash), 
	FOREIGN KEY(user_id) REFERENCES app_user (id)
);
-- split
CREATE TABLE source_asset (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	owner_id UUID NOT NULL, 
	title TEXT NOT NULL, 
	license_note TEXT, 
	visibility TEXT DEFAULT 'PRIVATE' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_visibility CHECK (visibility IN ('PRIVATE', 'SCHOOL')), 
	FOREIGN KEY(owner_id) REFERENCES app_user (id)
);
-- split
CREATE TABLE lesson_reviewer (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	lesson_id UUID NOT NULL, 
	reviewer_id UUID NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (lesson_id, reviewer_id), 
	FOREIGN KEY(lesson_id) REFERENCES lesson (id), 
	FOREIGN KEY(reviewer_id) REFERENCES app_user (id)
);
-- split
CREATE TABLE lesson_revision (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	lesson_id UUID NOT NULL, 
	revision_no INTEGER NOT NULL, 
	state TEXT DEFAULT 'DRAFT' NOT NULL, 
	base_revision_id UUID, 
	version INTEGER DEFAULT 1 NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (lesson_id, revision_no), 
	CONSTRAINT ck_state CHECK (state IN ('DRAFT', 'IN_REVIEW', 'PUBLISHED', 'SUPERSEDED')), 
	FOREIGN KEY(lesson_id) REFERENCES lesson (id), 
	FOREIGN KEY(base_revision_id) REFERENCES lesson_revision (id)
);
-- split
CREATE TABLE source_revision (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	asset_id UUID NOT NULL, 
	version INTEGER NOT NULL, 
	sha256 TEXT NOT NULL, 
	mime TEXT NOT NULL, 
	file_uri TEXT, 
	extract_status TEXT DEFAULT 'PENDING' NOT NULL, 
	locked_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (asset_id, version), 
	CONSTRAINT ck_extract_status CHECK (extract_status IN ('PENDING', 'OK', 'FAILED')), 
	FOREIGN KEY(asset_id) REFERENCES source_asset (id)
);
-- split
CREATE TABLE content_block (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	revision_id UUID NOT NULL, 
	kind TEXT NOT NULL, 
	parent_id UUID, 
	position INTEGER NOT NULL, 
	payload JSONB NOT NULL, 
	content_hash TEXT NOT NULL, 
	transformation TEXT NOT NULL, 
	review_status TEXT DEFAULT 'UNREVIEWED' NOT NULL, 
	no_source_reason TEXT, 
	is_factual BOOLEAN DEFAULT false NOT NULL, 
	version INTEGER DEFAULT 1 NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_transformation CHECK (transformation IN ('ORIGINAL', 'PARAPHRASED', 'SYNTHESISED', 'AI_PROPOSED', 'TEACHER_AUTHORED')), 
	CONSTRAINT ck_review_status CHECK (review_status IN ('UNREVIEWED', 'AUTO_CHECKED', 'FLAGGED', 'APPROVED', 'REVIEW_AGAIN', 'REJECTED')), 
	FOREIGN KEY(revision_id) REFERENCES lesson_revision (id), 
	FOREIGN KEY(parent_id) REFERENCES content_block (id)
);
-- split
CREATE TABLE generation_job (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	revision_id UUID NOT NULL, 
	output_type TEXT NOT NULL, 
	params JSONB DEFAULT '{}' NOT NULL, 
	status TEXT DEFAULT 'QUEUED' NOT NULL, 
	error TEXT, 
	model TEXT, 
	prompt_version TEXT, 
	tokens_in INTEGER DEFAULT 0 NOT NULL, 
	tokens_out INTEGER DEFAULT 0 NOT NULL, 
	created_by UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_output_type CHECK (output_type IN ('WORKSHEET', 'FLASHCARDS')), 
	CONSTRAINT ck_status CHECK (status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')), 
	FOREIGN KEY(revision_id) REFERENCES lesson_revision (id), 
	FOREIGN KEY(created_by) REFERENCES app_user (id)
);
-- split
CREATE TABLE lesson_source (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	lesson_revision_id UUID NOT NULL, 
	source_revision_id UUID NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (lesson_revision_id, source_revision_id), 
	FOREIGN KEY(lesson_revision_id) REFERENCES lesson_revision (id), 
	FOREIGN KEY(source_revision_id) REFERENCES source_revision (id)
);
-- split
CREATE TABLE published_version (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	lesson_revision_id UUID NOT NULL, 
	snapshot JSONB NOT NULL, 
	snapshot_hash TEXT NOT NULL, 
	published_by UUID NOT NULL, 
	state TEXT DEFAULT 'ACTIVE' NOT NULL, 
	withdraw_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_state CHECK (state IN ('ACTIVE', 'WITHDRAWN')), 
	UNIQUE (lesson_revision_id), 
	FOREIGN KEY(lesson_revision_id) REFERENCES lesson_revision (id), 
	FOREIGN KEY(published_by) REFERENCES app_user (id)
);
-- split
CREATE TABLE source_anchor (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	source_revision_id UUID NOT NULL, 
	code TEXT NOT NULL, 
	kind TEXT NOT NULL, 
	locator JSONB NOT NULL, 
	excerpt TEXT NOT NULL, 
	excerpt_hash TEXT NOT NULL, 
	numbers NUMERIC[] DEFAULT '{}' NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (source_revision_id, code), 
	CONSTRAINT ck_kind CHECK (kind IN ('PARAGRAPH', 'HEADING', 'TABLE_CELL', 'TABLE_ROW')), 
	FOREIGN KEY(source_revision_id) REFERENCES source_revision (id)
);
-- split
CREATE TABLE assignment (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	published_version_id UUID NOT NULL, 
	class_id UUID NOT NULL, 
	open_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	due_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(published_version_id) REFERENCES published_version (id), 
	FOREIGN KEY(class_id) REFERENCES class (id)
);
-- split
CREATE TABLE block_dependency (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	block_id UUID NOT NULL, 
	depends_on_block_id UUID NOT NULL, 
	kind TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (block_id, depends_on_block_id), 
	CONSTRAINT ck_kind CHECK (kind IN ('ANSWER_OF', 'EXPLANATION_OF', 'FEEDBACK_OF', 'LABEL_OF')), 
	FOREIGN KEY(block_id) REFERENCES content_block (id), 
	FOREIGN KEY(depends_on_block_id) REFERENCES content_block (id)
);
-- split
CREATE TABLE provenance_link (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	block_id UUID NOT NULL, 
	anchor_id UUID NOT NULL, 
	relation TEXT NOT NULL, 
	rationale TEXT, 
	status TEXT DEFAULT 'VERIFIED' NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (block_id, anchor_id), 
	CONSTRAINT ck_relation CHECK (relation IN ('derived_from', 'quotes', 'supports')), 
	CONSTRAINT ck_status CHECK (status IN ('VERIFIED', 'UNRESOLVED')), 
	FOREIGN KEY(block_id) REFERENCES content_block (id), 
	FOREIGN KEY(anchor_id) REFERENCES source_anchor (id)
);
-- split
CREATE TABLE review_event (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	block_id UUID NOT NULL, 
	content_hash TEXT NOT NULL, 
	source_hashes TEXT[] DEFAULT '{}' NOT NULL, 
	reviewer_id UUID NOT NULL, 
	action TEXT NOT NULL, 
	note TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_action CHECK (action IN ('APPROVE', 'REJECT', 'REQUEST_CHANGES')), 
	FOREIGN KEY(block_id) REFERENCES content_block (id), 
	FOREIGN KEY(reviewer_id) REFERENCES app_user (id)
);
-- split
CREATE TABLE transformation_event (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	block_id UUID NOT NULL, 
	actor_type TEXT NOT NULL, 
	actor_id UUID, 
	operation TEXT NOT NULL, 
	before_hash TEXT, 
	after_hash TEXT NOT NULL, 
	generator_version TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_actor_type CHECK (actor_type IN ('AI', 'TEACHER', 'SYSTEM')), 
	CONSTRAINT ck_operation CHECK (operation IN ('GENERATE', 'EDIT', 'REGENERATE', 'SOURCE_REPLACED')), 
	FOREIGN KEY(block_id) REFERENCES content_block (id), 
	FOREIGN KEY(actor_id) REFERENCES app_user (id)
);
-- split
CREATE TABLE validation_result (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	block_id UUID NOT NULL, 
	rule TEXT NOT NULL, 
	severity TEXT NOT NULL, 
	outcome TEXT NOT NULL, 
	evidence JSONB DEFAULT '{}' NOT NULL, 
	method TEXT NOT NULL, 
	content_hash TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_validation_rule CHECK (rule ~ '^VAL-0[1-9]$'), 
	CONSTRAINT ck_severity CHECK (severity IN ('BLOCKER', 'WARNING')), 
	CONSTRAINT ck_outcome CHECK (outcome IN ('PASS', 'FAIL')), 
	FOREIGN KEY(block_id) REFERENCES content_block (id)
);
-- split
CREATE TABLE student_attempt (
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	assignment_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	item_block_id UUID NOT NULL, 
	answer JSONB NOT NULL, 
	is_correct BOOLEAN, 
	request_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (assignment_id, student_id, item_block_id), 
	FOREIGN KEY(assignment_id) REFERENCES assignment (id), 
	FOREIGN KEY(student_id) REFERENCES app_user (id), 
	FOREIGN KEY(item_block_id) REFERENCES content_block (id), 
	UNIQUE (request_id)
);
