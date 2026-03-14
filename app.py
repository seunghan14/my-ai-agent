import streamlit as st
from datetime import datetime, date, timedelta
import json

# 페이지 설정
st.set_page_config(page_title="나만의 AI 에이전트", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ===== 세션 초기화 =====
defaults = {
    "logged_in": False, "user": None, "current_page": "🏠 대시보드",
    "gemini_api_key": "", "claude_api_key": "", "ai_engine": "auto",
    "editing_note": None, "quick_capture": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ===== DB & AI 임포트 =====
try:
    from db_utils import *
    from ai_engine import *
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ===== 스타일 =====
st.markdown("""<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem; border-radius: 12px; color: white; text-align: center; }
    .note-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;
        margin: 4px 0; transition: all 0.2s; }
    .note-card:hover { border-color: #6366f1; box-shadow: 0 2px 8px rgba(99,102,241,0.15); }
    .tag-pill { display: inline-block; padding: 2px 10px; border-radius: 12px;
        font-size: 12px; margin: 2px; background: #eef2ff; color: #4f46e5; }
    .kanban-col { background: #f8fafc; border-radius: 8px; padding: 8px; min-height: 200px; }
    .priority-high { border-left: 3px solid #ef4444; }
    .priority-medium { border-left: 3px solid #f59e0b; }
    .priority-low { border-left: 3px solid #22c55e; }
    div[data-testid="stSidebar"] { background: #fafbfc; }
    .status-todo { color: #6b7280; } .status-doing { color: #3b82f6; } .status-done { color: #22c55e; }
</style>""", unsafe_allow_html=True)


# ===== 사이드바 =====
with st.sidebar:
    st.markdown("## 🚀 나만의 AI 에이전트")
    st.markdown("---")

    # 로그인 / 사용자 정보
    if not st.session_state.logged_in:
        auth_tab = st.radio("", ["로그인", "회원가입"], horizontal=True, label_visibility="collapsed")
        
        if auth_tab == "로그인":
            email = st.text_input("이메일", key="login_email")
            pwd = st.text_input("비밀번호", type="password", key="login_pwd")
            if st.button("로그인", use_container_width=True, type="primary"):
                if DB_AVAILABLE:
                    user, err = login_user(email, pwd)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error(err or "로그인 실패")
                else:
                    # DB 없이 데모 모드
                    st.session_state.logged_in = True
                    st.session_state.user = {"id": "demo", "email": email, "display_name": email.split("@")[0]}
                    st.rerun()
        else:
            name = st.text_input("이름", key="reg_name")
            email = st.text_input("이메일", key="reg_email")
            pwd = st.text_input("비밀번호", type="password", key="reg_pwd")
            pwd2 = st.text_input("비밀번호 확인", type="password", key="reg_pwd2")
            if st.button("가입하기", use_container_width=True, type="primary"):
                if pwd != pwd2:
                    st.error("비밀번호가 일치하지 않습니다")
                elif DB_AVAILABLE:
                    user, err = register_user(email, pwd, name)
                    if user:
                        st.success("가입 완료! 로그인해주세요.")
                    else:
                        st.error(err or "가입 실패")
                else:
                    st.info("DB 연결 후 가입 가능합니다")
    else:
        user = st.session_state.user
        st.markdown(f"👤 **{user.get('display_name', user.get('email', ''))}**")
        
        # 네비게이션
        st.markdown("---")
        pages = ["🏠 대시보드", "📝 노트", "✅ 태스크", "📅 캘린더", "💰 재정", "✨ AI 콘텐츠", "🎙️ 전사/회의록", "⚙️ 설정"]
        st.session_state.current_page = st.radio("메뉴", pages, label_visibility="collapsed")
        
        st.markdown("---")
        
        # 퀵 캡처
        st.markdown("### ⚡ 퀵 캡처")
        quick_text = st.text_input("빠른 입력", placeholder="생각나는 것을 바로 입력...", label_visibility="collapsed", key="quick_input")
        if quick_text and st.button("저장", use_container_width=True, key="quick_save"):
            if DB_AVAILABLE:
                classified = smart_classify(quick_text)
                ctype = classified.get("type", "note")
                if ctype == "task":
                    create_task(user["id"], classified.get("title", quick_text), classified.get("content", ""))
                    st.success("✅ 태스크로 저장!")
                elif ctype == "expense":
                    amt = classified.get("amount", 0)
                    cat = classified.get("category", "기타")
                    if amt:
                        add_expense(user["id"], int(amt), cat, quick_text)
                        st.success(f"💰 지출 기록: {cat} {int(amt):,}원")
                    else:
                        create_note(user["id"], classified.get("title", quick_text), quick_text)
                        st.success("📝 노트로 저장!")
                elif ctype == "event":
                    st.info(f"📅 일정 감지: {classified.get('title', quick_text)} → 캘린더에서 추가해주세요")
                else:
                    create_note(user["id"], classified.get("title", quick_text[:50]), quick_text)
                    st.success("📝 노트로 저장!")
            else:
                st.info(f"분류 결과: {quick_text}")
        
        st.markdown("---")
        if st.button("로그아웃", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ===== 메인 영역 =====
if not st.session_state.logged_in:
    st.markdown("# 🚀 나만의 AI 에이전트")
    st.markdown("### 노트 · 태스크 · 캘린더 · 재정 · AI — 하나의 앱에서")
    st.info("👈 사이드바에서 로그인하세요. DB 미연결 시 데모 모드로 체험 가능합니다.")
    st.stop()

user = st.session_state.user
user_id = user["id"]
page = st.session_state.current_page


# =============================================
# 🏠 대시보드
# =============================================
if page == "🏠 대시보드":
    st.markdown(f"## 🏠 좋은 하루 되세요, {user.get('display_name', '')}님!")
    
    if DB_AVAILABLE:
        today_tasks = get_tasks(user_id)
        todo = [t for t in today_tasks if t["status"] == "todo"]
        doing = [t for t in today_tasks if t["status"] == "doing"]
        done = [t for t in today_tasks if t["status"] == "done"]
        recent_notes = get_notes(user_id)[:5]
        today_expenses = get_expenses(user_id, datetime.now().strftime("%Y-%m"))
        
        # 메트릭
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📝 할 일", f"{len(todo)}개")
        c2.metric("🔄 진행중", f"{len(doing)}개")
        c3.metric("✅ 완료", f"{len(done)}개")
        c4.metric("💰 이달 지출", f"{sum(e.get('amount',0) for e in today_expenses):,}원")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📝 최근 노트")
            if recent_notes:
                for n in recent_notes:
                    with st.container():
                        st.markdown(f"**{n['title']}** · _{n.get('updated_at','')[:10]}_")
            else:
                st.info("아직 노트가 없어요. 📝 노트 탭에서 시작해보세요!")
        
        with col2:
            st.markdown("### ✅ 오늘 할 일")
            if todo:
                for t in todo[:5]:
                    prio = "🔴" if t.get("priority") == "high" else "🟡" if t.get("priority") == "medium" else "🟢"
                    st.markdown(f"{prio} {t['title']}")
            else:
                st.info("할 일이 모두 완료되었어요! 🎉")
        
        # AI 브리핑
        st.markdown("---")
        if st.button("☀️ AI 아침 브리핑 받기", type="primary"):
            with st.spinner("브리핑 생성 중..."):
                today_str = datetime.now().strftime("%Y년 %m월 %d일 %A")
                task_summary = f"할일 {len(todo)}개, 진행중 {len(doing)}개"
                prompt = f"""오늘은 {today_str}입니다.

현재 상황:
- {task_summary}
- 이달 지출: {sum(e.get('amount',0) for e in today_expenses):,}원

오늘의 브리핑을 작성해주세요:
1. 오늘 집중해야 할 것
2. 생산성 팁 2가지
3. 동기부여 한마디

간결하고 실용적으로 작성해주세요."""
                result = get_ai_response(prompt, st.session_state.ai_engine, "summary")
                st.markdown(result)
    else:
        st.info("Supabase DB를 연결하면 대시보드 데이터가 표시됩니다.")


# =============================================
# 📝 노트
# =============================================
elif page == "📝 노트":
    st.markdown("## 📝 노트")
    
    # 상단 액션
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search_q = st.text_input("🔍 검색", placeholder="키워드, 태그, 제목...", label_visibility="collapsed")
    with col2:
        note_filter = st.selectbox("필터", ["전체", "일반 노트", "회의록", "데일리", "즐겨찾기"], label_visibility="collapsed")
    with col3:
        if st.button("📅 오늘의 데일리 노트", use_container_width=True):
            if DB_AVAILABLE:
                daily = get_daily_note(user_id)
                if daily:
                    st.session_state.editing_note = daily
                    st.rerun()
    with col4:
        if st.button("➕ 새 노트", type="primary", use_container_width=True):
            if DB_AVAILABLE:
                new_note = create_note(user_id, "새 노트", "")
                if new_note:
                    st.session_state.editing_note = new_note
                    st.rerun()
            else:
                st.session_state.editing_note = {"id": "demo", "title": "새 노트", "content": "", "note_type": "note", "is_favorite": False}
    
    st.markdown("---")
    
    # 노트 편집 모드
    if st.session_state.editing_note:
        note = st.session_state.editing_note
        
        col_title, col_fav = st.columns([5, 1])
        with col_title:
            new_title = st.text_input("제목", value=note.get("title", ""), label_visibility="collapsed", key="note_title_edit")
        with col_fav:
            is_fav = st.checkbox("⭐", value=note.get("is_favorite", False), key="note_fav")
        
        # 태그
        tag_input = st.text_input("태그 (쉼표로 구분)", placeholder="#업무, #프로젝트A, #아이디어", key="note_tags_input")
        
        # 노트 유형
        note_type = st.selectbox("노트 유형", ["note", "meeting", "daily", "idea", "project"], 
                                  format_func=lambda x: {"note":"일반 노트","meeting":"회의록","daily":"데일리","idea":"아이디어","project":"프로젝트"}.get(x, x),
                                  index=["note","meeting","daily","idea","project"].index(note.get("note_type","note")) if note.get("note_type","note") in ["note","meeting","daily","idea","project"] else 0)
        
        # 템플릿 버튼
        tcol1, tcol2, tcol3, tcol4 = st.columns(4)
        with tcol1:
            if st.button("📋 회의록 템플릿"):
                st.session_state.template_content = "## 📋 회의 정보\n- 날짜: \n- 참석자: \n- 목적: \n\n## 📌 안건\n1. \n\n## 💬 논의 내용\n\n\n## ✅ 결정 사항\n\n\n## 🎯 액션 아이템\n- [ ] \n\n## 📅 다음 회의\n- "
        with tcol2:
            if st.button("📊 주간 리뷰 템플릿"):
                st.session_state.template_content = "## 📊 주간 리뷰\n\n### ✅ 이번 주 완료\n- \n\n### 🔄 진행 중\n- \n\n### 🚫 미완료 / 이월\n- \n\n### 💡 배운 점\n- \n\n### 🎯 다음 주 목표\n1. \n2. \n3. "
        with tcol3:
            if st.button("💡 아이디어 템플릿"):
                st.session_state.template_content = "## 💡 아이디어\n\n### 핵심 내용\n\n\n### 배경 / 문제\n\n\n### 기대 효과\n\n\n### 실행 방안\n1. \n\n### 참고 자료\n- "
        with tcol4:
            if st.button("📄 1:1 미팅 템플릿"):
                st.session_state.template_content = "## 👥 1:1 미팅\n- 날짜: \n- 상대방: \n\n### 이전 액션 아이템 체크\n- [ ] \n\n### 논의 사항\n1. \n\n### 피드백\n- \n\n### 다음 액션 아이템\n- [ ] "
        
        # 에디터
        default_content = st.session_state.get("template_content", note.get("content", ""))
        if "template_content" in st.session_state:
            del st.session_state.template_content
        
        content = st.text_area("내용 (마크다운 지원)", value=default_content, height=400, key="note_content_edit", label_visibility="collapsed")
        
        # AI 기능
        ai_col1, ai_col2, ai_col3 = st.columns(3)
        with ai_col1:
            if st.button("🤖 AI 요약", use_container_width=True):
                if content:
                    with st.spinner("요약 중..."):
                        summary = get_ai_response(f"다음 내용을 핵심만 3-5줄로 요약해주세요:\n\n{content}", st.session_state.ai_engine, "summary")
                        st.markdown("**AI 요약:**")
                        st.markdown(summary)
        with ai_col2:
            if st.button("🔗 관련 노트 추천", use_container_width=True):
                if DB_AVAILABLE and content:
                    with st.spinner("분석 중..."):
                        all_notes = get_notes(user_id)
                        suggestions = suggest_related_notes(content, all_notes)
                        if suggestions:
                            st.markdown("**관련 노트:**")
                            for s in suggestions:
                                matching = [n for n in all_notes if n["id"] == s]
                                if matching:
                                    st.markdown(f"- 📝 {matching[0]['title']}")
                        else:
                            st.info("관련 노트를 찾지 못했어요.")
        with ai_col3:
            if st.button("✨ AI 보완/확장", use_container_width=True):
                if content:
                    with st.spinner("작성 중..."):
                        expanded = get_ai_response(f"다음 내용을 보완하고 확장해주세요. 빠진 관점이 있으면 추가하고, 구조를 정리해주세요:\n\n{content}", st.session_state.ai_engine, "content")
                        st.markdown("**AI 보완:**")
                        st.markdown(expanded)
        
        # 저장 / 닫기
        st.markdown("---")
        save_col, close_col, delete_col = st.columns([2, 1, 1])
        with save_col:
            if st.button("💾 저장", type="primary", use_container_width=True):
                if DB_AVAILABLE and note.get("id") != "demo":
                    update_note(note["id"], title=new_title, content=content, note_type=note_type, is_favorite=is_fav)
                    if tag_input:
                        for tag_name in [t.strip().replace("#", "") for t in tag_input.split(",") if t.strip()]:
                            tag = add_tag(user_id, tag_name)
                            if tag:
                                tag_note(note["id"], tag["id"])
                    st.success("저장 완료!")
                else:
                    st.success("저장 완료! (데모 모드)")
        with close_col:
            if st.button("닫기", use_container_width=True):
                st.session_state.editing_note = None
                st.rerun()
        with delete_col:
            if st.button("🗑️ 삭제", use_container_width=True):
                if DB_AVAILABLE and note.get("id") != "demo":
                    delete_note(note["id"])
                st.session_state.editing_note = None
                st.rerun()
    
    # 노트 목록
    else:
        if DB_AVAILABLE:
            filter_map = {"전체": None, "일반 노트": "note", "회의록": "meeting", "데일리": "daily", "즐겨찾기": None}
            fav_only = note_filter == "즐겨찾기"
            ntype = filter_map.get(note_filter)
            notes = get_notes(user_id, note_type=ntype, search=search_q if search_q else None, favorites_only=fav_only)
            
            if notes:
                for n in notes:
                    icon = {"meeting": "📋", "daily": "📅", "idea": "💡", "project": "📁"}.get(n.get("note_type"), "📝")
                    fav = "⭐ " if n.get("is_favorite") else ""
                    col_n, col_a = st.columns([5, 1])
                    with col_n:
                        st.markdown(f"{fav}{icon} **{n['title']}** · _{n.get('updated_at','')[:10]}_")
                        if n.get("content"):
                            st.caption(n["content"][:100] + "..." if len(n.get("content","")) > 100 else n.get("content",""))
                    with col_a:
                        if st.button("열기", key=f"open_{n['id']}"):
                            st.session_state.editing_note = n
                            st.rerun()
            else:
                st.info("노트가 없습니다. '새 노트'를 눌러 시작하세요!")
        else:
            st.info("DB 연결 후 노트를 사용할 수 있습니다.")


# =============================================
# ✅ 태스크 (칸반)
# =============================================
elif page == "✅ 태스크":
    st.markdown("## ✅ 태스크 관리")
    
    # 태스크 추가
    with st.expander("➕ 새 태스크 추가", expanded=False):
        tc1, tc2 = st.columns(2)
        with tc1:
            task_title = st.text_input("할 일", key="new_task_title")
            task_project = st.text_input("프로젝트 (선택)", key="new_task_project")
        with tc2:
            task_priority = st.selectbox("우선순위", ["high", "medium", "low"], format_func=lambda x: {"high":"🔴 높음","medium":"🟡 보통","low":"🟢 낮음"}[x])
            task_due = st.date_input("마감일 (선택)", value=None, key="new_task_due")
        task_desc = st.text_input("설명 (선택)", key="new_task_desc")
        
        if st.button("추가", type="primary", key="add_task_btn"):
            if task_title and DB_AVAILABLE:
                create_task(user_id, task_title, task_desc, "todo", task_priority, task_due if task_due else None, task_project if task_project else None)
                st.success("태스크 추가됨!")
                st.rerun()
    
    st.markdown("---")
    
    # 프로젝트 필터
    if DB_AVAILABLE:
        all_tasks = get_tasks(user_id)
        projects = list(set([t.get("project","") for t in all_tasks if t.get("project")]))
        
        if projects:
            proj_filter = st.selectbox("프로젝트 필터", ["전체"] + projects, key="proj_filter")
            if proj_filter != "전체":
                all_tasks = [t for t in all_tasks if t.get("project") == proj_filter]
        
        # 칸반 보드
        col_todo, col_doing, col_done = st.columns(3)
        
        with col_todo:
            st.markdown("### 📋 할 일")
            todo_tasks = [t for t in all_tasks if t["status"] == "todo"]
            for t in todo_tasks:
                prio = "🔴" if t.get("priority")=="high" else "🟡" if t.get("priority")=="medium" else "🟢"
                with st.container():
                    st.markdown(f"{prio} **{t['title']}**")
                    if t.get("project"):
                        st.caption(f"📁 {t['project']}")
                    if t.get("due_date"):
                        st.caption(f"📅 {t['due_date']}")
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("▶️", key=f"start_{t['id']}", help="진행중으로"):
                            update_task(t["id"], status="doing")
                            st.rerun()
                    with bc2:
                        if st.button("🗑️", key=f"del_{t['id']}", help="삭제"):
                            delete_task(t["id"])
                            st.rerun()
                    st.markdown("---")
        
        with col_doing:
            st.markdown("### 🔄 진행중")
            doing_tasks = [t for t in all_tasks if t["status"] == "doing"]
            for t in doing_tasks:
                prio = "🔴" if t.get("priority")=="high" else "🟡" if t.get("priority")=="medium" else "🟢"
                with st.container():
                    st.markdown(f"{prio} **{t['title']}**")
                    if t.get("project"):
                        st.caption(f"📁 {t['project']}")
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("✅", key=f"done_{t['id']}", help="완료"):
                            update_task(t["id"], status="done")
                            st.rerun()
                    with bc2:
                        if st.button("◀️", key=f"back_{t['id']}", help="할일로"):
                            update_task(t["id"], status="todo")
                            st.rerun()
                    st.markdown("---")
        
        with col_done:
            st.markdown("### ✅ 완료")
            done_tasks = [t for t in all_tasks if t["status"] == "done"]
            for t in done_tasks[:10]:
                st.markdown(f"~~{t['title']}~~")
                if st.button("🗑️", key=f"deldone_{t['id']}"):
                    delete_task(t["id"])
                    st.rerun()
    else:
        st.info("DB 연결 후 태스크를 사용할 수 있습니다.")


# =============================================
# 📅 캘린더
# =============================================
elif page == "📅 캘린더":
    st.markdown("## 📅 캘린더")
    
    # 일정 추가
    with st.expander("➕ 새 일정 추가", expanded=False):
        ec1, ec2 = st.columns(2)
        with ec1:
            event_title = st.text_input("일정 제목", key="new_event_title")
            event_date = st.date_input("날짜", key="new_event_date")
        with ec2:
            event_time = st.time_input("시간", key="new_event_time")
            event_desc = st.text_input("메모 (선택)", key="new_event_desc")
        event_color = st.color_picker("색상", "#3b82f6", key="event_color")
        
        if st.button("일정 추가", type="primary", key="add_event_btn"):
            if event_title and DB_AVAILABLE:
                start = datetime.combine(event_date, event_time)
                create_event(user_id, event_title, start, description=event_desc, color=event_color)
                st.success("일정 추가됨!")
                st.rerun()
    
    st.markdown("---")
    
    # 이번 주 일정
    if DB_AVAILABLE:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        events = get_events(user_id, datetime.combine(week_start, datetime.min.time()), datetime.combine(week_end, datetime.max.time()))
        
        st.markdown(f"### 📆 이번 주 ({week_start.strftime('%m/%d')} - {week_end.strftime('%m/%d')})")
        
        for day_offset in range(7):
            day = week_start + timedelta(days=day_offset)
            day_name = ["월", "화", "수", "목", "금", "토", "일"][day_offset]
            is_today = day == today
            
            day_events = [e for e in events if e.get("start_time", "")[:10] == str(day)]
            
            prefix = "**👉 " if is_today else ""
            suffix = " (오늘)**" if is_today else ""
            
            st.markdown(f"{prefix}{day.strftime('%m/%d')} ({day_name}){suffix}")
            
            if day_events:
                for e in day_events:
                    time_str = e.get("start_time", "")[11:16] if e.get("start_time") else ""
                    col_e, col_d = st.columns([5, 1])
                    with col_e:
                        st.markdown(f"　⏰ {time_str} - {e['title']}")
                    with col_d:
                        if st.button("🗑️", key=f"del_ev_{e['id']}"):
                            delete_event(e["id"])
                            st.rerun()
            else:
                st.caption("　일정 없음")
        
        # AI 일정 최적화
        st.markdown("---")
        if st.button("⚡ AI 일정 최적화", type="primary"):
            with st.spinner("분석 중..."):
                schedule_text = "\n".join([f"- {e.get('start_time','')[:16]} {e['title']}" for e in events])
                prompt = f"이번 주 일정:\n{schedule_text}\n\n시간 활용 최적화 방안과 빈 시간 활용법을 제안해주세요."
                result = get_ai_response(prompt, st.session_state.ai_engine, "analysis")
                st.markdown(result)
    else:
        st.info("DB 연결 후 캘린더를 사용할 수 있습니다.")


# =============================================
# 💰 재정 관리
# =============================================
elif page == "💰 재정":
    st.markdown("## 💰 재정 관리")
    
    # 빠른 지출 입력
    with st.expander("➕ 지출 기록", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            exp_amount = st.number_input("금액 (원)", min_value=0, step=1000, key="exp_amount")
        with fc2:
            exp_category = st.selectbox("카테고리", ["식비", "교통비", "쇼핑", "생활비", "의료", "교육", "여가", "카페", "구독", "기타"], key="exp_cat")
        with fc3:
            exp_date = st.date_input("날짜", key="exp_date")
        exp_desc = st.text_input("메모", key="exp_desc")
        
        if st.button("기록하기", type="primary", key="add_exp_btn"):
            if exp_amount > 0 and DB_AVAILABLE:
                add_expense(user_id, exp_amount, exp_category, exp_desc, exp_date)
                st.success(f"✅ {exp_category} {exp_amount:,}원 기록됨!")
                st.rerun()
    
    st.markdown("---")
    
    # 이달 현황
    if DB_AVAILABLE:
        current_month = datetime.now().strftime("%Y-%m")
        month_expenses = get_expenses(user_id, current_month)
        
        if month_expenses:
            total = sum(e.get("amount", 0) for e in month_expenses)
            st.markdown(f"### 📊 {datetime.now().strftime('%Y년 %m월')} 현황")
            st.metric("이달 총 지출", f"{total:,}원")
            
            # 카테고리별
            categories = {}
            for e in month_expenses:
                cat = e.get("category", "기타")
                categories[cat] = categories.get(cat, 0) + e.get("amount", 0)
            
            st.markdown("#### 카테고리별 지출")
            for cat, amt in sorted(categories.items(), key=lambda x: -x[1]):
                pct = amt / total * 100 if total > 0 else 0
                st.progress(pct / 100, text=f"{cat}: {amt:,}원 ({pct:.1f}%)")
            
            # 최근 내역
            st.markdown("#### 최근 내역")
            for e in month_expenses[:10]:
                st.markdown(f"- {e.get('expense_date','')} | {e.get('category','')} | {e.get('amount',0):,}원 | {e.get('description','')}")
            
            # AI 분석
            st.markdown("---")
            if st.button("🤖 AI 재정 분석", type="primary"):
                with st.spinner("분석 중..."):
                    prompt = f"""이달 지출 분석:
총 지출: {total:,}원
카테고리별: {json.dumps(categories, ensure_ascii=False)}

절약 방안과 예산 제안을 해주세요."""
                    result = get_ai_response(prompt, st.session_state.ai_engine, "analysis")
                    st.markdown(result)
        else:
            st.info("이달 지출 기록이 없습니다. 위에서 기록을 시작하세요!")
    else:
        st.info("DB 연결 후 재정 관리를 사용할 수 있습니다.")


# =============================================
# ✨ AI 콘텐츠 생성
# =============================================
elif page == "✨ AI 콘텐츠":
    st.markdown("## ✨ AI 콘텐츠 생성기")
    
    content_type = st.selectbox("생성할 콘텐츠", ["블로그", "인스타그램", "트위터 스레드", "전체 패키지"])
    topic = st.text_area("📌 주제", placeholder="예: AI로 생산성 높이는 5가지 방법")
    keywords = st.text_input("🔑 키워드 (쉼표로 구분)", placeholder="예: AI, 자동화, 효율성")
    
    engine_choice = st.radio("AI 엔진", ["자동 선택", "Gemini", "Claude"], horizontal=True)
    engine_map = {"자동 선택": "auto", "Gemini": "gemini", "Claude": "claude"}
    
    if st.button("✨ 생성하기", type="primary", use_container_width=True):
        if not topic:
            st.error("주제를 입력하세요!")
        else:
            with st.spinner("AI가 열심히 작성 중..."):
                prompts = {
                    "블로그": f"주제: {topic}\n키워드: {keywords}\n\n매력적인 블로그 글을 작성해주세요. 제목 3개 옵션, SEO 메타 설명, 본문 1500-2000자, 해시태그 10개를 포함해주세요.",
                    "인스타그램": f"주제: {topic}\n키워드: {keywords}\n\n인스타그램 포스트를 작성해주세요. 강력한 훅, 본문 2000자 이내, 해시태그 30개를 포함해주세요.",
                    "트위터 스레드": f"주제: {topic}\n키워드: {keywords}\n\n트위터 스레드 5-8개 트윗, 각 280자 이내로 작성해주세요.",
                }
                
                if content_type == "전체 패키지":
                    for ctype in ["블로그", "인스타그램", "트위터 스레드"]:
                        st.markdown(f"### {ctype}")
                        result = get_ai_response(prompts[ctype], engine_map[engine_choice], "content")
                        st.markdown(result)
                        st.markdown("---")
                else:
                    result = get_ai_response(prompts[content_type], engine_map[engine_choice], "content")
                    st.markdown(result)
                    
                    # 노트로 저장
                    if DB_AVAILABLE and st.button("📝 노트로 저장"):
                        create_note(user_id, f"[콘텐츠] {topic[:30]}", result, "note")
                        st.success("노트에 저장됨!")


# =============================================
# 🎙️ 전사 / 회의록
# =============================================
elif page == "🎙️ 전사/회의록":
    st.markdown("## 🎙️ 전사 & 회의록")
    
    tab_trans, tab_terms = st.tabs(["🎙️ 전사/분석", "📖 용어 사전"])
    
    with tab_trans:
        st.markdown("### 음성 파일 전사")
        audio_file = st.file_uploader("음성 파일 업로드", type=["mp3", "wav", "m4a", "ogg", "webm"], key="audio_upload")
        
        if audio_file:
            st.audio(audio_file)
            
            if st.button("🎙️ 전사 시작", type="primary"):
                with st.spinner("전사 중... (파일 크기에 따라 시간이 걸릴 수 있습니다)"):
                    transcript = transcribe_audio(audio_file)
                    
                    # 용어 교정 적용
                    if DB_AVAILABLE:
                        transcript = apply_custom_terms(user_id, transcript)
                    
                    st.session_state.transcript = transcript
                    st.markdown("### 📄 전사 결과")
                    st.text_area("전사 내용", value=transcript, height=300, key="transcript_view")
        
        # 전사 텍스트 직접 입력
        st.markdown("---")
        st.markdown("### 또는 전사 텍스트 직접 붙여넣기")
        manual_transcript = st.text_area("갤럭시탭 전사 결과를 여기에 붙여넣으세요", height=200, key="manual_transcript")
        
        if manual_transcript:
            # 용어 교정 적용
            if DB_AVAILABLE:
                corrected = apply_custom_terms(user_id, manual_transcript)
                if corrected != manual_transcript:
                    st.markdown("### ✅ 용어 교정 적용됨")
                    st.text_area("교정된 내용", value=corrected, height=200, key="corrected_view")
                    st.session_state.transcript = corrected
                else:
                    st.session_state.transcript = manual_transcript
            else:
                st.session_state.transcript = manual_transcript
        
        # 분석 기능
        if st.session_state.get("transcript"):
            st.markdown("---")
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                if st.button("📋 회의록 생성", type="primary", use_container_width=True):
                    with st.spinner("회의록 생성 중..."):
                        summary = summarize_meeting(st.session_state.transcript)
                        st.markdown(summary)
                        if DB_AVAILABLE:
                            create_note(user_id, f"📋 회의록 {date.today()}", summary, "meeting")
                            st.success("회의록이 노트에 저장되었습니다!")
            with ac2:
                if st.button("📊 핵심 요약", use_container_width=True):
                    with st.spinner("요약 중..."):
                        result = get_ai_response(f"다음 내용의 핵심만 5줄 이내로 요약해주세요:\n\n{st.session_state.transcript}", st.session_state.ai_engine, "summary")
                        st.markdown(result)
            with ac3:
                if st.button("✅ 액션아이템 추출", use_container_width=True):
                    with st.spinner("추출 중..."):
                        result = get_ai_response(f"다음 내용에서 액션 아이템(해야 할 일)만 추출해주세요. 체크박스 형태로:\n\n{st.session_state.transcript}", st.session_state.ai_engine, "analysis")
                        st.markdown(result)
    
    with tab_terms:
        st.markdown("### 📖 나만의 용어 사전")
        st.caption("자주 틀리는 전사 용어를 등록하면 자동으로 교정됩니다.")
        
        tc1, tc2 = st.columns(2)
        with tc1:
            wrong = st.text_input("잘못 전사되는 단어", placeholder="예: 케이피아이", key="wrong_term")
        with tc2:
            correct = st.text_input("올바른 단어", placeholder="예: KPI", key="correct_term")
        
        if st.button("등록", type="primary", key="add_term_btn"):
            if wrong and correct and DB_AVAILABLE:
                add_custom_term(user_id, wrong, correct)
                st.success(f"✅ '{wrong}' → '{correct}' 등록됨!")
                st.rerun()
        
        # 등록된 용어 목록
        if DB_AVAILABLE:
            terms = get_custom_terms(user_id)
            if terms:
                st.markdown("#### 등록된 용어")
                for w, c in terms.items():
                    st.markdown(f"- ~~{w}~~ → **{c}**")


# =============================================
# ⚙️ 설정
# =============================================
elif page == "⚙️ 설정":
    st.markdown("## ⚙️ 설정")
    
    st.markdown("### 🔑 API 키")
    gemini_key = st.text_input("Gemini API 키", value=st.session_state.gemini_api_key, type="password", key="set_gemini")
    claude_key = st.text_input("Claude API 키 (선택사항)", value=st.session_state.claude_api_key, type="password", key="set_claude", help="없으면 Gemini만 사용됩니다")
    
    if st.button("API 키 저장", type="primary"):
        st.session_state.gemini_api_key = gemini_key
        st.session_state.claude_api_key = claude_key
        st.success("저장 완료!")
    
    st.markdown("---")
    st.markdown("### 🤖 AI 엔진 설정")
    ai_mode = st.radio("기본 AI 엔진", ["auto", "gemini", "claude"], 
                        format_func=lambda x: {"auto":"🔄 자동 선택 (추천)","gemini":"Gemini","claude":"Claude"}[x],
                        index=["auto","gemini","claude"].index(st.session_state.ai_engine))
    st.session_state.ai_engine = ai_mode
    
    if ai_mode == "auto":
        st.info("작업 유형에 따라 최적의 AI가 자동 선택됩니다. Claude API 키가 없으면 Gemini가 사용됩니다.")
    
    st.markdown("---")
    st.markdown("### 📊 사용 현황")
    if DB_AVAILABLE:
        notes_count = len(get_notes(user_id))
        tasks_count = len(get_tasks(user_id))
        c1, c2, c3 = st.columns(3)
        c1.metric("노트", f"{notes_count}개")
        c2.metric("태스크", f"{tasks_count}개")
        c3.metric("DB 상태", "연결됨 ✅")
    else:
        st.warning("DB 미연결 — 데모 모드로 동작 중")
    
    st.markdown("---")
    st.markdown("### ℹ️ 정보")
    st.caption("나만의 AI 에이전트 v1.0")
    st.caption("Streamlit + Supabase + Gemini + Claude")
    st.caption("월 비용: 0원 (모든 무료 티어)")


# ===== 푸터 =====
st.markdown("---")
st.caption("🚀 나만의 AI 에이전트 | Powered by Gemini + Claude")
