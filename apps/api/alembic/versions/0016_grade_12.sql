ALTER TABLE class DROP CONSTRAINT ck_class_grade
-- split
ALTER TABLE class ADD CONSTRAINT ck_class_grade CHECK (grade IN (10, 11, 12))
-- split
ALTER TABLE lesson DROP CONSTRAINT ck_lesson_grade
-- split
ALTER TABLE lesson ADD CONSTRAINT ck_lesson_grade CHECK (grade IN (10, 11, 12))
