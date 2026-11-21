-- VAL-10 (answer must not be readable before submitting): widen the rule-name CHECK from VAL-01..09 to VAL-01..19.
ALTER TABLE validation_result DROP CONSTRAINT ck_validation_rule
-- split
ALTER TABLE validation_result ADD CONSTRAINT ck_validation_rule CHECK (rule ~ '^VAL-(0[1-9]|1[0-9])$')
