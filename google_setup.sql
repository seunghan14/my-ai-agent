-- Google Calendar 연동 + 앱 이벤트에 gcal_id 컬럼 추가
-- Supabase SQL Editor에서 실행

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS google_access_token TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS google_refresh_token TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS google_token_expiry TIMESTAMPTZ;

ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS gcal_id TEXT;
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'local';
