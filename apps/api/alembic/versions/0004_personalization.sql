-- Student-chosen learning options. No psychological or health labels: see docs/adr/ADR-0013-personalization.md.
CREATE TABLE student_preference (
  student_id UUID NOT NULL REFERENCES app_user(id),
  key TEXT NOT NULL CONSTRAINT ck_pref_key CHECK (key IN ('chia_nho_tung_buoc', 'hen_gio_tap_trung', 'uu_tien_bang_so_lieu',
    'uu_tien_giai_thich', 'nhac_tien_do', 'focus_mode_used')),
  value TEXT NOT NULL CONSTRAINT ck_pref_value CHECK (value IN ('on', '5', '10')),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  PRIMARY KEY (student_id, key)
)
