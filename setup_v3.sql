-- ============================================
-- V3 전체 DB 스키마
-- Supabase SQL Editor에 통째로 붙여넣기
-- ============================================

-- 사용자
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    theme TEXT DEFAULT 'light',
    menu_order TEXT DEFAULT 'default',
    gmail_address TEXT,
    gmail_app_password TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 폴더
CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    parent_id UUID REFERENCES folders(id),
    icon TEXT DEFAULT '📁',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 노트
CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    folder_id UUID REFERENCES folders(id),
    title TEXT NOT NULL DEFAULT 'Untitled',
    content TEXT DEFAULT '',
    note_type TEXT DEFAULT 'note',
    is_daily BOOLEAN DEFAULT FALSE,
    daily_date DATE,
    is_favorite BOOLEAN DEFAULT FALSE,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    source_file TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 태그
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#6366f1',
    UNIQUE(user_id, name)
);

-- 노트-태그
CREATE TABLE IF NOT EXISTS note_tags (
    note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

-- 노트 링크
CREATE TABLE IF NOT EXISTS note_links (
    source_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    target_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    PRIMARY KEY (source_id, target_id)
);

-- 커스텀 템플릿
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    icon TEXT DEFAULT '📄',
    content TEXT DEFAULT '',
    note_type TEXT DEFAULT 'note',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 태스크
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'todo',
    priority TEXT DEFAULT 'medium',
    due_date DATE,
    project TEXT,
    note_id UUID REFERENCES notes(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 캘린더
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    color_label TEXT DEFAULT 'blue',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 캘린더 색상 라벨
CREATE TABLE IF NOT EXISTS color_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    color_key TEXT NOT NULL,
    label TEXT NOT NULL,
    hex_code TEXT NOT NULL,
    UNIQUE(user_id, color_key)
);

-- 지출
CREATE TABLE IF NOT EXISTS expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT DEFAULT '',
    expense_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 수입
CREATE TABLE IF NOT EXISTS income (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    source TEXT NOT NULL,
    income_date DATE DEFAULT CURRENT_DATE,
    is_recurring BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 대출
CREATE TABLE IF NOT EXISTS loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    total_amount INTEGER NOT NULL,
    remaining_amount INTEGER NOT NULL,
    interest_rate NUMERIC(5,2) DEFAULT 0,
    monthly_payment INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 습관
CREATE TABLE IF NOT EXISTS habits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    icon TEXT DEFAULT '✅',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    habit_id UUID REFERENCES habits(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    completed BOOLEAN DEFAULT FALSE,
    UNIQUE(habit_id, log_date)
);

-- 관심주식
CREATE TABLE IF NOT EXISTS watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    market TEXT DEFAULT 'KR',
    UNIQUE(user_id, symbol)
);

-- 뽀모도로
CREATE TABLE IF NOT EXISTS pomodoro_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    duration_minutes INTEGER DEFAULT 25,
    task_name TEXT,
    completed_at TIMESTAMPTZ DEFAULT now()
);

-- 전사 용어
CREATE TABLE IF NOT EXISTS custom_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    wrong_term TEXT NOT NULL,
    correct_term TEXT NOT NULL,
    UNIQUE(user_id, wrong_term)
);

-- 웹클립
CREATE TABLE IF NOT EXISTS web_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    note_id UUID REFERENCES notes(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 핀 아이템
CREATE TABLE IF NOT EXISTS pinned_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL,
    item_id UUID,
    title TEXT NOT NULL,
    url TEXT,
    sort_order INTEGER DEFAULT 0
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_notes_folder ON notes(folder_id);
CREATE INDEX IF NOT EXISTS idx_notes_daily ON notes(user_id, daily_date);
CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(user_id, note_type);
CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(user_id, project);
CREATE INDEX IF NOT EXISTS idx_expenses_user ON expenses(user_id, expense_date);
CREATE INDEX IF NOT EXISTS idx_income_user ON income(user_id, income_date);
CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs ON habit_logs(user_id, log_date);
CREATE INDEX IF NOT EXISTS idx_calendar_user ON calendar_events(user_id);
CREATE INDEX IF NOT EXISTS idx_folders_user ON folders(user_id);

-- RLS
DO $$ 
DECLARE t TEXT;
BEGIN
FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public' 
    AND tablename IN ('profiles','folders','notes','tags','note_tags','note_links','templates','tasks','calendar_events','color_labels','expenses','income','loans','habits','habit_logs','watchlist','pomodoro_logs','custom_terms','web_clips','pinned_items')
LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY IF NOT EXISTS "allow_all_%s" ON %I FOR ALL USING (true) WITH CHECK (true)', t, t);
END LOOP;
END $$;
