-- ============================================================
-- Google Calendar 컬럼 수정 마이그레이션
-- Supabase SQL Editor에서 실행하세요
-- ============================================================

-- 1. gcal_id 컬럼 추가 (없으면 추가, 있으면 무시)
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS gcal_id TEXT;

-- 2. source 컬럼 추가
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'local';

-- 3. color_label 컬럼 추가 (기존 color 컬럼명 호환)
-- Setup.sql에서는 'color', 코드에서는 'color_label' 사용 → 통일
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS color_label TEXT DEFAULT 'blue';

-- 4. google_event_id가 있는 경우 gcal_id로 데이터 이전
UPDATE calendar_events 
SET gcal_id = google_event_id 
WHERE google_event_id IS NOT NULL AND gcal_id IS NULL;

-- 5. 중복 이벤트 제거 (gcal_id 기반)
-- 같은 user_id + gcal_id 조합에서 가장 최신 것만 남기고 나머지 삭제
DELETE FROM calendar_events
WHERE id NOT IN (
    SELECT DISTINCT ON (user_id, gcal_id) id
    FROM calendar_events
    WHERE gcal_id IS NOT NULL
    ORDER BY user_id, gcal_id, created_at DESC
)
AND gcal_id IS NOT NULL;

-- 6. gcal_id 중복 방지 인덱스 (선택사항)
CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_gcal_id 
ON calendar_events(user_id, gcal_id) 
WHERE gcal_id IS NOT NULL;

-- 7. profiles 테이블 Google 토큰 컬럼 확인
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS google_access_token TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS google_refresh_token TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS google_token_expiry TIMESTAMPTZ;

-- 완료 확인 쿼리
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'calendar_events'
ORDER BY ordinal_position;
