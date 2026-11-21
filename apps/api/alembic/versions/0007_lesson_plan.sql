-- Competency catalogue per subject (CV 5512). Other subjects are added later, never guessed here.
CREATE TABLE subject_competency (
	subject TEXT NOT NULL,
	code TEXT NOT NULL,
	name_vi TEXT NOT NULL,
	PRIMARY KEY (subject, code)
)
-- split
INSERT INTO subject_competency (subject, code, name_vi) VALUES
	('DIA_LI', 'NHAN_THUC', 'Nhận thức khoa học địa lí'),
	('DIA_LI', 'TIM_HIEU', 'Tìm hiểu địa lí'),
	('DIA_LI', 'VAN_DUNG', 'Vận dụng kiến thức, kĩ năng')
-- split
CREATE TABLE lesson_plan (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	owner_id UUID NOT NULL REFERENCES app_user (id),
	source_revision_id UUID NOT NULL REFERENCES source_revision (id),
	subject TEXT NOT NULL,
	grade INTEGER,
	title TEXT NOT NULL,
	ppct_period TEXT,
	week TEXT,
	planned_on DATE,
	taught_from DATE,
	taught_to DATE,
	redacted_count INTEGER DEFAULT 0 NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT clock_timestamp() NOT NULL,
	PRIMARY KEY (id)
)
-- split
CREATE TABLE lesson_section (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	lesson_plan_id UUID NOT NULL REFERENCES lesson_plan (id),
	position INTEGER NOT NULL,
	kind TEXT NOT NULL,
	activity_type TEXT,
	sub TEXT,
	anchor_ids UUID[] DEFAULT '{}' NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_section_activity CHECK (activity_type IS NULL OR activity_type IN ('mo_dau', 'hinh_thanh', 'luyen_tap', 'van_dung')),
	CONSTRAINT ck_section_sub CHECK (sub IS NULL OR sub IN ('muc_tieu', 'noi_dung', 'san_pham', 'to_chuc'))
)
-- split
CREATE TABLE objective (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	lesson_plan_id UUID NOT NULL REFERENCES lesson_plan (id),
	text TEXT NOT NULL,
	competency_code TEXT,
	anchor_id UUID REFERENCES source_anchor (id),
	PRIMARY KEY (id)
)
-- split
CREATE TABLE extracted_mcq (
	id UUID DEFAULT gen_random_uuid() NOT NULL,
	lesson_plan_id UUID NOT NULL REFERENCES lesson_plan (id),
	position INTEGER NOT NULL,
	stem_anchor_id UUID NOT NULL REFERENCES source_anchor (id),
	option_anchor_ids UUID[] DEFAULT '{}' NOT NULL,
	correct_option TEXT,
	answer_source TEXT,
	confidence TEXT DEFAULT 'low' NOT NULL,
	needs_confirmation BOOLEAN DEFAULT true NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_mcq_correct CHECK (correct_option IS NULL OR correct_option IN ('A', 'B', 'C', 'D')),
	CONSTRAINT ck_mcq_source CHECK (answer_source IS NULL OR answer_source IN ('underline', 'docx_underline', 'teacher')),
	CONSTRAINT ck_mcq_conf CHECK (confidence IN ('high', 'low'))
)
