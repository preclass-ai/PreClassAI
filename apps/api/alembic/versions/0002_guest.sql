-- Guest (anonymous survey) accounts. No IP is stored: rate limiting is in memory only.
ALTER TABLE app_user ADD COLUMN is_guest BOOLEAN NOT NULL DEFAULT false;
-- split
ALTER TABLE app_user ADD COLUMN survey_code TEXT;
-- split
ALTER TABLE app_user ADD COLUMN last_seen_at TIMESTAMP WITH TIME ZONE;
-- split
ALTER TABLE app_user ADD CONSTRAINT uq_app_user_survey_code UNIQUE (survey_code);
-- split
ALTER TABLE app_user ADD CONSTRAINT ck_guest_has_code CHECK (NOT is_guest OR survey_code IS NOT NULL);
