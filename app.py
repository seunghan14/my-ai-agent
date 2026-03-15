import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta
import json, calendar, math, re

st.set_page_config(page_title="Personal Assistant", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

defs = {
    "logged_in":False,"user":None,"current_page":"🏠 Dashboard","prev_page":"🏠 Dashboard",
    "gemini_api_key":"","claude_api_key":"","ai_engine":"auto",
    "editing_note":None,"editing_task":None,"theme":"light",
    "transcript":"","gemini_model":"gemini-2.5-flash",
    "show_related":False,"qc_preview":None,"qc_text":"",
    "temp_note_save":None,"ai_result":None,"ai_result_type":None,
    "time_reset_key":0,"cal_prefill_date":None,
    "dash_widgets":{"habits":True,"pinned":True,"recent":True,"tasks":True,"reminders":True}
}
for k,v in defs.items():
    if k not in st.session_state: st.session_state[k]=v

try:
    from db_utils import *
    from ai_engine import *
    DB=True
except: DB=False

# ===== THEME =====
th=st.session_state.theme
if th=="dark":
    st.markdown("""<style>
/* 전체 배경 */
.stApp, .stApp > div, section.main, section.main > div {background:#121212 !important}
/* 사이드바 */
section[data-testid="stSidebar"] {background:#1a1a1a !important}
section[data-testid="stSidebar"] > div {background:#1a1a1a !important}
section[data-testid="stSidebar"] * {color:#c8c8c8 !important}
/* 전체 텍스트 - 눈에 편한 연회색 */
.stApp, .stApp p, .stApp span, .stApp label, .stApp div {color:#c8c8c8}
h1,h2,h3,h4 {color:#e8e8e8 !important}
/* 입력창 */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background:#2a2a2a !important; color:#e0e0e0 !important; border-color:#444 !important}
.stSelectbox > div > div {background:#2a2a2a !important; color:#e0e0e0 !important}
/* 버튼 */
.stButton > button {background:#2a2a2a !important; color:#e0e0e0 !important; border:1px solid #444 !important}
.stButton > button:hover {background:#3a3a3a !important}
/* 메트릭 */
div[data-testid="stMetric"] {background:#1e1e1e; border:1px solid #333; border-radius:8px; padding:10px}
div[data-testid="stMetricValue"] {color:#e8e8e8 !important}
/* 익스팬더 */
div[data-testid="stExpander"] {border:1px solid #333; border-radius:8px}
div[data-testid="stExpander"] summary {color:#c8c8c8 !important}
/* 탭 */
div[data-baseweb="tab-list"] {background:#1a1a1a !important}
button[data-baseweb="tab"] {color:#aaa !important}
button[data-baseweb="tab"][aria-selected="true"] {color:#e8e8e8 !important}
/* 구분선 */
hr {border-color:#333 !important}
/* 캡션 */
.stMarkdown small, caption {color:#888 !important}
/* 정보/경고 박스 */
div[data-testid="stInfo"] {background:#1e3a5f !important; color:#c8d8f0 !important}
div[data-testid="stWarning"] {background:#3a2a00 !important; color:#f0d080 !important}
div[data-testid="stSuccess"] {background:#0a3a1a !important; color:#80d0a0 !important}
div[data-testid="stError"] {background:#3a0a0a !important; color:#f08080 !important}
/* 프로그레스 바 배경 */
div[data-testid="stProgressBar"] > div {background:#333 !important}
/* 체크박스 */
label[data-testid="stCheckbox"] span {color:#c8c8c8 !important}
/* 라디오 */
div[data-testid="stRadio"] label {color:#c8c8c8 !important}
/* 코드 블록 */
code {background:#2a2a2a !important; color:#f0a080 !important}
</style>""", unsafe_allow_html=True)

st.markdown('<style>@media(max-width:768px){[data-testid="stHorizontalBlock"]>div{flex:100%!important;max-width:100%!important}}</style>',unsafe_allow_html=True)

COLOR_PRESETS={"blue":"#3b82f6","red":"#ef4444","green":"#22c55e","purple":"#8b5cf6",
               "orange":"#f97316","pink":"#ec4899","teal":"#14b8a6","yellow":"#eab308",
               "gray":"#6b7280","indigo":"#6366f1"}
COLOR_DOTS={"blue":"🔵","red":"🔴","green":"🟢","purple":"🟣","orange":"🟠",
            "pink":"🩷","teal":"🩵","yellow":"🟡","gray":"⚫","indigo":"🔷"}

def get_default_event_time():
    now=datetime.now(); next_15=math.ceil((now.minute+1)/15)*15
    if next_15>=60: return now.replace(hour=(now.hour+1)%24,minute=0,second=0,microsecond=0).time()
    return now.replace(minute=next_15,second=0,microsecond=0).time()

def get_label(color_key,custom_labels):
    if custom_labels and color_key in custom_labels: return custom_labels[color_key].get("label",color_key.capitalize())
    return color_key.capitalize()

def get_group(task):
    p=task.get("project","") or ""
    if p.lower()=="personal": return "personal"
    if p: return "project"
    return "general"

def clear_nc():
    if "nc" in st.session_state: del st.session_state["nc"]

# ===== 임시저장: prev_page 기반 =====
current_page_now = st.session_state.current_page
prev_page_now = st.session_state.get("prev_page", current_page_now)

if prev_page_now == "📝 Notes" and current_page_now != "📝 Notes":
    if st.session_state.get("editing_note"):
        note_tmp = st.session_state.editing_note
        temp_c = st.session_state.get("nc", note_tmp.get("content","") if note_tmp else "")
        temp_t = st.session_state.get("nt", note_tmp.get("title","") if note_tmp else "")
        if temp_c or temp_t:
            st.session_state["temp_note_save"] = {"note": note_tmp, "content": temp_c, "title": temp_t}
        st.session_state.editing_note = None

st.session_state.prev_page = current_page_now

# ===== SIDEBAR =====
with st.sidebar:
    if not st.session_state.logged_in:
        st.markdown("## 🚀 Personal Assistant")
        tab=st.radio("",["Login","Sign Up"],horizontal=True,label_visibility="collapsed")
        if tab=="Login":
            em=st.text_input("Email",key="le"); pw=st.text_input("Password",type="password",key="lp")
            if st.button("Login",use_container_width=True,type="primary"):
                if DB:
                    u,err=login_user(em,pw)
                    if u: st.session_state.logged_in=True;st.session_state.user=u;st.rerun()
                    else: st.error(err)
                else:
                    st.session_state.logged_in=True
                    st.session_state.user={"id":"demo","email":em,"display_name":em.split("@")[0]}
                    st.rerun()
        else:
            nm=st.text_input("Name",key="rn");em=st.text_input("Email",key="re")
            pw=st.text_input("Password",type="password",key="rp");pw2=st.text_input("Confirm",type="password",key="rp2")
            if st.button("Sign Up",use_container_width=True,type="primary"):
                if pw!=pw2: st.error("Passwords don't match")
                elif DB:
                    u,err=register_user(em,pw,nm)
                    if u: st.success("Done! Please login.")
                    else: st.error(err)
    else:
        user=st.session_state.user; uid=user["id"]
        dname=user.get("display_name",user.get("email","").split("@")[0])
        st.markdown(f"## 🚀 {dname}'s Assistant")
        st.markdown("---")
        st.markdown("### ⚡ Quick Capture")
        qtext=st.text_input("",placeholder="무엇이든 입력하세요...",label_visibility="collapsed",key="qi")
        if qtext:
            qc1,qc2=st.columns(2)
            if qc1.button("🤖 미리보기",use_container_width=True,key="qp"):
                if DB:
                    with st.spinner("분류 중..."):
                        c=smart_classify(qtext); st.session_state.qc_preview=c; st.session_state.qc_text=qtext
            if qc2.button("💾 바로저장",use_container_width=True,key="qs"):
                if DB: create_note(uid,qtext[:50],qtext); st.success("📝 저장!"); st.rerun()
        if st.session_state.get("qc_preview"):
            c=st.session_state.qc_preview; ct=c.get("type","note")
            icons={"task":"✅","expense":"💰","note":"📝","event":"📅"}
            st.info(f"{icons.get(ct,'📝')} **{ct.upper()}**: {c.get('title',qtext)[:40]}")
            cc1,cc2=st.columns(2)
            if cc1.button("✅ 확인저장",use_container_width=True,key="qcs"):
                if DB:
                    qt=st.session_state.get("qc_text","")
                    if ct=="task": create_task(uid,c.get("title",qt)); st.success("✅!")
                    elif ct=="expense" and c.get("amount"): add_expense(uid,int(c["amount"]),c.get("category","기타"),qt); st.success("💰!")
                    else: create_note(uid,c.get("title",qt[:50]),qt); st.success("📝!")
                    st.session_state.qc_preview=None; st.session_state.qc_text=""; st.rerun()
            if cc2.button("📝 노트로",use_container_width=True,key="qcn"):
                if DB:
                    qt=st.session_state.get("qc_text","")
                    create_note(uid,qt[:50],qt); st.success("📝!")
                    st.session_state.qc_preview=None; st.rerun()

        st.markdown("### 🔍 Search")
        sidebar_search=st.text_input("",placeholder="빠른 검색...",label_visibility="collapsed",key="sidebar_sq")
        if sidebar_search and DB:
            results=search_all(uid,sidebar_search)
            if results:
                for r in results[:5]:
                    icon={"note":"📝","task":"✅","event":"📅"}.get(r["type"],"📄")
                    st.caption(f"{icon} {r['title'][:25]}")
            else: st.caption("결과 없음")

        st.markdown("---")
        pages=["🏠 Dashboard","📅 Calendar","✅ Tasks","📝 Notes","🎙️ Transcription",
               "✨ AI Content","💹 Economy","📧 Email","🔗 Web Clipper","🍅 Pomodoro",
               "📊 Weekly Report","🔍 Search","⚙️ Settings"]
        new_page=st.radio("",pages,label_visibility="collapsed",
                          index=pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0)
        if new_page!=st.session_state.current_page:
            st.session_state.current_page=new_page; st.rerun()

        st.markdown("---")
        tt=st.radio("",["☀️ Light","🌙 Dark"],horizontal=True,label_visibility="collapsed",index=0 if th=="light" else 1)
        nt="light" if "Light" in tt else "dark"
        if nt!=st.session_state.theme: st.session_state.theme=nt; st.rerun()
        if st.button("Logout",use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

if not st.session_state.logged_in:
    st.markdown("# 🚀 Personal Assistant")
    st.info("👈 Login from sidebar"); st.stop()

user=st.session_state.user; uid=user["id"]; dname=user.get("display_name","User")
page=st.session_state.current_page

# ===== DASHBOARD =====
if page=="🏠 Dashboard":
    col_title,col_cfg=st.columns([5,1])
    col_title.markdown(f"## 🏠 {dname}님, 좋은 하루 되세요!")
    with col_cfg.expander("⚙️ 위젯"):
        dw=st.session_state.dash_widgets
        dw["reminders"]=st.checkbox("리마인더",value=dw.get("reminders",True))
        dw["habits"]=st.checkbox("목표&습관",value=dw.get("habits",True))
        dw["pinned"]=st.checkbox("핀 위젯",value=dw.get("pinned",True))
        dw["recent"]=st.checkbox("최근 노트",value=dw.get("recent",True))
        dw["tasks"]=st.checkbox("오늘 할 일",value=dw.get("tasks",True))
        st.session_state.dash_widgets=dw
    if DB:
        tasks=get_tasks(uid)
        backlog=[t for t in tasks if t["status"]=="backlog"]
        todo=[t for t in tasks if t["status"]=="todo"]
        doing=[t for t in tasks if t["status"]=="doing"]
        done_t=[t for t in tasks if t["status"]=="done"]
        c1,c2,c3,c4=st.columns(4)
        c1.metric("📋 Backlog",len(backlog));c2.metric("📝 To Do",len(todo))
        c3.metric("🔄 진행중",len(doing));c4.metric("✅ 완료",len(done_t))
        if dw.get("reminders",True):
            upcoming=[t for t in todo+doing if t.get("due_date") and t["due_date"]<=str(date.today()+timedelta(days=2))]
            if upcoming:
                st.warning(f"⚠️ {len(upcoming)}개 태스크 마감 임박!")
                for t in upcoming:
                    st.markdown(f"- {'🔴' if t.get('priority')=='high' else '🟡'} **{t['title']}** — {t['due_date']}")
        if dw.get("habits",True):
            st.markdown("---"); st.markdown("### 🎯 목표 & 습관")
            habits=get_habits(uid)
            if habits:
                logs=get_habit_logs(uid,date.today(),date.today())
                done_ids={l["habit_id"] for l in logs if l.get("completed")}
                log_values={l["habit_id"]:l.get("value",0) for l in logs}
                cols=st.columns(min(len(habits),4))
                for i,h in enumerate(habits):
                    with cols[i%min(len(habits),4)]:
                        htype=h.get("habit_type","check")
                        if htype=="numeric":
                            target=float(h.get("target_value",1)); unit=h.get("unit","")
                            cur_val=float(log_values.get(h["id"],0))
                            st.markdown(f"**{h.get('icon','🎯')} {h['name']}**")
                            new_val=st.number_input(f"목표: {target}{unit}",min_value=0.0,max_value=target*3,value=cur_val,step=0.5,key=f"hv_{h['id']}")
                            pct=min(new_val/target,1.0) if target>0 else 0
                            st.progress(pct,text=f"{new_val}/{target}{unit}")
                            # 완료 체크박스 (목표 달성 시 자동 체크)
                            auto_done = pct >= 1.0
                            done_check=st.checkbox("✅ 완료",value=h["id"] in done_ids or auto_done,key=f"hnc_{h['id']}")
                            if st.button("저장",key=f"hsv_{h['id']}",use_container_width=True):
                                toggle_habit_value(h["id"],uid,new_val if done_check else 0)
                        else:
                            checked=st.checkbox(f"{h.get('icon','✅')} {h['name']}",value=h["id"] in done_ids,key=f"h_{h['id']}")
                            if checked!=(h["id"] in done_ids): toggle_habit(h["id"],uid)
                ws_d=date.today()-timedelta(days=date.today().weekday())
                wl=get_habit_logs(uid,ws_d,date.today())
                wc=len([l for l in wl if l.get("completed")]); wt=len(habits)*(date.today().weekday()+1)
                r=int(wc/wt*100) if wt>0 else 0
                st.progress(r/100,text=f"이번 주: {r}% ({wc}/{wt})")
            else: st.info("Settings에서 목표/습관을 추가하세요!")
        if dw.get("pinned",True):
            pins=get_pinned(uid)
            if pins:
                st.markdown("---"); st.markdown("### 📌 Pinned")
                for p in pins: st.markdown(f"{'📝' if p['item_type']=='note' else '🔗'} **{p['title']}**")
        st.markdown("---")
        co1,co2=st.columns(2)
        if dw.get("recent",True):
            with co1:
                st.markdown("### 📝 최근 노트")
                for n in get_notes(uid)[:5]: st.markdown(f"**{n['title']}** · _{n.get('updated_at','')[:10]}_")
        if dw.get("tasks",True):
            with co2:
                st.markdown("### ✅ 오늘 할 일")
                for t in todo[:5]:
                    p="🔴" if t.get("priority")=="high" else "🟡" if t.get("priority")=="medium" else "🟢"
                    st.markdown(f"{p} {t['title']}")
                if not todo: st.info("All done! 🎉")
        st.markdown("---")
        bc1,bc2=st.columns(2)
        if bc1.button("☀️ Morning Briefing",type="primary",use_container_width=True):
            with st.spinner("..."): st.markdown(get_ai(f"오늘:{datetime.now().strftime('%Y-%m-%d %A')}. 할일:{len(todo)}, 진행:{len(doing)}.\n간결한 아침 브리핑: 1)오늘 집중 2)팁 3)동기부여",st.session_state.ai_engine,"summary"))
        if bc2.button("🌙 Daily Review",use_container_width=True):
            with st.spinner("..."):
                today_notes=[n for n in get_notes(uid) if n.get("updated_at","")[:10]==str(date.today())]
                st.markdown(get_ai(f"오늘 작성 노트:{len(today_notes)}개, 완료 태스크:{len(done_t)}개.\n오늘의 회고: 1)한일 2)배운점 3)내일계획",st.session_state.ai_engine,"summary"))

# ===== CALENDAR =====
elif page=="📅 Calendar":
    st.markdown("## 📅 Calendar")
    view=st.radio("",["Monthly","Weekly","Daily","List"],horizontal=True,label_visibility="collapsed")
    custom_labels=get_color_labels(uid) if DB else {}

    # 날짜 클릭으로 사전 입력된 날짜 처리
    prefill_date = st.session_state.get("cal_prefill_date") or date.today()
    default_start=get_default_event_time()
    default_end=(datetime.combine(date.today(),default_start)+timedelta(hours=1)).time()
    tkey=st.session_state.time_reset_key

    with st.expander("➕ New Event", expanded=bool(st.session_state.get("cal_prefill_date"))):
        et=st.text_input("Title",key="et",placeholder="일정 제목")
        dc1,dc2,dc3,dc4=st.columns([2,1,1,1])
        ed=dc1.date_input("Date",value=prefill_date,key=f"ed_{tkey}")
        etime_s=dc2.time_input("Start",value=default_start,key=f"etm_s_{tkey}",step=timedelta(minutes=15))
        etime_e=dc3.time_input("End",value=default_end,key=f"etm_e_{tkey}",step=timedelta(minutes=15))
        if dc4.button("🕐 지금",help="현재 시각으로 리셋",key="reset_time"):
            st.session_state.time_reset_key+=1
            if "cal_prefill_date" in st.session_state: del st.session_state["cal_prefill_date"]
            st.rerun()
        label_opts={k:get_label(k,custom_labels) for k in COLOR_PRESETS.keys()}
        cl=st.selectbox("Label",list(label_opts.keys()),format_func=lambda x:f"{COLOR_DOTS.get(x,'🔵')} {label_opts[x]}",key="ev_label")
        edesc=st.text_area("Memo",key="edesc",height=80,placeholder="메모 (선택)")
        if st.button("Add Event",type="primary",key="ae"):
            if not et: st.warning("⚠️ 제목을 입력해주세요.")
            elif DB:
                try:
                    result=create_event(uid,et,datetime.combine(ed,etime_s),end=datetime.combine(ed,etime_e),desc=edesc,color_label=cl)
                    if result:
                        st.success("✅ 추가됨!")
                        st.session_state.cal_prefill_date=None
                        st.rerun()
                    else: st.error("❌ 추가 실패.")
                except Exception as e: st.error(f"❌ 오류: {e}")

    if DB:
        today=date.today()
        if view=="Monthly":
            ms=today.replace(day=1); last_day=calendar.monthrange(today.year,today.month)[1]; me=ms.replace(day=last_day)
            evs=get_events(uid,datetime.combine(ms,datetime.min.time()),datetime.combine(me,datetime.max.time()))
            st.markdown(f"### {today.strftime('%Y년 %m월')}")
            hc=st.columns(7)
            for i,d_name in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]): hc[i].markdown(f"**{d_name}**")
            for week in calendar.monthcalendar(today.year,today.month):
                cols=st.columns(7)
                for i,day in enumerate(week):
                    if day==0: cols[i].markdown("")
                    else:
                        des=[e for e in evs if e.get("start_time","")[:10]==f"{today.year}-{today.month:02d}-{day:02d}"]
                        is_today=(day==today.day)
                        mk=f"**👉{day}**" if is_today else (f"**{day}📌**" if des else str(day))
                        if cols[i].button(mk,key=f"cal_day_{day}",use_container_width=True,
                                          help=f"{today.year}-{today.month:02d}-{day:02d} 클릭 → 일정 추가"):
                            st.session_state.cal_prefill_date=date(today.year,today.month,day)
                            st.session_state.time_reset_key+=1; st.rerun()
                        for e in des:
                            c=COLOR_PRESETS.get(e.get("color_label","blue"),"#3b82f6")
                            cols[i].markdown(f'<div style="background:{c}22;border-left:2px solid {c};padding:2px 4px;margin:1px 0;border-radius:3px;font-size:10px">⏰{e.get("start_time","")[11:16]} {e["title"][:10]}</div>',unsafe_allow_html=True)
        elif view=="Weekly":
            ws=today-timedelta(days=today.weekday())
            evs=get_events(uid,datetime.combine(ws,datetime.min.time()),datetime.combine(ws+timedelta(6),datetime.max.time()))
            day_names=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            header_cols=st.columns(7)
            for i,(col,dn) in enumerate(zip(header_cols,day_names)):
                day=ws+timedelta(i); is_today=(day==today)
                bg="background:#3b82f622;border-radius:8px;padding:4px;" if is_today else ""
                col.markdown(f'<div style="{bg}text-align:center"><b>{"👉 " if is_today else ""}{dn}</b><br><small>{day.strftime("%m/%d")}</small></div>',unsafe_allow_html=True)
            st.markdown('<hr style="margin:6px 0">',unsafe_allow_html=True)
            event_cols=st.columns(7)
            for i,col in enumerate(event_cols):
                day=ws+timedelta(i); day_evs=[e for e in evs if e.get("start_time","")[:10]==str(day)]
                with col:
                    if day_evs:
                        for e in day_evs:
                            color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3b82f6")
                            st.markdown(f'<div style="background:{color}20;border-left:3px solid {color};padding:4px 6px;margin:3px 0;border-radius:4px;font-size:11px"><b>{e.get("start_time","")[11:16]}</b><br>{e["title"]}</div>',unsafe_allow_html=True)
                            if col.button("🗑️",key=f"wde_{e['id']}"): delete_event(e["id"]);st.rerun()
                    else: col.markdown('<div style="text-align:center;color:#aaa;font-size:12px;padding:8px">—</div>',unsafe_allow_html=True)
        elif view=="Daily":
            sd=st.date_input("",value=today,label_visibility="collapsed")
            evs=get_events(uid,datetime.combine(sd,datetime.min.time()),datetime.combine(sd,datetime.max.time()))
            st.markdown(f"### {sd.strftime('%Y-%m-%d (%A)')}")
            today_tasks=[t for t in get_tasks(uid) if t.get("due_date")==str(sd) and t["status"]!="done"]
            if today_tasks:
                st.markdown("**📋 마감 태스크:**")
                for t in today_tasks:
                    p="🔴" if t.get("priority")=="high" else "🟡" if t.get("priority")=="medium" else "🟢"
                    st.markdown(f"　{p} {t['title']}")
            if evs:
                for e in evs:
                    color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3b82f6")
                    c1,c2=st.columns([6,1])
                    c1.markdown(f'<div style="border-left:3px solid {color};padding:6px 10px;margin:4px 0"><b>⏰ {e.get("start_time","")[11:16]}</b> — {e["title"]}{"<br><small>"+e["description"]+"</small>" if e.get("description") else ""}</div>',unsafe_allow_html=True)
                    if c2.button("🗑️",key=f"de_{e['id']}"): delete_event(e["id"]);st.rerun()
            else: st.info("일정 없음")
        else:
            evs=get_events(uid,datetime.combine(today,datetime.min.time()),datetime.combine(today+timedelta(30),datetime.max.time()))
            if evs:
                for e in evs:
                    color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3b82f6")
                    label_name=get_label(e.get("color_label","blue"),custom_labels)
                    st.markdown(f'<div style="border-left:3px solid {color};padding:6px 10px;margin:4px 0">📅 {e.get("start_time","")[:10]} &nbsp; ⏰ {e.get("start_time","")[11:16]} &nbsp; <b>{e["title"]}</b> &nbsp; <span style="color:{color}">● {label_name}</span></div>',unsafe_allow_html=True)
            else: st.info("향후 30일 일정 없음")

# ===== TASKS =====
elif page=="✅ Tasks":
    st.markdown("## ✅ Tasks")
    tab_kanban,tab_project=st.tabs(["📋 Kanban","📁 By Project"])

    with tab_kanban:
        with st.expander("➕ New Task"):
            tc1,tc2=st.columns(2)
            tt_new=tc1.text_input("Task 제목",key="tt")
            proj_type=tc1.selectbox("구분",["📌 General","👤 Personal","📁 Project"],key="proj_type")
            proj_name=""
            if proj_type=="📁 Project": proj_name=tc1.text_input("Project 이름",key="proj_name_input")
            elif proj_type=="👤 Personal": proj_name="Personal"
            tpr=tc2.selectbox("Priority",["high","medium","low"],format_func=lambda x:{"high":"🔴 High","medium":"🟡 Medium","low":"🟢 Low"}[x],index=1,key="tpr_new")
            tst=tc2.selectbox("초기 상태",["backlog","todo"],format_func=lambda x:{"backlog":"📋 Backlog","todo":"📝 To Do"}[x],key="tst_new")
            tdu=tc1.date_input("Due date",value=date.today(),key="td")
            td_desc=tc2.text_input("설명 (선택)",key="td_desc")
            if st.button("Add Task",type="primary",key="at"):
                if tt_new and DB: create_task(uid,tt_new,td_desc,tst,tpr,tdu,proj_name or None); st.success("✅ 추가됨!"); st.rerun()

        if st.session_state.get("editing_task"):
            t=st.session_state.editing_task
            st.markdown("---")
            st.markdown(f'<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:10px;margin:8px 0">✏️ <b>수정 중: {t.get("title","")}</b></div>',unsafe_allow_html=True)
            ec1,ec2=st.columns(2)
            new_title=ec1.text_input("제목",value=t.get("title",""),key="et_title")
            new_proj=ec1.text_input("Project/구분",value=t.get("project","") or "",key="et_proj")
            new_desc=st.text_input("설명",value=t.get("description","") or "",key="et_desc")
            status_list=["backlog","todo","doing","done"]; prio_list=["high","medium","low"]
            status_labels={"backlog":"📋 Backlog","todo":"📝 To Do","doing":"🔄 Doing","done":"✅ Done"}
            prio_labels={"high":"🔴 High","medium":"🟡 Medium","low":"🟢 Low"}
            ec2a,ec2b=ec2.columns(2)
            new_prio=ec2a.selectbox("Priority",prio_list,format_func=lambda x:prio_labels[x],
                                    index=prio_list.index(t.get("priority","medium")),key="et_prio")
            new_status=ec2b.selectbox("Status",status_list,format_func=lambda x:status_labels[x],
                                      index=status_list.index(t.get("status","todo")),key="et_status")
            due_val=date.today()
            if t.get("due_date"):
                try: due_val=date.fromisoformat(t["due_date"])
                except: pass
            new_due=st.date_input("Due date",value=due_val,key="et_due")
            sc1,sc2=st.columns(2)
            if sc1.button("💾 저장",type="primary",use_container_width=True):
                if DB:
                    update_task(t["id"],title=new_title,description=new_desc,status=new_status,
                                priority=new_prio,due_date=str(new_due),project=new_proj or None)
                    st.session_state.editing_task=None; st.success("✅ 수정됨!"); st.rerun()
            if sc2.button("취소",use_container_width=True): st.session_state.editing_task=None; st.rerun()
            st.markdown("---")

        if DB:
            at=get_tasks(uid)
            status_config=[("backlog","📋 Backlog","#94a3b8"),("todo","📝 To Do","#3b82f6"),
                           ("doing","🔄 Doing","#f97316"),("done","✅ Done","#22c55e")]
            cols_k=st.columns(4)
            for col,(s,lb,col_color) in zip(cols_k,status_config):
                with col:
                    tasks_in=[t for t in at if t["status"]==s]
                    st.markdown(f'<div style="border-top:3px solid {col_color};padding-top:8px;margin-bottom:8px"><b>{lb}</b> <small style="color:#888">({len(tasks_in)})</small></div>',unsafe_allow_html=True)
                    for t in tasks_in:
                        bc="#ef4444" if t.get("priority")=="high" else "#eab308" if t.get("priority")=="medium" else "#22c55e"
                        p_icon="🔴" if t.get("priority")=="high" else "🟡" if t.get("priority")=="medium" else "🟢"
                        grp=get_group(t)
                        proj_disp=""
                        if grp=="personal": proj_disp='<br><small style="color:#8b5cf6">👤 Personal</small>'
                        elif grp=="project": proj_disp=f'<br><small style="color:#3b82f6">📁 {t["project"]}</small>'
                        due_disp=f'<br><small style="color:#888">📅 {t["due_date"]}</small>' if t.get("due_date") else ""
                        st.markdown(f'<div style="background:#f8f9fa;border-radius:8px;padding:8px;margin:4px 0;border-left:3px solid {bc}">{p_icon} <b>{t["title"]}</b>{proj_disp}{due_disp}</div>',unsafe_allow_html=True)
                        b_cols=st.columns(4)
                        if b_cols[0].button("✏️",key=f"edit_{t['id']}",help="수정"): st.session_state.editing_task=t;st.rerun()
                        if s=="backlog":
                            if b_cols[1].button("▶️",key=f"fwd_{t['id']}",help="To Do로"): update_task(t["id"],status="todo");st.rerun()
                        elif s=="todo":
                            if b_cols[1].button("◀️",key=f"bk_{t['id']}",help="Backlog으로"): update_task(t["id"],status="backlog");st.rerun()
                            if b_cols[2].button("▶️",key=f"fwd_{t['id']}",help="Doing으로"): update_task(t["id"],status="doing");st.rerun()
                        elif s=="doing":
                            if b_cols[1].button("◀️",key=f"bk_{t['id']}",help="To Do로"): update_task(t["id"],status="todo");st.rerun()
                            if b_cols[2].button("✅",key=f"dn_{t['id']}",help="Done으로"): update_task(t["id"],status="done");st.rerun()
                        elif s=="done":
                            if b_cols[1].button("↩️",key=f"bk_{t['id']}",help="Doing으로"): update_task(t["id"],status="doing");st.rerun()
                        if b_cols[3].button("🗑️",key=f"x_{t['id']}",help="삭제"): delete_task(t["id"]);st.rerun()
                        st.markdown('<hr style="margin:4px 0;opacity:0.15">',unsafe_allow_html=True)

    with tab_project:
        if DB:
            at=get_tasks(uid)
            sort_opt=st.selectbox("정렬",["마감 임박순","이름순","Task 수 많은순"],key="proj_sort",label_visibility="collapsed")

            general=[t for t in at if get_group(t)=="general"]
            personal=[t for t in at if get_group(t)=="personal"]
            proj_map={}
            for t in at:
                if get_group(t)=="project":
                    pn=t.get("project","기타"); proj_map.setdefault(pn,[]).append(t)

            def proj_sort_key(item):
                pn,tasks=item; dues=[t["due_date"] for t in tasks if t.get("due_date")]
                if sort_opt=="마감 임박순": return min(dues) if dues else "9999"
                if sort_opt=="이름순": return pn
                return -len(tasks)
            sorted_projs=sorted(proj_map.items(),key=proj_sort_key)

            def render_group(name,tasks,icon,header_color):
                if not tasks: return
                done_c=len([t for t in tasks if t["status"]=="done"]); pct=int(done_c/len(tasks)*100) if tasks else 0
                # 그룹 헤더 - 시각적으로 명확하게
                st.markdown(f'<div style="background:{header_color}18;border:1px solid {header_color}44;border-radius:10px;padding:10px 14px;margin:12px 0 4px 0"><span style="font-size:1.1rem;font-weight:700;color:{header_color}">{icon} {name}</span> &nbsp; <small style="color:#888">{done_c}/{len(tasks)} 완료 ({pct}%)</small></div>',unsafe_allow_html=True)
                st.progress(pct/100)
                status_icons={"backlog":"📋","todo":"📝","doing":"🔄","done":"✅"}
                for t in tasks:
                    s_icon=status_icons.get(t["status"],"📝")
                    p_icon="🔴" if t.get("priority")=="high" else "🟡" if t.get("priority")=="medium" else "🟢"
                    due_str=f" · 📅{t['due_date']}" if t.get("due_date") else ""
                    # 태스크는 들여쓰기로 구분
                    st.markdown(f'<div style="margin-left:16px;padding:4px 8px;border-left:2px solid {header_color}44;margin-bottom:2px"><small>{s_icon} {p_icon} {t["title"]}{due_str}</small></div>',unsafe_allow_html=True)

            render_group("General",general,"📌","#3b82f6")
            render_group("Personal",personal,"👤","#8b5cf6")
            for pn,tasks in sorted_projs:
                render_group(pn,tasks,"📁","#22c55e")

            if not at: st.info("태스크가 없습니다.")

# ===== NOTES =====
elif page=="📝 Notes":
    st.markdown("## 📝 Notes")

    # 임시저장 복원 배너
    if st.session_state.get("temp_note_save"):
        temp=st.session_state.temp_note_save
        st.warning(f"📝 임시저장된 노트가 있습니다: **'{temp.get('title','(제목 없음)')}'**")
        rb1,rb2=st.columns(2)
        if rb1.button("✅ 이어서 편집",use_container_width=True,key="restore_note"):
            st.session_state.editing_note=temp["note"]
            st.session_state["_tmpl"]=temp["content"]
            clear_nc()
            st.session_state["temp_note_save"]=None; st.rerun()
        if rb2.button("❌ 버리기",use_container_width=True,key="discard_note"):
            st.session_state["temp_note_save"]=None; st.rerun()

    nc1,nc2,nc3,nc4=st.columns([2,1,1,1])
    sq=nc1.text_input("🔍",placeholder="Search...",label_visibility="collapsed")
    sort_notes=nc2.selectbox("",["최신순","업데이트순","이름순"],label_visibility="collapsed",key="note_sort")
    if nc3.button("📅 Daily",use_container_width=True):
        if DB: st.session_state.editing_note=get_daily_note(uid);st.session_state.show_related=False;clear_nc();st.rerun()
    if nc4.button("➕ New",type="primary",use_container_width=True):
        if DB: st.session_state.editing_note=create_note(uid,"New Note","");st.session_state.show_related=False;clear_nc();st.rerun()

    if DB:
        with st.expander("📁 Folders"):
            folders=get_folders(uid)
            fc1,fc2=st.columns([3,1])
            fn=fc1.text_input("새 폴더 이름",key="fn",placeholder="폴더 이름")
            if fc2.button("➕ 생성",key="cf"):
                if fn: create_folder(uid,fn);st.rerun()
            if folders:
                for f in folders:
                    f1,f2=st.columns([5,1])
                    btn_label=f"{'📂' if st.session_state.get('folder_filter')==f['id'] else '📁'} {f['name']}"
                    if f1.button(btn_label,key=f"fld_{f['id']}",use_container_width=True): st.session_state["folder_filter"]=f["id"];st.rerun()
                    if f2.button("🗑️",key=f"df_{f['id']}"): delete_folder(f["id"]);st.rerun()
            if st.session_state.get("folder_filter"):
                if st.button("📂 전체 노트 보기",use_container_width=True): st.session_state.pop("folder_filter",None);st.rerun()

    if st.session_state.editing_note:
        note=st.session_state.editing_note
        all_notes=get_notes(uid) if DB else []
        new_title=st.text_input("Title",value=note.get("title",""),key="nt")
        type_map={"note":"📝 Note","meeting":"📋 Meeting","daily":"📅 Daily","idea":"💡 Idea","project":"📁 Project"}
        nt_sel=st.selectbox("Type",list(type_map.keys()),format_func=lambda x:type_map[x],
                            index=list(type_map.keys()).index(note.get("note_type","note")) if note.get("note_type","note") in type_map else 0,
                            key="nt_sel")
        builtin={"meeting":"## 📋 Meeting\n- Date: \n- Attendees: \n\n## Agenda\n1. \n\n## Discussion\n\n## Decisions\n\n## Action Items\n- [ ] \n\n## Next Steps\n- ",
                 "idea":"## 💡 Idea\n\n### Core Concept\n\n### Background\n\n### Expected Impact\n\n### Action Plan\n1. ",
                 "project":"## 📁 Project\n- Start: \n- Deadline: \n- Status: \n\n## Goals\n1. \n\n## Tasks\n- [ ] \n\n## Notes\n\n## Resources\n- ",
                 "daily":f"# {date.today().strftime('%Y-%m-%d %A')}\n\n## Notes\n\n\n## To Do\n- [ ] \n\n## Ideas\n\n"}
        if DB:
            all_tmps=get_templates(uid)
            note_tmps=[t for t in all_tmps if t.get("note_type") not in ["report_template","ai_prompt","pomo_prompt"]]
            if note_tmps:
                st.markdown("**📄 Templates:**")
                tc=st.columns(min(len(note_tmps)+1,5))
                for i,t in enumerate(note_tmps):
                    if tc[i].button(f"{t.get('icon','📄')} {t['name']}",key=f"tmp_{t['id']}"):
                        st.session_state["_tmpl"]=t["content"]; clear_nc(); st.rerun()

        default_content=st.session_state.pop("_tmpl",None)
        if default_content is None:
            default_content=builtin.get(nt_sel,"") if not note.get("content") else note.get("content","")
        content=st.text_area("",value=default_content,height=380,label_visibility="collapsed",key="nc")

        uploaded=st.file_uploader("📎 파일 첨부",type=["txt","md","docx","xlsx","csv","png","jpg","jpeg","pdf"],key="nf_upload")
        if uploaded:
            if uploaded.type.startswith("image"):
                st.image(uploaded)
                if st.button("🔍 OCR",key="ocr_btn"):
                    with st.spinner("Reading..."):
                        ocr_text=ocr_image(uploaded.read(),uploaded.type); st.markdown(ocr_text)
                        st.session_state["_tmpl"]=content+"\n\n---\n## Extracted\n"+ocr_text; clear_nc(); st.rerun()
            else:
                if st.button("📥 Import",key="import_btn"):
                    with st.spinner("Converting..."):
                        imported=file_to_markdown(uploaded); st.session_state["_tmpl"]=content+"\n\n---\n## Imported\n"+imported; clear_nc(); st.rerun()

        tag_input=st.text_input("🏷️ Tags",placeholder="#work, #project-a",key="ntags")

        # AI Tools - 버튼 먼저, 프롬프트 선택 아래
        st.markdown("**🤖 AI Tools:**")
        ac=st.columns(4)
        btn_sum=ac[0].button("🤖 Summary",use_container_width=True,help="📌 입력 내용만 기반으로 요약 (외부 정보 없음)")
        btn_rel=ac[1].button("🔗 Related",use_container_width=True,help="📌 연결 노트 패널 열기/닫기\n[[노트제목]] 자동 링크")
        btn_exp=ac[2].button("✨ Expand",use_container_width=True,help="📌 입력 내용만 기반으로 확장")
        btn_md=ac[3].button("📄→MD",use_container_width=True,help="📌 내용을 Markdown 형식으로 변환")

        # 프롬프트 선택 - 버튼 아래 한 줄
        ai_prompts_db=[]
        if DB:
            all_tmps_ai=get_templates(uid)
            ai_prompts_db=[t for t in all_tmps_ai if t.get("note_type")=="ai_prompt"]
        sum_prompts=["기본 요약 (3~5줄)"]+[t["name"] for t in ai_prompts_db if t.get("icon","")=="📝"]
        exp_prompts=["기본 확장"]+[t["name"] for t in ai_prompts_db if t.get("icon","")=="✨"]

        pc1,pc2,_,_=st.columns(4)
        sel_sum=pc1.selectbox("Summary 프롬프트",sum_prompts,key="sel_sum",label_visibility="visible")
        sel_exp=pc2.selectbox("Expand 프롬프트",exp_prompts,key="sel_exp",label_visibility="visible")

        # 버튼 액션 처리
        if btn_sum:
            if content:
                custom_p=None
                if sel_sum!="기본 요약 (3~5줄)":
                    m=[t for t in ai_prompts_db if t["name"]==sel_sum]
                    if m: custom_p=m[0]["content"]
                with st.spinner("..."):
                    result=summarize_note(content,custom_p)
                    st.session_state.ai_result=result; st.session_state.ai_result_type="summary"; st.rerun()
        if btn_rel:
            st.session_state.show_related=not st.session_state.get("show_related",False); st.rerun()
        if btn_exp:
            if content:
                custom_p=None
                if sel_exp!="기본 확장":
                    m=[t for t in ai_prompts_db if t["name"]==sel_exp]
                    if m: custom_p=m[0]["content"]
                with st.spinner("..."):
                    result=expand_note(content,custom_p)
                    st.session_state.ai_result=result; st.session_state.ai_result_type="expand"; st.rerun()
        if btn_md:
            if content:
                with st.spinner("..."):
                    result=get_ai(f"다음 내용을 깔끔한 마크다운으로 정리. 외부 정보 추가 없이 원본만 정리:\n\n{content}",st.session_state.ai_engine,"content")
                    st.session_state.ai_result=result; st.session_state.ai_result_type="md"; st.rerun()

        # AI 결과 + 반영 버튼
        if st.session_state.get("ai_result"):
            res=st.session_state.ai_result; rtype=st.session_state.ai_result_type
            type_labels={"summary":"📋 요약 결과","expand":"✨ 확장 결과","md":"📄 MD 변환 결과"}
            st.markdown(f"---\n#### {type_labels.get(rtype,'AI 결과')}")
            st.markdown(res)
            st.markdown("**노트에 반영:**")
            rb1,rb2,rb3,rb4=st.columns(4)
            if rb1.button("📌 맨 위에 추가",use_container_width=True,key="ai_top"):
                sep="\n\n---\n\n"
                new_c=f"## 📋 요약\n{res}{sep}{content}" if rtype=="summary" else f"{res}{sep}{content}"
                st.session_state["_tmpl"]=new_c; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb2.button("📎 맨 아래 추가",use_container_width=True,key="ai_bot"):
                new_c=f"{content}\n\n---\n\n{res}"
                st.session_state["_tmpl"]=new_c; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb3.button("🔄 원본 대체",use_container_width=True,key="ai_rep"):
                st.session_state["_tmpl"]=res; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb4.button("✖️ 무시",use_container_width=True,key="ai_ign"):
                st.session_state.ai_result=None; st.rerun()

        # Related Panel
        if st.session_state.get("show_related") and note.get("id") and note["id"]!="demo":
            st.markdown("---"); st.markdown("#### 🔗 Note Links")
            r_col1,r_col2=st.columns(2)
            with r_col1:
                st.markdown("**현재 연결된 노트:**")
                linked=get_linked_notes(note["id"]); linked_ids=[l["target_id"] for l in linked]
                linked_objs=[n for n in all_notes if n["id"] in linked_ids]
                if linked_objs:
                    for ln in linked_objs: st.markdown(f"📝 {ln['title']}")
                else: st.caption("연결된 노트 없음")
                st.info("💡 `[[노트제목]]` 입력 → 저장 시 자동 링크")
            with r_col2:
                st.markdown("**노트 검색 후 연결:**")
                link_search=st.text_input("제목 검색",key="link_search_input",placeholder="검색어...")
                if link_search:
                    matching=[n for n in all_notes if link_search.lower() in n["title"].lower() and n["id"]!=note.get("id")]
                    for mn in matching[:5]:
                        if st.button(f"🔗 {mn['title']}",key=f"link_{mn['id']}"): link_notes(note["id"],mn["id"]);st.success("연결!");st.rerun()
                if st.button("🤖 AI 추천",key="ai_related"):
                    if content and all_notes:
                        with st.spinner("..."):
                            suggested=suggest_related(content,all_notes)
                            if suggested:
                                st.markdown("**AI 추천:**")
                                for sid in suggested:
                                    m=[n for n in all_notes if n["id"]==sid]
                                    if m: st.markdown(f"- 📝 {m[0]['title']}")

        st.markdown("---")
        sc=st.columns([2,1,1,1])
        if sc[0].button("💾 Save",type="primary",use_container_width=True):
            if DB and note.get("id")!="demo":
                update_note(note["id"],title=new_title,content=content,note_type=nt_sel)
                if tag_input:
                    for tn_t in [t.strip().replace("#","") for t in tag_input.split(",") if t.strip()]:
                        tg=add_tag(uid,tn_t)
                        if tg: tag_note(note["id"],tg["id"])
                found_links=re.findall(r'\[\[(.+?)\]\]',content)
                for fl in found_links:
                    matches=[n for n in all_notes if n["title"].lower()==fl.lower() and n["id"]!=note["id"]]
                    if matches: link_notes(note["id"],matches[0]["id"])
                st.success("✅ Saved!")
        if sc[1].button("Close",use_container_width=True):
            st.session_state.editing_note=None;st.session_state.show_related=False
            st.session_state.ai_result=None;clear_nc();st.rerun()
        if sc[2].button("🗑️ Del",use_container_width=True):
            if DB: delete_note(note["id"])
            st.session_state.editing_note=None;clear_nc();st.rerun()
        if sc[3].button("📥 Export",use_container_width=True):
            st.download_button("⬇️ .md",f"# {new_title}\n\n{content}",file_name=f"{new_title}.md",mime="text/markdown")
    else:
        if DB:
            fid=st.session_state.get("folder_filter")
            notes=get_notes(uid,search=sq or None,folder_id=fid)
            if sort_notes=="이름순": notes=sorted(notes,key=lambda x:x.get("title",""))
            elif sort_notes=="업데이트순": notes=sorted(notes,key=lambda x:x.get("updated_at",""),reverse=True)
            else: notes=sorted(notes,key=lambda x:x.get("created_at",""),reverse=True)
            for n in notes:
                icon={"meeting":"📋","daily":"📅","idea":"💡","project":"📁"}.get(n.get("note_type"),"📝")
                fav="⭐" if n.get("is_favorite") else ""
                cn,ca=st.columns([5,1])
                cn.markdown(f"{fav}{icon} **{n['title']}** · _{n.get('updated_at','')[:10]}_")
                if ca.button("Open",key=f"o_{n['id']}"): st.session_state.editing_note=n;st.session_state.show_related=False;st.session_state.ai_result=None;clear_nc();st.rerun()
            if not notes: st.info("노트가 없습니다. ➕ New를 눌러 추가하세요.")
        st.markdown("---")
        if st.checkbox("🕸️ Note Graph"):
            if DB:
                all_n=get_notes(uid); all_l=get_all_links(uid); nmap={n["id"]:n["title"] for n in all_n}
                if all_l:
                    for l in all_l: st.markdown(f"📝 {nmap.get(l['source_id'],'?')} ↔️ 📝 {nmap.get(l['target_id'],'?')}")
                else: st.info("연결된 노트 없음")
        if st.checkbox("📦 Backup"):
            if DB:
                md=export_all_notes_md(uid)
                st.download_button("📥 모든 노트 다운로드",md,"all_notes_backup.md","text/markdown")
        if st.checkbox("📊 Folder Summary (AI)"):
            period=st.selectbox("Period",["This week","This month","Last 7 days","Last 30 days"])
            if st.button("Generate",key="folder_sum"):
                if DB:
                    with st.spinner("..."):
                        if "week" in period.lower(): start=date.today()-timedelta(days=date.today().weekday())
                        elif "month" in period.lower(): start=date.today().replace(day=1)
                        elif "7" in period: start=date.today()-timedelta(7)
                        else: start=date.today()-timedelta(30)
                        period_notes=[n for n in get_notes(uid) if n.get("updated_at","")[:10]>=str(start)]
                        st.markdown(folder_summary(period_notes,period))

# ===== TRANSCRIPTION =====
elif page=="🎙️ Transcription":
    st.markdown("## 🎙️ Transcription")
    tab1,tab2=st.tabs(["🎙️ Transcribe","📖 Dictionary"])
    with tab1:
        audio=st.file_uploader("Upload audio",type=["mp3","wav","m4a","ogg","webm"])
        if audio:
            st.audio(audio)
            if st.button("🎙️ Transcribe",type="primary"):
                with st.spinner("..."): t=transcribe(audio);t=apply_terms(uid,t) if DB else t;st.session_state.transcript=t
        st.markdown("---")
        manual=st.text_area("Or paste transcript here",height=200,key="mt")
        if manual:
            corrected=apply_terms(uid,manual) if DB else manual
            if corrected!=manual: st.info("✅ 용어 자동 교정됨")
            st.session_state.transcript=corrected or manual
        if st.session_state.get("transcript"):
            st.text_area("Transcript",value=st.session_state.transcript,height=200,key="tv",disabled=True)
            save_type=st.selectbox("Format",["📋 Meeting Notes","📊 Summary Only","✅ Action Items Only","📝 Raw Note"])
            if st.button("💾 Process & Save",type="primary"):
                with st.spinner("Processing..."):
                    result=""
                    if "Meeting" in save_type: result=summarize_meeting(st.session_state.transcript)
                    elif "Summary" in save_type: result=get_ai(f"5줄 핵심 요약:\n\n{st.session_state.transcript}",st.session_state.ai_engine,"summary")
                    elif "Action" in save_type: result=get_ai(f"액션아이템 체크박스로:\n\n{st.session_state.transcript}",st.session_state.ai_engine,"analysis")
                    else: result=st.session_state.transcript
                    if DB: create_note(uid,f"{'📋 Meeting' if 'Meeting' in save_type else 'Summary' if 'Summary' in save_type else 'Actions' if 'Action' in save_type else 'Transcript'} {date.today()}",result,"meeting" if "Meeting" in save_type else "note");st.success("Saved!")
                    if result and "Raw" not in save_type: st.markdown(result)
    with tab2:
        tc1,tc2=st.columns(2)
        w_term=tc1.text_input("Wrong",placeholder="케이피아이");c_term=tc2.text_input("Correct",placeholder="KPI")
        if st.button("Add",type="primary",key="at2"):
            if w_term and c_term and DB: add_term(uid,w_term,c_term);st.success(f"'{w_term}'→'{c_term}'");st.rerun()
        if DB:
            for w,c in get_terms(uid).items(): st.markdown(f"~~{w}~~ → **{c}**")

# ===== AI CONTENT =====
elif page=="✨ AI Content":
    st.markdown("## ✨ AI Content")
    ct=st.selectbox("Type",["Blog","Instagram","Twitter Thread","Full Package"])
    topic=st.text_area("📌 Topic",placeholder="e.g. 5 ways AI boosts productivity")
    kw=st.text_input("🔑 Keywords")
    img=st.file_uploader("📷 Image (optional)",type=["png","jpg","jpeg"],key="ci")
    eng=st.radio("Engine",["Auto","Gemini","Claude"],horizontal=True)
    if st.button("✨ Generate",type="primary",use_container_width=True):
        if topic:
            with st.spinner("Generating..."):
                result=""
                if img: result=analyze_image_for_content(img.read(),img.type,ct);st.markdown(result)
                else:
                    em={"Auto":"auto","Gemini":"gemini","Claude":"claude"}
                    prompts={"Blog":f"주제:{topic}\n키워드:{kw}\n\n블로그: 제목3개, SEO메타, 본문1500-2000자, 해시태그10개",
                             "Instagram":f"주제:{topic}\n키워드:{kw}\n\n인스타: 훅, 본문2000자이내, 해시태그30개",
                             "Twitter Thread":f"주제:{topic}\n키워드:{kw}\n\n트위터 5-8개, 각280자"}
                    if ct=="Full Package":
                        for t_name in ["Blog","Instagram","Twitter Thread"]:
                            st.markdown(f"### {t_name}"); part=get_ai(prompts[t_name],em[eng],"content"); st.markdown(part); result+=f"\n\n## {t_name}\n"+part; st.markdown("---")
                    else: result=get_ai(prompts[ct],em[eng],"content"); st.markdown(result)
                if result:
                    sc1,sc2=st.columns(2)
                    if sc1.button("📝 Save to Notes",key="sc_note"):
                        if DB: create_note(uid,f"[Content] {topic[:30]}",result,"note");st.success("Saved!")
                    sc2.download_button("📥 Download",result,f"content_{ct}.txt","text/plain")

# ===== ECONOMY =====
elif page=="💹 Economy":
    st.markdown("## 💹 Economy")
    tabs=st.tabs(["📊 Dashboard","💰 Finance","📈 Market","🤖 Analysis"])
    with tabs[0]:
        if DB:
            cm=datetime.now().strftime("%Y-%m"); exps=get_expenses(uid,cm); inc=get_income(uid,cm); loans=get_loans(uid)
            te=sum(e.get("amount",0) for e in exps); ti=sum(i.get("amount",0) for i in inc); tl=sum(l.get("remaining_amount",0) for l in loans)
            c1,c2,c3,c4=st.columns(4)
            c1.metric("💵 Income",f"{ti:,}₩");c2.metric("💸 Expenses",f"{te:,}₩");c3.metric("💰 Balance",f"{ti-te:,}₩");c4.metric("🏦 Debt",f"{tl:,}₩")
            if exps:
                cats={}
                for e in exps: cats[e.get("category","기타")]=cats.get(e.get("category","기타"),0)+e.get("amount",0)
                for cat,amt in sorted(cats.items(),key=lambda x:-x[1]):
                    st.progress(min(amt/te,1) if te>0 else 0,text=f"{cat}: {amt:,}₩")
    with tabs[1]:
        sub=st.radio("",["Expenses","Income","Loans","Upload"],horizontal=True,label_visibility="collapsed")
        if sub=="Expenses":
            fc1,fc2,fc3=st.columns(3)
            ea=fc1.number_input("₩",min_value=0,step=1000,key="ea"); ecat=fc2.selectbox("Cat",["식비","교통비","쇼핑","생활비","의료","교육","여가","카페","구독","기타"]); edt=fc3.date_input("",key="edt",label_visibility="collapsed")
            edsc=st.text_input("Memo",key="edsc")
            if st.button("Record",type="primary",key="re"):
                if ea>0 and DB: add_expense(uid,ea,ecat,edsc,edt);st.success("✅");st.rerun()
            if DB:
                for e in get_expenses(uid,datetime.now().strftime("%Y-%m"))[:20]: st.markdown(f"- {e.get('expense_date','')} | {e.get('category','')} | {e.get('amount',0):,}₩")
        elif sub=="Income":
            ic1,ic2=st.columns(2); ia=ic1.number_input("₩",min_value=0,step=100000,key="ia"); isrc=ic2.text_input("Source",key="isrc")
            if st.button("Record",type="primary",key="ri"):
                if ia>0 and DB: add_income(uid,ia,isrc);st.success("✅");st.rerun()
            if DB:
                for i in get_income(uid,datetime.now().strftime("%Y-%m")): st.markdown(f"- {i.get('income_date','')} | {i.get('source','')} | {i.get('amount',0):,}₩")
        elif sub=="Loans":
            lc1,lc2=st.columns(2); ln=lc1.text_input("Name"); lt=lc2.number_input("Total₩",min_value=0,step=1000000,key="lt")
            lr=lc1.number_input("Remaining₩",min_value=0,step=1000000,key="lr"); li=lc2.number_input("Rate%",min_value=0.0,step=0.1,key="li")
            if st.button("Add",type="primary",key="al"):
                if ln and DB: add_loan(uid,ln,lt,lr,li);st.success("✅");st.rerun()
            if DB:
                for l in get_loans(uid):
                    pct=(1-l.get("remaining_amount",0)/max(l.get("total_amount",1),1))*100
                    st.progress(pct/100,text=f"{l['name']}: {l.get('remaining_amount',0):,}₩")
        elif sub=="Upload":
            uploaded=st.file_uploader("Excel/CSV/Text",type=["csv","xlsx","txt"],key="eu"); text_in=st.text_area("Or paste data",height=100,key="eti")
            if st.button("🤖 AI Import",type="primary"):
                data=""
                if uploaded:
                    if uploaded.name.endswith(".csv"):
                        import pandas as pd; data=pd.read_csv(uploaded).to_string()
                    elif uploaded.name.endswith(".xlsx"):
                        import pandas as pd; data=pd.read_excel(uploaded).to_string()
                    else: data=uploaded.read().decode("utf-8")
                elif text_in: data=text_in
                if data:
                    with st.spinner("..."):
                        items=classify_expenses(data)
                        if items:
                            for c in items: st.markdown(f"- {c.get('date','')} | {c.get('category','')} | {c.get('amount',0):,}₩")
                            if st.button("✅ Import All",key="imp"):
                                if DB: bulk_add_expenses(uid,items);st.success(f"{len(items)} imported!")
    with tabs[2]:
        if st.button("🔄 Latest Market Info",type="primary"):
            with st.spinner("..."): st.markdown(get_ai("US(S&P500,NASDAQ,DOW)+KR(KOSPI,KOSDAQ)+환율(USD/KRW,EUR/KRW,JPY/KRW)+경제뉴스5개. 간결하게.",st.session_state.ai_engine,"analysis"))
        st.markdown("---"); st.markdown("### ⭐ Watchlist")
        wc1,wc2,wc3=st.columns([2,2,1])
        ws_sym=wc1.text_input("Symbol",key="ws"); wn_name=wc2.text_input("Name",key="wn"); wm=wc3.selectbox("",["US","KR"],key="wm",label_visibility="collapsed")
        if st.button("Add",key="aw"):
            if ws_sym and wn_name and DB: add_watch(uid,ws_sym,wn_name,wm);st.rerun()
        if DB:
            for w in get_watchlist(uid):
                c1,c2=st.columns([5,1]); c1.markdown(f"{'🇺🇸' if w.get('market')=='US' else '🇰🇷'} **{w['name']}** ({w['symbol']})")
                if c2.button("🗑️",key=f"dw_{w['id']}"): del_watch(w["id"]);st.rerun()
    with tabs[3]:
        if st.button("🤖 Full Analysis",type="primary"):
            if DB:
                cm=datetime.now().strftime("%Y-%m")
                with st.spinner("..."): st.markdown(analyze_finances(get_expenses(uid,cm),get_income(uid,cm),get_loans(uid)))

# ===== EMAIL =====
elif page=="📧 Email":
    st.markdown("## 📧 Email")
    to=st.text_input("To"); subj=st.text_input("Subject"); body=st.text_area("Body",height=200)
    with st.expander("⚙️ Gmail Settings"):
        ga=st.text_input("Gmail",key="ga"); gp=st.text_input("App Password",type="password",key="gp")
    if st.button("📨 Send",type="primary"):
        if all([to,subj,body,ga,gp]):
            ok,msg=send_gmail(to,subj,body,ga,gp)
            st.success(msg) if ok else st.error(msg)

# ===== WEB CLIPPER =====
elif page=="🔗 Web Clipper":
    st.markdown("## 🔗 Web Clipper")
    url=st.text_input("URL",placeholder="https://...")
    if st.button("📥 Clip & Summarize",type="primary"):
        if url:
            with st.spinner("..."):
                s=web_summary(url); st.markdown(s)
                if DB: create_note(uid,f"🔗 {url[:50]}",f"URL: {url}\n\n---\n{s}","note");st.success("Saved!")
    if DB:
        clips=[n for n in get_notes(uid) if n.get("content","").startswith("URL:")]
        if clips:
            st.markdown("### 📚 Saved Clips")
            for c in clips[:10]: st.markdown(f"🔗 **{c['title']}** · _{c.get('updated_at','')[:10]}_")

# ===== POMODORO =====
elif page=="🍅 Pomodoro":
    st.markdown("## 🍅 Pomodoro Timer")
    pc1,pc2,pc3=st.columns(3)
    focus_min=pc1.number_input("집중 (분)",min_value=1,max_value=90,value=25,step=5,key="focus_min")
    break_min=pc2.number_input("휴식 (분)",min_value=1,max_value=30,value=5,step=1,key="break_min")
    tn_work=pc3.text_input("작업 내용:",key="pt",placeholder="기획서 작성...")

    timer_html=f"""
<style>
.pc{{text-align:center;padding:1.2rem;font-family:-apple-system,sans-serif}}
.td{{font-size:5rem;font-weight:800;color:#ef4444;font-family:'Courier New',monospace;letter-spacing:4px;margin:0.5rem 0}}
.td.brk{{color:#22c55e}}.ts{{font-size:1rem;color:#666;margin-bottom:0.8rem;min-height:1.4rem}}
.prog{{width:75%;max-width:380px;height:8px;background:#e5e7eb;border-radius:4px;margin:0 auto 1rem;overflow:hidden}}
.pb{{height:100%;background:linear-gradient(90deg,#ef4444,#f97316);border-radius:4px;transition:width 1s linear}}
.pb.brk{{background:linear-gradient(90deg,#22c55e,#14b8a6)}}
.br{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}}
.btn{{padding:0.6rem 1.4rem;font-size:0.9rem;border-radius:8px;border:none;cursor:pointer;font-weight:600}}
.bs{{background:#ef4444;color:#fff}}.bb{{background:#22c55e;color:#fff}}.br2{{background:#6b7280;color:#fff}}
.sc{{font-size:0.85rem;color:#888;margin-top:0.7rem}}
</style>
<div class="pc">
<div class="td" id="td">{focus_min:02d}:00</div>
<div class="ts" id="ts">집중할 준비가 되셨나요? 🍅</div>
<div class="prog"><div class="pb" id="pb" style="width:100%"></div></div>
<div class="br">
<button class="btn bs" id="sb" onclick="toggle()">▶️ 시작</button>
<button class="btn bb" onclick="startBreak()">☕ 휴식</button>
<button class="btn br2" onclick="reset()">🔄 리셋</button>
</div>
<div class="sc" id="sc">오늘 완료: 0 🍅</div>
</div>
<script>
const F={focus_min}*60,B={break_min}*60;
let left=F,total=F,run=false,brk=false,iv=null,sess=0;
function fmt(t){{return String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0')}}
function ui(){{document.getElementById('td').textContent=fmt(left);document.getElementById('td').className='td'+(brk?' brk':'');document.getElementById('pb').style.width=(left/total*100)+'%';document.getElementById('pb').className='pb'+(brk?' brk':'')}}
function beep(){{try{{const a=new AudioContext(),o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.type='sine';o.frequency.setValueAtTime(880,a.currentTime);o.frequency.setValueAtTime(660,a.currentTime+0.2);o.frequency.setValueAtTime(880,a.currentTime+0.4);g.gain.setValueAtTime(0.3,a.currentTime);g.gain.exponentialRampToValueAtTime(0.01,a.currentTime+0.7);o.start();o.stop(a.currentTime+0.7)}}catch(e){{}}}}
function toggle(){{if(run){{clearInterval(iv);run=false;document.getElementById('sb').textContent='▶️ 재개';document.getElementById('ts').textContent='⏸️ 일시정지'}}else{{run=true;document.getElementById('sb').textContent='⏸️ 일시정지';document.getElementById('ts').textContent=brk?'☕ 휴식 중...':'🍅 집중 중!';iv=setInterval(()=>{{if(left>0){{left--;ui()}}else{{clearInterval(iv);run=false;document.getElementById('sb').textContent='▶️ 시작';if(!brk){{sess++;document.getElementById('sc').textContent='오늘 완료: '+sess+' 🍅';document.getElementById('ts').textContent='✅ 완료! 아래 버튼으로 기록하세요 👇';beep()}}else{{document.getElementById('ts').textContent='💪 휴식 완료! 다시 집중해봐요';brk=false;left=F;total=F;ui()}}}}}}),1000)}}}}
function startBreak(){{clearInterval(iv);run=false;brk=true;left=B;total=B;document.getElementById('sb').textContent='▶️ 시작';document.getElementById('ts').textContent='☕ 휴식 준비';ui()}}
function reset(){{clearInterval(iv);run=false;brk=false;left=F;total=F;document.getElementById('sb').textContent='▶️ 시작';document.getElementById('ts').textContent='집중할 준비가 되셨나요? 🍅';ui()}}
</script>"""
    components.html(timer_html,height=300)
    st.markdown("---")
    col_r1,col_r2,col_r3=st.columns(3)
    interruptions=col_r2.number_input("방해받은 횟수",min_value=0,max_value=20,value=0,key="pomo_int")
    is_complete=col_r3.checkbox("완주 여부",value=True,key="pomo_complete")
    if col_r1.button("✅ 세션 기록",type="primary",use_container_width=True):
        if DB:
            status="complete" if is_complete else "interrupted"
            log_pomo(uid,focus_min,tn_work,status=status,interruptions=interruptions)
            st.success(f"🍅 기록됨! ({'완주' if is_complete else '중단'})")
            if is_complete: st.balloons()
    if DB:
        logs=get_pomo_logs(uid,7)
        if logs:
            st.markdown("---")
            col_s1,col_s2,col_s3=st.columns(3)
            complete_logs=[l for l in logs if l.get("status","complete")=="complete"]
            col_s1.metric("완료 세션",f"{len(complete_logs)} 🍅")
            col_s2.metric("총 집중",f"{sum(l.get('duration_minutes',25) for l in complete_logs)}분")
            col_s3.metric("완주율",f"{int(len(complete_logs)/len(logs)*100) if logs else 0}%")
            with st.expander("📋 최근 기록"):
                for l in logs[:10]:
                    s_icon="✅" if l.get("status","complete")=="complete" else "⚠️"
                    intr=l.get("interruptions",0)
                    st.markdown(f"{s_icon} {l.get('task_name','(미입력)')} — {l.get('completed_at','')[:10]} ({l.get('duration_minutes',25)}분{', 방해'+str(intr)+'회' if intr else ''})")
            st.markdown("### 🤖 AI Insight")
            pomo_prompts_db=[]
            if DB:
                all_tmps_p=get_templates(uid)
                pomo_prompts_db=[t for t in all_tmps_p if t.get("note_type")=="pomo_prompt"]
            pomo_prompt_opts=["기본 뽀모도로 분석"]+[t["name"] for t in pomo_prompts_db]
            sel_pomo_prompt=st.selectbox("분석 프롬프트",pomo_prompt_opts,key="sel_pomo_p")
            if st.button("🤖 Insight 분석",type="primary",use_container_width=True):
                custom_pp=None
                if sel_pomo_prompt!="기본 뽀모도로 분석":
                    m=[t for t in pomo_prompts_db if t["name"]==sel_pomo_prompt]
                    if m: custom_pp=m[0]["content"]
                with st.spinner("분석 중..."):
                    insight=pomodoro_insight(logs,custom_pp); st.markdown(insight)
                    if st.button("📝 노트에 저장",key="pomo_note"):
                        if DB: create_note(uid,f"🍅 Pomodoro Insight {date.today()}",insight,"note");st.success("Saved!")

# ===== WEEKLY REPORT =====
elif page=="📊 Weekly Report":
    st.markdown("## 📊 Weekly Report")
    col_d1,col_d2=st.columns(2)
    use_preset=col_d1.selectbox("기간",["이번 주","지난 7일","지난 14일","이번 달","사용자 지정"])
    if use_preset=="이번 주": start=date.today()-timedelta(days=date.today().weekday());end=date.today()
    elif use_preset=="지난 7일": start=date.today()-timedelta(7);end=date.today()
    elif use_preset=="지난 14일": start=date.today()-timedelta(14);end=date.today()
    elif use_preset=="이번 달": start=date.today().replace(day=1);end=date.today()
    else:
        start=col_d1.date_input("시작일",value=date.today()-timedelta(7))
        end=col_d2.date_input("종료일",value=date.today())
    col_d2.info(f"**기간:** {start} ~ {end}")
    DEFAULT_FORMAT="형식:\n## 📊 주간 업무 보고\n### 1. 핵심 성과\n### 2. 진행 중 업무\n### 3. 회의 요약\n### 4. 이슈/리스크\n### 5. 다음 주 계획\n### 6. 건의사항"
    if DB:
        all_tmps=get_templates(uid); report_tmps=[t for t in all_tmps if t.get("note_type")=="report_template"]
        tmpl_names=["📋 기본 템플릿"]+[f"📊 {t['name']}" for t in report_tmps]
        sel_tmpl=st.selectbox("템플릿",tmpl_names)
        if sel_tmpl=="📋 기본 템플릿": prompt_val=DEFAULT_FORMAT
        else:
            t_name=sel_tmpl.replace("📊 ",""); tmpl_obj=next((t for t in report_tmps if t["name"]==t_name),None)
            prompt_val=tmpl_obj["content"] if tmpl_obj else DEFAULT_FORMAT
        custom_prompt=st.text_area("리포트 형식",value=prompt_val,height=200)
        with st.expander("💾 새 템플릿으로 저장"):
            new_t_name=st.text_input("이름",placeholder="예: 영업팀 주간보고")
            if st.button("저장",key="save_rpt"):
                if new_t_name: create_template(uid,new_t_name,custom_prompt,note_type="report_template",icon="📊");st.success("저장됨!");st.rerun()
    else: custom_prompt=DEFAULT_FORMAT
    if st.button("📊 보고서 생성",type="primary",use_container_width=True):
        if DB:
            with st.spinner("Generating..."):
                notes=[n for n in get_notes(uid) if n.get("updated_at","")[:10]>=str(start)]
                tasks=get_tasks(uid); exps=get_expenses(uid,datetime.now().strftime("%Y-%m"))
                report=weekly_report(notes,tasks,exps,custom_format=custom_prompt)
                st.markdown(report)
                sc1,sc2=st.columns(2)
                if sc1.button("📝 저장",key="sr"): create_note(uid,f"📊 Report {start}~{end}",report,"note");st.success("Saved!")
                sc2.download_button("📥 Download",report,f"report_{start}_{end}.md","text/markdown")

# ===== SEARCH =====
elif page=="🔍 Search":
    st.markdown("## 🔍 Smart Search")
    kw=st.text_input("",placeholder="노트, 태스크, 일정 통합 검색...",label_visibility="collapsed")
    if kw and DB:
        results=search_all(uid,kw)
        if results:
            st.markdown(f"**{len(results)}개 결과:**")
            for r in results:
                icon={"note":"📝","task":"✅","event":"📅"}.get(r["type"],"📄")
                st.markdown(f"{icon} **{r['title']}** · {r['type']} · {r.get('date','')}")
        else: st.info("결과 없음")

# ===== SETTINGS =====
elif page=="⚙️ Settings":
    st.markdown("## ⚙️ Settings")
    tabs_s=st.tabs(["👤 Profile","🔑 API Keys","🤖 AI Engine","🎯 목표&습관","📅 Labels","📄 Templates","🤖 AI 프롬프트","📊 Stats"])
    with tabs_s[0]:
        st.markdown("### 👤 Profile")
        nn=st.text_input("Display Name",value=dname,key="sn")
        if st.button("Update Name"):
            if DB: update_profile(uid,display_name=nn);st.session_state.user["display_name"]=nn;st.success("Updated!");st.rerun()
        st.markdown("---"); st.markdown("### 🔑 비밀번호 변경")
        cur_pw=st.text_input("현재 비밀번호",type="password",key="cur_pw")
        new_pw=st.text_input("새 비밀번호",type="password",key="new_pw")
        new_pw2=st.text_input("확인",type="password",key="new_pw2")
        if st.button("비밀번호 변경",key="chg_pw"):
            if new_pw!=new_pw2: st.error("새 비밀번호 불일치")
            elif not cur_pw: st.error("현재 비밀번호 입력")
            elif DB:
                import hashlib
                u,err=login_user(user.get("email",""),cur_pw)
                if u: update_profile(uid,password_hash=hashlib.sha256(new_pw.encode()).hexdigest());st.success("✅ 변경됨!")
                else: st.error("현재 비밀번호 틀림")
    with tabs_s[1]:
        st.markdown("### 🔑 API Keys")
        gk=st.text_input("Gemini API Key",value=st.session_state.gemini_api_key,type="password",key="sgk")
        ck=st.text_input("Claude API Key (선택)",value=st.session_state.claude_api_key,type="password",key="sck")
        if st.button("Save Keys",type="primary"):
            st.session_state.gemini_api_key=gk;st.session_state.claude_api_key=ck;st.success("저장됨")
        st.info("💡 영구 저장: Streamlit Secrets에 GEMINI_API_KEY 추가")
    with tabs_s[2]:
        st.session_state.ai_engine=st.radio("Engine",["auto","gemini","claude"],format_func=lambda x:{"auto":"🔄 Auto","gemini":"⚡ Gemini","claude":"🧠 Claude"}[x],horizontal=True)
        from ai_engine import GEMINI_MODELS,DEFAULT_MODEL
        current_model=st.session_state.get("gemini_model",DEFAULT_MODEL); model_keys=list(GEMINI_MODELS.keys())
        selected=st.selectbox("Gemini Model",model_keys,format_func=lambda x:GEMINI_MODELS[x],index=model_keys.index(current_model) if current_model in model_keys else 0)
        st.session_state.gemini_model=selected
        st.caption("⚡ Flash = 빠르고 무료 | 🧠 Pro = 더 스마트 (일 50회)")
    with tabs_s[3]:
        st.markdown("### 🎯 목표 & 습관")
        st.caption("✅ 체크형: 했냐/안했냐 | 📊 수치형: 목표값 달성률 + 완료 체크")
        hc1,hc2,hc3=st.columns([2,1,1])
        hn=hc1.text_input("이름"); hi=hc2.text_input("아이콘",value="✅",key="hi")
        htype=hc3.selectbox("타입",["check","numeric"],format_func=lambda x:{"check":"✅ 체크형","numeric":"📊 수치형"}[x],key="htype")
        htarget=1.0; hunit=""
        if htype=="numeric":
            hc4,hc5=st.columns(2)
            htarget=hc4.number_input("목표값",min_value=0.1,value=1.0,step=0.5,key="htarget")
            hunit=hc5.text_input("단위",placeholder="km, 잔, 분...",key="hunit")
        if st.button("추가",key="ah"):
            if hn and DB: create_habit_v2(uid,hn,hi,htype,htarget,hunit);st.rerun()
        if DB:
            for h in get_habits(uid):
                c1,c2,c3=st.columns([4,2,1])
                c1.markdown(f"{h.get('icon','✅')} {h['name']}")
                if h.get("habit_type")=="numeric": c2.caption(f"목표: {h.get('target_value',1)}{h.get('unit','')}")
                if c3.button("🗑️",key=f"dh_{h['id']}"): delete_habit(h["id"]);st.rerun()
    with tabs_s[4]:
        st.markdown("### 📅 Calendar Labels")
        if DB:
            custom_labels=get_color_labels(uid)
            for color_key,hex_val in COLOR_PRESETS.items():
                current_label=custom_labels.get(color_key,{}).get("label",color_key.capitalize())
                ca,cb,cc=st.columns([1,3,1])
                ca.markdown(f'<div style="width:22px;height:22px;background:{hex_val};border-radius:50%;margin-top:8px"></div>',unsafe_allow_html=True)
                new_label=cb.text_input(f"label_{color_key}",value=current_label,key=f"lbl_{color_key}",label_visibility="collapsed")
                if cc.button("저장",key=f"slbl_{color_key}"): set_color_label(uid,color_key,new_label,hex_val);st.success("저장됨");st.rerun()
    with tabs_s[5]:
        st.markdown("### 📄 Note Templates")
        tn_t=st.text_input("이름",key="tn"); ti_t=st.text_input("아이콘",value="📄",key="ti"); tc_t=st.text_area("내용",height=150,key="tc")
        if st.button("Save",key="st_btn"):
            if tn_t and tc_t and DB: create_template(uid,tn_t,tc_t,icon=ti_t);st.success("Saved!");st.rerun()
        if DB:
            for t in get_templates(uid):
                if t.get("note_type") not in ["report_template","ai_prompt","pomo_prompt"]:
                    c1,c2=st.columns([5,1]); c1.markdown(f"{t.get('icon','📄')} {t['name']}")
                    if c2.button("🗑️",key=f"dt_{t['id']}"): delete_template(t["id"]);st.rerun()
    with tabs_s[6]:
        st.markdown("### 🤖 AI 커스텀 프롬프트")
        st.caption("노트 Summary/Expand 및 Pomodoro 분석 시 선택 가능한 커스텀 프롬프트입니다.")
        pt_cat=st.selectbox("카테고리",["📝 Summary용","✨ Expand용","🍅 Pomodoro 분석용"],key="pt_cat")
        pt_name=st.text_input("이름",key="pt_name"); pt_content=st.text_area("프롬프트 내용",height=120,key="pt_content")
        cat_map={"📝 Summary용":("ai_prompt","📝"),"✨ Expand용":("ai_prompt","✨"),"🍅 Pomodoro 분석용":("pomo_prompt","🍅")}
        if st.button("저장",key="save_ai_p"):
            if pt_name and pt_content and DB:
                nt_type,icon=cat_map[pt_cat]
                create_template(uid,pt_name,pt_content,note_type=nt_type,icon=icon);st.success("저장됨!");st.rerun()
        if DB:
            for t in get_templates(uid):
                if t.get("note_type") in ["ai_prompt","pomo_prompt"]:
                    c1,c2=st.columns([5,1]); c1.markdown(f"{t.get('icon','🤖')} {t['name']}")
                    if c2.button("🗑️",key=f"dap_{t['id']}"): delete_template(t["id"]);st.rerun()
    with tabs_s[7]:
        st.markdown("### 📊 Stats")
        if DB:
            c1,c2,c3=st.columns(3)
            c1.metric("Notes",len(get_notes(uid)));c2.metric("Tasks",len(get_tasks(uid)));c3.metric("DB","✅")
            st.info("💡 다른 이메일로 가입하면 완전히 독립된 계정으로 사용 가능합니다.")

st.markdown("---")
st.caption(f"🚀 {dname}'s Personal Assistant v4.2")
