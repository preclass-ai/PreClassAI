-- The edit log keeps what a block said before and after a teacher edit (who and when were already there). Additive; append-only trigger unchanged.
ALTER TABLE transformation_event ADD COLUMN before_payload JSONB, ADD COLUMN after_payload JSONB
