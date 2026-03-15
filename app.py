import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta, timezone
import json, calendar, math, re

st.set_page_config(page_title="Personal Assistant", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

KST = timezone(timedelta(hours=9))
def now_kst(): return datetime.now(KST)
def today_kst(): return now_kst().date()

def get_default_event_time():
    now = now_kst()
    next_15 = math.ceil((now.minute + 1) / 15) * 15
    if next_15 >= 60:
        return now.replace(hour=(now.hour+1)%24, minute=0, second=0, microsecond=0).time()
    return now.replace(minute=next_15, second=0, microsecond=0).time()

defs = {
    "logged_in":False,"user":None,"current_page":"🏠 Dashboard","prev_page":"🏠 Dashboard",
    "gemini_api_key":"","claude_api_key":"","ai_engine":"auto",
    "editing_note":None,"editing_task":None,"theme":"light",
    "transcript":"","gemini_model":"gemini-2.5-flash",
    "show_related":False,"qc_preview":None,"qc_text":"",
    "temp_note_save":None,"temp_task_save":None,
    "ai_result":None,"ai_result_type":None,
    "time_reset_key":0,"cal_prefill_date":None,
    "md_preview_mode":False,"delete_confirm":None,
    "gcal_synced_at":None,
    "dash_widget_order":["reminders","habits","pinned","recent","tasks"],
    "dash_widgets":{"habits":True,"pinned":True,"recent":True,"tasks":True,"reminders":True},
}
for k,v in defs.items():
    if k not in st.session_state: st.session_state[k]=v

try:
    from db_utils import *
    from ai_engine import *
    DB=True
except: DB=False

try:
    from google_calendar_helper import *
    GCAL=True
except: GCAL=False

# ===== iPhone Safari: LocalStorage 기반 로그인 유지 =====
# JS로 localStorage에서 uid를 읽어 query_params에 전달
ls_html = """
<script>
(function(){
  var uid = localStorage.getItem('pa_uid');
  if(uid){
    var params = new URLSearchParams(window.location.search);
    if(!params.get('uid')){
      params.set('uid', uid);
      var newUrl = window.location.pathname + '?' + params.toString();
      window.history.replaceState({}, '', newUrl);
      window.location.reload();
    }
  }
  // Listen for uid stored event
  window.addEventListener('message', function(e){
    if(e.data && e.data.type === 'store_uid'){
      localStorage.setItem('pa_uid', e.data.uid);
    } else if(e.data && e.data.type === 'clear_uid'){
      localStorage.removeItem('pa_uid');
    }
  });
})();
</script>
"""
components.html(ls_html, height=0)

# ===== 로그인 유지 (query_params) =====
if not st.session_state.logged_in and DB:
    uid_param = st.query_params.get("uid","")
    if uid_param:
        restored = get_user_by_id(uid_param)
        if restored:
            st.session_state.logged_in=True
            st.session_state.user=restored

# ===== Google OAuth 코드 처리 =====
oauth_code = st.query_params.get("code","")
if oauth_code and GCAL and DB:
    if not st.session_state.get("gcal_code_processed"):
        # uid를 session_state 또는 별도 저장에서 가져옴
        _oauth_uid = None
        if st.session_state.logged_in and st.session_state.get("user"):
            _oauth_uid = st.session_state.user["id"]
        elif st.session_state.get("pre_oauth_uid"):
            _oauth_uid = st.session_state["pre_oauth_uid"]
            # uid로 로그인 복원
            restored = get_user_by_id(_oauth_uid)
            if restored:
                st.session_state.logged_in = True
                st.session_state.user = restored
        if _oauth_uid:
            token_data = exchange_code_for_token(oauth_code)
            if token_data:
                expiry = (now_kst() + timedelta(seconds=token_data.get("expires_in",3600))).isoformat()
                save_google_tokens(
                    _oauth_uid,
                    token_data.get("access_token"),
                    token_data.get("refresh_token",""),
                    expiry
                )
                st.session_state["gcal_code_processed"] = True
                st.session_state.pop("pre_oauth_uid", None)
                st.query_params.clear()
                st.query_params["uid"] = str(_oauth_uid)
                st.success("✅ Google Calendar 연결됨!")
                st.rerun()

# ===== DESIGN SYSTEM =====
th = st.session_state.theme
DESIGN = {
    "light": {
        "bg": "#FFFFFF", "surface": "#F7F7F8", "surface2": "#F0F0F1",
        "border": "#E5E5E5", "border2": "#D4D4D4",
        "text": "#0F0F0F", "text2": "#6B6B6B", "text3": "#9B9B9B",
        "accent": "#2563EB", "accent_hover": "#1D4ED8",
        "success": "#059669", "warning": "#D97706", "danger": "#DC2626",
        "sidebar_bg": "#FAFAFA",
    },
    "dark": {
        "bg": "#0F0F0F", "surface": "#1A1A1A", "surface2": "#242424",
        "border": "#2A2A2A", "border2": "#333333",
        "text": "#EBEBEB", "text2": "#A0A0A0", "text3": "#666666",
        "accent": "#3B82F6", "accent_hover": "#2563EB",
        "success": "#10B981", "warning": "#F59E0B", "danger": "#EF4444",
        "sidebar_bg": "#141414",
    }
}
D = DESIGN[th]

st.markdown(f"""<style>
/* ===== BASE RESET ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*, *::before, *::after {{ box-sizing: border-box; }}
.stApp {{ background:{D['bg']} !important; font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif !important; }}
.stApp p, .stApp span, .stApp div, .stApp label {{ color:{D['text']}; font-size:14px; line-height:1.6; }}
h1, h2, h3 {{ color:{D['text']} !important; font-weight:600 !important; letter-spacing:-0.02em; }}
h2 {{ font-size:1.5rem !important; }}
h3 {{ font-size:1.1rem !important; }}

/* ===== SIDEBAR ===== */
section[data-testid="stSidebar"] {{ background:{D['sidebar_bg']} !important; border-right:1px solid {D['border']} !important; }}
section[data-testid="stSidebar"] > div {{ background:{D['sidebar_bg']} !important; }}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div {{ color:{D['text']} !important; }}
section[data-testid="stSidebar"] .stRadio label {{ color:{D['text']} !important; font-size:13.5px !important; }}

/* ===== INPUTS ===== */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox select {{
    background:{D['surface']} !important;
    color:{D['text']} !important;
    border:1px solid {D['border']} !important;
    border-radius:8px !important;
    font-size:14px !important;
    transition: border-color 0.15s !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color:{D['accent']} !important;
    box-shadow: 0 0 0 3px {D['accent']}20 !important;
    outline: none !important;
}}
.stSelectbox > div > div {{
    background:{D['surface']} !important;
    color:{D['text']} !important;
    border:1px solid {D['border']} !important;
    border-radius:8px !important;
}}

/* ===== BUTTONS ===== */
.stButton > button {{
    border-radius:8px !important;
    font-size:13.5px !important;
    font-weight:500 !important;
    padding:6px 14px !important;
    border:1px solid {D['border']} !important;
    background:{D['surface']} !important;
    color:{D['text']} !important;
    transition:all 0.15s !important;
}}
.stButton > button:hover {{
    background:{D['surface2']} !important;
    border-color:{D['border2']} !important;
}}
.stButton > button[kind="primary"] {{
    background:{D['accent']} !important;
    color:#fff !important;
    border-color:{D['accent']} !important;
}}
.stButton > button[kind="primary"]:hover {{
    background:{D['accent_hover']} !important;
    border-color:{D['accent_hover']} !important;
}}

/* ===== METRICS ===== */
div[data-testid="stMetric"] {{
    background:{D['surface']} !important;
    border:1px solid {D['border']} !important;
    border-radius:12px !important;
    padding:16px !important;
}}
div[data-testid="stMetricValue"] {{ color:{D['text']} !important; font-size:1.6rem !important; font-weight:700 !important; }}
div[data-testid="stMetricLabel"] {{ color:{D['text2']} !important; font-size:12px !important; }}

/* ===== TABS ===== */
div[data-baseweb="tab-list"] {{
    background:transparent !important;
    border-bottom:1px solid {D['border']} !important;
    gap:4px !important;
}}
button[data-baseweb="tab"] {{
    color:{D['text2']} !important;
    font-size:13.5px !important;
    font-weight:500 !important;
    border-radius:6px 6px 0 0 !important;
    padding:8px 16px !important;
    background:transparent !important;
    border:none !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color:{D['accent']} !important;
    border-bottom:2px solid {D['accent']} !important;
    background:transparent !important;
}}

/* ===== EXPANDER ===== */
div[data-testid="stExpander"] {{
    border:1px solid {D['border']} !important;
    border-radius:10px !important;
    background:{D['surface']} !important;
}}
div[data-testid="stExpander"] summary {{
    color:{D['text']} !important;
    font-weight:500 !important;
    font-size:14px !important;
}}

/* ===== ALERTS ===== */
div[data-testid="stInfo"] {{ background:{D['accent']}12 !important; border:1px solid {D['accent']}30 !important; border-radius:8px !important; color:{D['text']} !important; }}
div[data-testid="stSuccess"] {{ background:{D['success']}12 !important; border:1px solid {D['success']}30 !important; border-radius:8px !important; }}
div[data-testid="stWarning"] {{ background:{D['warning']}12 !important; border:1px solid {D['warning']}30 !important; border-radius:8px !important; }}
div[data-testid="stError"] {{ background:{D['danger']}12 !important; border:1px solid {D['danger']}30 !important; border-radius:8px !important; }}

/* ===== MISC ===== */
hr {{ border:none !important; border-top:1px solid {D['border']} !important; margin:16px 0 !important; }}
div[data-testid="stCheckbox"] label {{ color:{D['text']} !important; font-size:14px !important; }}
div[data-testid="stRadio"] label {{ color:{D['text']} !important; }}
code {{ background:{D['surface2']} !important; color:{D['accent']} !important; border-radius:4px !important; padding:1px 5px !important; font-size:12px !important; }}
div[data-testid="stProgressBar"] > div {{ background:{D['surface2']} !important; border-radius:99px !important; }}
div[data-testid="stProgressBar"] > div > div {{ background:{D['accent']} !important; border-radius:99px !important; }}

/* ===== MOBILE ===== */
@media(max-width:768px){{
  [data-testid="stHorizontalBlock"]>div{{flex:100%!important;max-width:100%!important}}
  section[data-testid="stSidebar"]{{width:260px!important}}
  .stApp p{{font-size:13px}}
  h2{{font-size:1.2rem!important}}
}}
@media(max-width:480px){{
  [data-testid="stHorizontalBlock"]>div{{flex:100%!important;max-width:100%!important}}
}}

/* ===== CUSTOM COMPONENTS ===== */
.pa-card{{
    background:{D['surface']};
    border:1px solid {D['border']};
    border-radius:12px;
    padding:14px 16px;
    margin:6px 0;
    transition:box-shadow 0.15s;
}}
.pa-card:hover{{box-shadow:0 2px 8px rgba(0,0,0,0.08)}}
.pa-breadcrumb{{font-size:12px;color:{D['text3']};margin-bottom:8px;display:flex;align-items:center;gap:6px}}
.pa-empty{{text-align:center;padding:40px 20px;color:{D['text3']}}}
.pa-empty-icon{{font-size:2.5rem;margin-bottom:10px}}
.pa-editing-badge{{
    background:{D['warning']}15;
    border:1px solid {D['warning']}40;
    border-radius:8px;
    padding:8px 14px;
    margin-bottom:12px;
    font-size:13px;
    color:{D['text']};
}}
.pa-tag{{
    display:inline-block;
    background:{D['accent']}15;
    color:{D['accent']};
    border-radius:99px;
    padding:2px 10px;
    font-size:12px;
    font-weight:500;
    margin:2px;
}}
.pa-section-header{{
    font-size:11px;
    font-weight:600;
    color:{D['text3']};
    letter-spacing:0.08em;
    text-transform:uppercase;
    margin:20px 0 10px 0;
}}
</style>""", unsafe_allow_html=True)

# ===== COLOR / PRIORITY SYSTEM =====
COLOR_PRESETS={"blue":"#3B82F6","red":"#EF4444","green":"#22C55E","purple":"#8B5CF6",
               "orange":"#F97316","pink":"#EC4899","teal":"#14B8A6","yellow":"#EAB308",
               "gray":"#6B7280","indigo":"#6366F1"}
COLOR_DOTS={"blue":"🔵","red":"🔴","green":"🟢","purple":"🟣","orange":"🟠",
            "pink":"🩷","teal":"🩵","yellow":"🟡","gray":"⚫","indigo":"🔷"}
PRIO_COLORS={"high":"#F97316","medium":"#F59E0B","low":"#10B981"}
PRIO_ICONS={"high":"🟠","medium":"🟡","low":"🟢"}
PRIO_LABELS={"high":"🟠 High","medium":"🟡 Medium","low":"🟢 Low"}

def get_label(color_key, custom_labels):
    if custom_labels and color_key in custom_labels:
        return custom_labels[color_key].get("label", color_key.capitalize())
    return color_key.capitalize()

def get_group(task):
    p = task.get("project","") or ""
    if p.lower()=="personal": return "personal"
    if p: return "project"
    return "general"

def clear_nc():
    for k in ["nc","nt","ntags","nt_sel"]:
        if k in st.session_state: del st.session_state[k]

def clear_ai():
    st.session_state.ai_result=None
    st.session_state.ai_result_type=None
    st.session_state.md_preview_mode=False

def relative_date(dt_str):
    if not dt_str: return ""
    try:
        d=date.fromisoformat(dt_str[:10]); diff=(today_kst()-d).days
        if diff==0: return "오늘"
        if diff==1: return "어제"
        if diff<7: return f"{diff}일 전"
        return f"{d.month}월 {d.day}일"
    except: return dt_str[:10]

def get_default_templates():
    return {
        "meeting":"## 📋 Meeting\n- Date: \n- Attendees: \n\n## Agenda\n1. \n\n## Discussion\n\n## Decisions\n\n## Action Items\n- [ ] \n\n## Next Steps\n- ",
        "idea":"## 💡 Idea\n\n### Core Concept\n\n### Background\n\n### Expected Impact\n\n### Action Plan\n1. ",
        "project":"## 📁 Project\n- Start: \n- Deadline: \n- Status: \n\n## Goals\n1. \n\n## Tasks\n- [ ] \n\n## Notes\n\n## Resources\n- ",
        "daily":f"# {today_kst().strftime('%Y-%m-%d %A')}\n\n## 오늘의 메모\n\n\n## To Do\n- [ ] \n\n## 아이디어\n\n",
        "note":"",
    }

def get_note_template(uid, note_type):
    if DB:
        try:
            tmps = get_templates(uid)
            for t in tmps:
                if t.get("note_type")==f"default_{note_type}": return t["content"]
        except: pass
    return get_default_templates().get(note_type,"")

# ===== 임시저장 =====
current_page_now=st.session_state.current_page
prev_page_now=st.session_state.get("prev_page",current_page_now)
if prev_page_now=="📝 Notes" and current_page_now!="📝 Notes":
    if st.session_state.get("editing_note"):
        note_tmp=st.session_state.editing_note
        temp_c=st.session_state.get("nc",note_tmp.get("content","") if note_tmp else "")
        temp_t=st.session_state.get("nt",note_tmp.get("title","") if note_tmp else "")
        st.session_state["temp_note_save"]={"note":note_tmp,"content":temp_c,"title":temp_t}
        st.session_state.editing_note=None; clear_ai()
if prev_page_now=="✅ Tasks" and current_page_now!="✅ Tasks":
    if st.session_state.get("editing_task"):
        st.session_state["temp_task_save"]=st.session_state.editing_task
        st.session_state.editing_task=None
st.session_state.prev_page=current_page_now

# ===== SIDEBAR =====
with st.sidebar:
    if not st.session_state.logged_in:
        st.markdown(f"<h2 style='color:{D['text']};font-size:1.2rem;margin-bottom:20px'>🚀 Personal Assistant</h2>", unsafe_allow_html=True)
        tab=st.radio("",["Login","Sign Up"],horizontal=True,label_visibility="collapsed")
        if tab=="Login":
            em=st.text_input("이메일",key="le",placeholder="you@example.com")
            pw=st.text_input("비밀번호",type="password",key="lp",placeholder="••••••••")
            if st.button("로그인",use_container_width=True,type="primary"):
                if DB:
                    u,err=login_user(em,pw)
                    if u:
                        st.session_state.logged_in=True; st.session_state.user=u
                        st.query_params["uid"]=str(u["id"])
                        # Store to localStorage for iPhone Safari
                        components.html(f"<script>window.parent.postMessage({{type:'store_uid',uid:'{u['id']}'}}, '*');</script>",height=0)
                        st.rerun()
                    else: st.error(err)
                else:
                    st.session_state.logged_in=True
                    st.session_state.user={"id":"demo","email":em,"display_name":em.split("@")[0]}
                    st.rerun()
        else:
            nm=st.text_input("이름",key="rn"); em=st.text_input("이메일",key="re")
            pw=st.text_input("비밀번호",type="password",key="rp"); pw2=st.text_input("확인",type="password",key="rp2")
            if st.button("회원가입",use_container_width=True,type="primary"):
                if pw!=pw2: st.error("비밀번호가 일치하지 않습니다")
                elif DB:
                    u,err=register_user(em,pw,nm)
                    if u: st.success("완료! 로그인해주세요.")
                    else: st.error(err)
    else:
        user=st.session_state.user; uid=user["id"]
        dname=user.get("display_name",user.get("email","").split("@")[0])

        st.markdown(f"""<div style='padding:12px 0 8px'>
<div style='font-size:13px;color:{D['text3']};margin-bottom:2px'>Personal Assistant</div>
<div style='font-size:15px;font-weight:600;color:{D['text']}'>{dname}</div>
</div>""", unsafe_allow_html=True)
        st.markdown(f"<hr style='border-color:{D['border']};margin:8px 0 12px'>", unsafe_allow_html=True)

        # Quick Capture
        st.markdown(f"<div class='pa-section-header'>Quick Capture</div>", unsafe_allow_html=True)
        qtext=st.text_input("",placeholder="무엇이든 입력...",label_visibility="collapsed",key="qi")
        if qtext:
            qc1,qc2=st.columns(2)
            if qc1.button("분류",use_container_width=True,key="qp"):
                if DB:
                    with st.spinner("..."):
                        c=smart_classify(qtext); st.session_state.qc_preview=c; st.session_state.qc_text=qtext
            if qc2.button("저장",use_container_width=True,key="qs"):
                if DB: create_note(uid,qtext[:50],qtext); st.success("저장됨"); st.rerun()
        if st.session_state.get("qc_preview"):
            c=st.session_state.qc_preview; ct=c.get("type","note")
            icons={"task":"✅","expense":"💰","note":"📝","event":"📅"}
            st.info(f"{icons.get(ct,'📝')} **{ct.upper()}**: {c.get('title',qtext)[:35]}")
            cc1,cc2=st.columns(2)
            if cc1.button("확인",use_container_width=True,key="qcs"):
                if DB:
                    qt=st.session_state.get("qc_text","")
                    if ct=="task": create_task(uid,c.get("title",qt))
                    elif ct=="expense" and c.get("amount"): add_expense(uid,int(c["amount"]),c.get("category","기타"),qt)
                    else: create_note(uid,c.get("title",qt[:50]),qt)
                    st.session_state.qc_preview=None; st.session_state.qc_text=""; st.rerun()
            if cc2.button("취소",use_container_width=True,key="qcx"):
                st.session_state.qc_preview=None; st.rerun()

        # Quick Search
        st.markdown(f"<div class='pa-section-header'>Quick Search</div>", unsafe_allow_html=True)
        qs_kw=st.text_input("",placeholder="검색...",label_visibility="collapsed",key="qs_kw")
        if qs_kw and DB:
            qs_results=search_all(uid,qs_kw)
            if qs_results:
                for r in qs_results[:6]:
                    icon={"note":"📝","task":"✅","event":"📅"}.get(r["type"],"📄")
                    col1,col2=st.columns([3,1])
                    col1.caption(f"{icon} {r['title'][:20]}")
                    if col2.button("→",key=f"qs_go_{r['id']}",help="열기"):
                        if r["type"]=="note":
                            all_n=get_notes(uid)
                            target=[n for n in all_n if n["id"]==r["id"]]
                            if target: st.session_state.editing_note=target[0]; clear_nc(); clear_ai(); st.session_state.current_page="📝 Notes"
                        elif r["type"]=="task":
                            all_t=get_tasks(uid)
                            target=[t for t in all_t if t["id"]==r["id"]]
                            if target: st.session_state.editing_task=target[0]; st.session_state.current_page="✅ Tasks"
                        elif r["type"]=="event":
                            try: st.session_state.cal_prefill_date=date.fromisoformat(r.get("date",""))
                            except: st.session_state.cal_prefill_date=today_kst()
                            st.session_state.current_page="📅 Calendar"
                        st.rerun()
            else: st.caption("결과 없음")

        st.markdown(f"<hr style='border-color:{D['border']};margin:12px 0'>", unsafe_allow_html=True)
        pages=["🏠 Dashboard","📅 Calendar","✅ Tasks","📝 Notes","🎯 목표 & 습관",
               "🎙️ Transcription","✨ AI Content","💹 Economy","📧 Email",
               "🔗 Web Clipper","🍅 Pomodoro","📊 Weekly Report","🔍 Search","⚙️ Settings"]
        new_page=st.radio("",pages,label_visibility="collapsed",
                          index=pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0)
        if new_page!=st.session_state.current_page:
            st.session_state.current_page=new_page; st.rerun()

        st.markdown(f"<hr style='border-color:{D['border']};margin:12px 0'>", unsafe_allow_html=True)
        tt=st.radio("",["Light","Dark"],horizontal=True,label_visibility="collapsed",index=0 if th=="light" else 1)
        nt="light" if tt=="Light" else "dark"
        if nt!=st.session_state.theme: st.session_state.theme=nt; st.rerun()
        if st.button("로그아웃",use_container_width=True):
            st.query_params.clear()
            components.html("<script>window.parent.postMessage({type:'clear_uid'}, '*');</script>",height=0)
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

if not st.session_state.logged_in:
    st.markdown(f"""<div style='display:flex;flex-direction:column;align-items:center;justify-content:center;height:80vh;text-align:center'>
<h1 style='font-size:2.5rem;font-weight:700;color:{D['text']};margin-bottom:8px'>🚀 Personal Assistant</h1>
<p style='color:{D['text2']};font-size:1rem;margin-bottom:32px'>Notes · Tasks · Calendar · AI — 하나로</p>
<p style='color:{D['text3']};font-size:0.875rem'>← 왼쪽 사이드바에서 로그인하세요</p>
</div>""", unsafe_allow_html=True)
    st.stop()

user=st.session_state.user; uid=user["id"]; dname=user.get("display_name","User")
page=st.session_state.current_page

# ===== HELPER: section header =====
def section(title, subtitle=None):
    s = f"<div style='margin:0 0 20px'><h2 style='margin:0;color:{D['text']}'>{title}</h2>"
    if subtitle: s += f"<p style='margin:4px 0 0;color:{D['text2']};font-size:13px'>{subtitle}</p>"
    s += "</div>"
    st.markdown(s, unsafe_allow_html=True)

def card(content, color=None):
    border_left = f"border-left:3px solid {color};" if color else ""
    st.markdown(f'<div class="pa-card" style="{border_left}">{content}</div>', unsafe_allow_html=True)

# ===== DASHBOARD =====
if page=="🏠 Dashboard":
    col_title,col_cfg=st.columns([5,1])
    col_title.markdown(f"<h2 style='color:{D['text']};margin-bottom:4px'>안녕하세요, {dname}님 👋</h2><p style='color:{D['text2']};font-size:13px;margin:0'>{now_kst().strftime('%Y년 %m월 %d일 %A')}</p>",unsafe_allow_html=True)
    with col_cfg.expander("위젯"):
        dw=st.session_state.dash_widgets; order=st.session_state.dash_widget_order
        wlabels={"reminders":"리마인더","habits":"목표 & 습관","pinned":"핀","recent":"최근 노트","tasks":"오늘 할 일"}
        for i,wk in enumerate(order):
            w1,w2,w3=st.columns([4,1,1])
            dw[wk]=w1.checkbox(wlabels.get(wk,wk),value=dw.get(wk,True),key=f"dw_{wk}")
            if i>0 and w2.button("↑",key=f"up_{wk}"):
                order[i],order[i-1]=order[i-1],order[i]; st.session_state.dash_widget_order=order; st.rerun()
            if i<len(order)-1 and w3.button("↓",key=f"dn_{wk}"):
                order[i],order[i+1]=order[i+1],order[i]; st.session_state.dash_widget_order=order; st.rerun()
        st.session_state.dash_widgets=dw

    if DB:
        tasks=get_tasks(uid)
        backlog=[t for t in tasks if t["status"]=="backlog"]
        todo=[t for t in tasks if t["status"]=="todo"]
        doing=[t for t in tasks if t["status"]=="doing"]
        done_t=[t for t in tasks if t["status"]=="done"]
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Backlog",len(backlog)); c2.metric("To Do",len(todo))
        c3.metric("진행 중",len(doing)); c4.metric("완료",len(done_t))

        for wk in st.session_state.dash_widget_order:
            if not dw.get(wk,True): continue
            if wk=="reminders":
                upcoming=[t for t in todo+doing if t.get("due_date") and t["due_date"]<=str(today_kst()+timedelta(days=2))]
                if upcoming:
                    st.warning(f"마감 임박 태스크 {len(upcoming)}개")
                    for t in upcoming:
                        is_today=t["due_date"]==str(today_kst())
                        p=PRIO_ICONS.get(t.get("priority","medium"),"🟡")
                        st.markdown(f"- {p} **{t['title']}** — {'🔥 오늘!' if is_today else t['due_date']}")
            elif wk=="habits":
                st.markdown("---")
                st.markdown(f"<div class='pa-section-header'>목표 & 습관</div>",unsafe_allow_html=True)
                habits=get_habits(uid)
                if habits:
                    logs=get_habit_logs(uid,today_kst(),today_kst())
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
                                new_val=st.number_input(f"/{target}{unit}",min_value=0.0,max_value=target*3,value=cur_val,step=0.5,key=f"hv_{h['id']}")
                                pct=min(new_val/target,1.0) if target>0 else 0
                                st.progress(pct,text=f"{new_val}/{target}{unit}")
                                done_check=st.checkbox("완료",value=h["id"] in done_ids or pct>=1.0,key=f"hnc_{h['id']}")
                                if st.button("저장",key=f"hsv_{h['id']}",use_container_width=True):
                                    toggle_habit_value(h["id"],uid,new_val if done_check else 0)
                            else:
                                checked=st.checkbox(f"{h.get('icon','✅')} {h['name']}",value=h["id"] in done_ids,key=f"h_{h['id']}")
                                if checked!=(h["id"] in done_ids): toggle_habit(h["id"],uid)
                    ws_d=today_kst()-timedelta(days=today_kst().weekday())
                    wl=get_habit_logs(uid,ws_d,today_kst())
                    wc=len([l for l in wl if l.get("completed")]); wt=len(habits)*(today_kst().weekday()+1)
                    r=int(wc/wt*100) if wt>0 else 0
                    st.progress(r/100,text=f"이번 주 {r}%")
                else:
                    st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">🎯</div><p style="color:{D["text3"]}">목표/습관 없음<br><small>🎯 목표 & 습관 메뉴에서 추가</small></p></div>',unsafe_allow_html=True)
            elif wk=="pinned":
                pins=get_pinned(uid)
                if pins:
                    st.markdown("---")
                    st.markdown(f"<div class='pa-section-header'>핀</div>",unsafe_allow_html=True)
                    for p in pins: st.markdown(f"{'📝' if p['item_type']=='note' else '🔗'} {p['title']}")
            elif wk=="recent":
                st.markdown("---")
                st.markdown(f"<div class='pa-section-header'>최근 노트</div>",unsafe_allow_html=True)
                notes=get_notes(uid)[:5]
                if notes:
                    for n in notes:
                        c1,c2=st.columns([5,1])
                        c1.markdown(f"📝 **{n['title']}** <small style='color:{D['text3']}'>{relative_date(n.get('updated_at',''))}</small>",unsafe_allow_html=True)
                        if c2.button("열기",key=f"db_n_{n['id']}"):
                            st.session_state.editing_note=n; clear_nc(); clear_ai(); st.session_state.current_page="📝 Notes"; st.rerun()
                else:
                    st.markdown(f'<div class="pa-empty"><p style="color:{D["text3"]}">노트 없음</p></div>',unsafe_allow_html=True)
            elif wk=="tasks":
                st.markdown("---")
                st.markdown(f"<div class='pa-section-header'>오늘 할 일</div>",unsafe_allow_html=True)
                if todo:
                    for t in todo[:5]:
                        p=PRIO_ICONS.get(t.get("priority","medium"),"🟡")
                        is_urgent=t.get("due_date")==str(today_kst())
                        st.markdown(f"{'🔥' if is_urgent else p} {t['title']}")
                else:
                    st.markdown(f'<div class="pa-empty"><p style="color:{D["text3"]}">모든 할 일 완료! 🎉</p></div>',unsafe_allow_html=True)

        st.markdown("---")
        bc1,bc2=st.columns(2)
        if bc1.button("Morning Briefing",type="primary",use_container_width=True):
            with st.spinner("..."):
                st.markdown(get_ai(f"오늘:{now_kst().strftime('%Y-%m-%d %A')}. 할일:{len(todo)}, 진행:{len(doing)}.\n간결한 아침 브리핑: 1)오늘 집중 2)팁 3)동기부여",st.session_state.ai_engine,"summary"))
        if bc2.button("Daily Review",use_container_width=True):
            with st.spinner("..."):
                today_notes=[n for n in get_notes(uid) if n.get("updated_at","")[:10]==str(today_kst())]
                st.markdown(get_ai(f"오늘 작성 노트:{len(today_notes)}개, 완료:{len(done_t)}개.\n회고: 1)한일 2)배운점 3)내일계획",st.session_state.ai_engine,"summary"))

# ===== CALENDAR =====
elif page=="📅 Calendar":
    section("캘린더")

    # Google Calendar 상태 표시 + 연동
    if DB:
        gcal_tokens = get_google_tokens(uid)
        gcal_connected = gcal_tokens and gcal_tokens.get("refresh_token")

    gcal_col1, gcal_col2 = st.columns([4,1])
    if gcal_connected:
        gcal_col1.success("Google Calendar 연결됨 ✅")
        if gcal_col2.button("연결 해제"):
            clear_google_tokens(uid); st.rerun()
        # 자동 동기화: Calendar 페이지 진입 시
        if GCAL and gcal_connected:
            last_sync = st.session_state.get("gcal_synced_at")
            should_sync = not last_sync or (now_kst() - last_sync).seconds > 60
            if should_sync:
                with st.spinner("Google Calendar 동기화 중..."):
                    try:
                        today_cal = today_kst()
                        gcal_start = datetime.combine(today_cal.replace(day=1), datetime.min.time())
                        gcal_end = gcal_start + timedelta(days=60)
                        gcal_events = gcal_get_events(uid, gcal_start, gcal_end)
                        # Upsert Google events into local DB
                        existing = get_events(uid, gcal_start, gcal_end)
                        existing_gcal_ids = {e.get("gcal_id") for e in existing if e.get("gcal_id")}
                        added = 0
                        for ge in gcal_events:
                            parsed = parse_gcal_event(ge)
                            if parsed["gcal_id"] not in existing_gcal_ids:
                                try:
                                    start_dt = datetime.fromisoformat(parsed["start_time"].replace("Z","+00:00"))
                                    end_dt = datetime.fromisoformat(parsed["end_time"].replace("Z","+00:00")) if parsed.get("end_time") else start_dt + timedelta(hours=1)
                                    create_event(uid, parsed["title"], start_dt, end_dt, parsed.get("description",""), "indigo", parsed["gcal_id"], "google")
                                    added += 1
                                except: pass
                        st.session_state.gcal_synced_at = now_kst()
                        if added > 0:
                            st.info(f"Google Calendar에서 {added}개 일정 가져왔습니다")
                    except Exception as e:
                        st.warning(f"Google Calendar 동기화 실패: {e}")
    else:
        if GCAL:
            auth_url = build_auth_url()
            if auth_url:
                gcal_col1.info("Google Calendar를 연동하면 일정이 자동으로 동기화됩니다 (60초마다)")
                st.session_state["pre_oauth_uid"] = uid
                gcal_col1.info("아래 버튼 클릭 후 Google 계정 연결 → 앱으로 돌아오면 자동 연결됩니다")
                gcal_col2.markdown(f'<a href="{auth_url}" target="_blank" style="display:inline-block;background:#2563EB;color:#fff;border-radius:8px;padding:8px 16px;font-size:13px;font-weight:600;text-decoration:none">🔗 Google 연결</a>', unsafe_allow_html=True)
            else:
                gcal_col1.caption("Settings > Secrets에 GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET 추가 시 Google Calendar 연동 가능")
        else:
            gcal_col1.caption("Google Calendar 연동: requirements.txt에 google-api-python-client 추가 필요")

    view=st.radio("",["Monthly","Weekly","Daily","List"],horizontal=True,label_visibility="collapsed")
    custom_labels=get_color_labels(uid) if DB else {}
    prefill_date=st.session_state.get("cal_prefill_date") or today_kst()
    default_start=get_default_event_time()
    default_end=(datetime.combine(today_kst(),default_start)+timedelta(hours=1)).time()
    tkey=st.session_state.time_reset_key

    with st.expander("새 일정 추가",expanded=bool(st.session_state.get("cal_prefill_date"))):
        et=st.text_input("제목",key="et",placeholder="일정 제목")
        dc1,dc2,dc3=st.columns([2,1,1])
        ed=dc1.date_input("날짜",value=prefill_date,key=f"ed_{tkey}")
        etime_s=dc2.time_input("시작",value=default_start,key=f"etm_s_{tkey}",step=timedelta(minutes=15))
        etime_e=dc3.time_input("종료",value=default_end,key=f"etm_e_{tkey}",step=timedelta(minutes=15))
        dc4,dc5=st.columns([1,3])
        if dc4.button("지금",key="reset_time",use_container_width=True):
            st.session_state.time_reset_key+=1; st.rerun()
        dc5.caption(f"현재 KST: {now_kst().strftime('%H:%M')}")
        label_opts={k:get_label(k,custom_labels) for k in COLOR_PRESETS.keys()}
        cl=st.selectbox("라벨",list(label_opts.keys()),format_func=lambda x:f"{COLOR_DOTS.get(x,'🔵')} {label_opts[x]}",key="ev_label")
        edesc=st.text_area("메모",key="edesc",height=80,placeholder="메모 (선택)")
        if st.button("추가",type="primary",key="ae"):
            if not et: st.warning("제목을 입력해주세요.")
            elif DB:
                try:
                    start_dt=datetime.combine(ed,etime_s)
                    end_dt=datetime.combine(ed,etime_e)
                    # Create in local DB
                    result=create_event(uid,et,start_dt,end=end_dt,desc=edesc,color_label=cl)
                    if result:
                        # Also sync to Google Calendar
                        if GCAL and gcal_connected:
                            gcal_id = gcal_create_event(uid,et,start_dt,end_dt,edesc)
                            if gcal_id:
                                # Update local event with gcal_id
                                q = get_sb()
                                if q: q.table("calendar_events").update({"gcal_id":gcal_id,"source":"both"}).eq("id",result["id"]).execute()
                        st.success("추가됨!"); st.session_state.cal_prefill_date=None; st.rerun()
                    else: st.error("추가 실패.")
                except Exception as e: st.error(f"오류: {e}")

    if DB:
        today=today_kst()
        if view=="Monthly":
            ms=today.replace(day=1); last_day=calendar.monthrange(today.year,today.month)[1]; me=ms.replace(day=last_day)
            evs=get_events(uid,datetime.combine(ms,datetime.min.time()),datetime.combine(me,datetime.max.time()))
            st.markdown(f"**{today.strftime('%Y년 %m월')}**")
            hc=st.columns(7)
            for i,dn in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]): hc[i].markdown(f"<small style='color:{D['text3']};font-weight:600'>{dn}</small>",unsafe_allow_html=True)
            for week in calendar.monthcalendar(today.year,today.month):
                cols=st.columns(7)
                for i,day in enumerate(week):
                    if day==0: cols[i].markdown("")
                    else:
                        des=[e for e in evs if e.get("start_time","")[:10]==f"{today.year}-{today.month:02d}-{day:02d}"]
                        is_today=(day==today.day)
                        day_style=f"color:{D['accent']};font-weight:700" if is_today else f"color:{D['text']}"
                        if cols[i].button(str(day),key=f"cal_day_{day}",use_container_width=True):
                            st.session_state.cal_prefill_date=date(today.year,today.month,day)
                            st.session_state.time_reset_key+=1; st.rerun()
                        for e in des:
                            c=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                            gcal_icon="☁️ " if e.get("source") in ["google","both"] else ""
                            cols[i].markdown(f'<div style="background:{c}18;border-left:2px solid {c};padding:2px 6px;border-radius:4px;font-size:10px;margin:1px 0;overflow:hidden;white-space:nowrap">{gcal_icon}{e["title"][:12]}</div>',unsafe_allow_html=True)
        elif view=="Weekly":
            ws=today-timedelta(days=today.weekday())
            evs=get_events(uid,datetime.combine(ws,datetime.min.time()),datetime.combine(ws+timedelta(6),datetime.max.time()))
            header_cols=st.columns(7)
            for i,(col,dn) in enumerate(zip(header_cols,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])):
                day=ws+timedelta(i); is_today=(day==today)
                if is_today:
                    col.markdown(f'<div style="text-align:center;background:{D["accent"]}15;border-radius:8px;padding:6px 2px"><b style="color:{D["accent"]}">{dn}</b><br><small style="color:{D["accent"]}">{day.strftime("%m/%d")}</small></div>',unsafe_allow_html=True)
                else:
                    col.markdown(f'<div style="text-align:center;padding:6px 2px"><b style="color:{D["text2"]}">{dn}</b><br><small style="color:{D["text3"]}">{day.strftime("%m/%d")}</small></div>',unsafe_allow_html=True)
            st.markdown(f"<hr style='margin:6px 0;border-color:{D['border']}'>",unsafe_allow_html=True)
            event_cols=st.columns(7)
            for i,col in enumerate(event_cols):
                day=ws+timedelta(i); day_evs=[e for e in evs if e.get("start_time","")[:10]==str(day)]
                with col:
                    if day_evs:
                        for e in day_evs:
                            color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                            gcal_icon="☁️" if e.get("source") in ["google","both"] else ""
                            st.markdown(f'<div style="background:{color}15;border-left:3px solid {color};padding:5px 7px;margin:3px 0;border-radius:6px;font-size:11px"><b>{e.get("start_time","")[11:16]}</b> {gcal_icon}<br>{e["title"][:15]}</div>',unsafe_allow_html=True)
                            if col.button("삭제",key=f"wde_{e['id']}",help="삭제"):
                                if (st.session_state.get("delete_confirm") or "")==f"ev_{e['id']}":
                                    if e.get("gcal_id") and GCAL and gcal_connected:
                                        gcal_delete_event(uid, e["gcal_id"])
                                    delete_event(e["id"]); st.session_state.delete_confirm=None; st.rerun()
                                else: st.session_state.delete_confirm=f"ev_{e['id']}"; st.rerun()
                    else: col.markdown(f'<div style="text-align:center;color:{D["text3"]};font-size:12px;padding:10px">—</div>',unsafe_allow_html=True)
            if (st.session_state.get("delete_confirm") or "").startswith("ev_"):
                st.warning("이 일정을 삭제할까요?")
                dc1,dc2=st.columns(2)
                if dc1.button("삭제",type="primary",key="ev_del_yes"):
                    eid=st.session_state.delete_confirm.replace("ev_","")
                    ev=[e for e in get_events(uid) if e["id"]==eid]
                    if ev and ev[0].get("gcal_id") and GCAL and gcal_connected:
                        gcal_delete_event(uid,ev[0]["gcal_id"])
                    delete_event(eid); st.session_state.delete_confirm=None; st.rerun()
                if dc2.button("취소",key="ev_del_no"): st.session_state.delete_confirm=None; st.rerun()
        elif view=="Daily":
            sd=st.date_input("",value=today,label_visibility="collapsed")
            evs=get_events(uid,datetime.combine(sd,datetime.min.time()),datetime.combine(sd,datetime.max.time()))
            st.markdown(f"**{sd.strftime('%Y년 %m월 %d일 (%A)')}**")
            today_tasks=[t for t in get_tasks(uid) if t.get("due_date")==str(sd) and t["status"]!="done"]
            if today_tasks:
                st.markdown(f"<div class='pa-section-header'>마감 태스크</div>",unsafe_allow_html=True)
                for t in today_tasks:
                    p=PRIO_ICONS.get(t.get("priority","medium"),"🟡"); st.markdown(f"  {p} {t['title']}")
            if evs:
                st.markdown(f"<div class='pa-section-header'>일정</div>",unsafe_allow_html=True)
                for e in evs:
                    color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                    gcal_badge = f'<span style="background:{D["accent"]}15;color:{D["accent"]};font-size:10px;padding:1px 5px;border-radius:4px">Google</span>' if e.get("source") in ["google","both"] else ""
                    c1,c2=st.columns([6,1])
                    c1.markdown(f'<div style="border-left:3px solid {color};padding:8px 12px;border-radius:0 8px 8px 0;background:{color}08;margin:4px 0"><b>{e.get("start_time","")[11:16]}–{e.get("end_time","")[11:16] if e.get("end_time") else ""}</b> {e["title"]} {gcal_badge}{"<br><small style=color:#888>"+e["description"]+"</small>" if e.get("description") else ""}</div>',unsafe_allow_html=True)
                    if c2.button("삭제",key=f"de_{e['id']}"):
                        if (st.session_state.get("delete_confirm") or "")==f"ev_{e['id']}":
                            if e.get("gcal_id") and GCAL and gcal_connected: gcal_delete_event(uid,e["gcal_id"])
                            delete_event(e["id"]); st.session_state.delete_confirm=None; st.rerun()
                        else: st.session_state.delete_confirm=f"ev_{e['id']}"; st.rerun()
                if (st.session_state.get("delete_confirm") or "").startswith("ev_"):
                    st.warning("삭제할까요?")
                    dy1,dy2=st.columns(2)
                    if dy1.button("삭제",type="primary",key="ev_d2_yes"):
                        eid=st.session_state.delete_confirm.replace("ev_","")
                        ev=[e for e in evs if e["id"]==eid]
                        if ev and ev[0].get("gcal_id") and GCAL and gcal_connected: gcal_delete_event(uid,ev[0]["gcal_id"])
                        delete_event(eid); st.session_state.delete_confirm=None; st.rerun()
                    if dy2.button("취소",key="ev_d2_no"): st.session_state.delete_confirm=None; st.rerun()
            else: st.markdown(f'<div class="pa-empty"><p style="color:{D["text3"]}">일정 없음</p></div>',unsafe_allow_html=True)
        else:
            evs=get_events(uid,datetime.combine(today,datetime.min.time()),datetime.combine(today+timedelta(30),datetime.max.time()))
            if evs:
                for e in evs:
                    color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                    gcal_badge="☁️ " if e.get("source") in ["google","both"] else ""
                    label_name=get_label(e.get("color_label","blue"),custom_labels)
                    st.markdown(f'<div style="border-left:3px solid {color};padding:8px 12px;border-radius:0 8px 8px 0;background:{color}08;margin:4px 0">{gcal_badge}<b>{e.get("start_time","")[:10]}</b> &nbsp;{e.get("start_time","")[11:16]} &nbsp;<b>{e["title"]}</b> &nbsp;<span style="color:{color};font-size:12px">● {label_name}</span></div>',unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">📅</div><p style="color:{D["text3"]}">향후 30일 일정 없음</p></div>',unsafe_allow_html=True)

# ===== TASKS =====
elif page=="✅ Tasks":
    section("Tasks")

    if st.session_state.get("temp_task_save"):
        t=st.session_state.temp_task_save
        st.warning(f"수정 중이던 Task: **'{t.get('title','')}'**")
        rb1,rb2=st.columns(2)
        if rb1.button("이어서 수정",use_container_width=True,key="restore_task"):
            st.session_state.editing_task=t; st.session_state.temp_task_save=None; st.rerun()
        if rb2.button("버리기",use_container_width=True,key="discard_task"):
            st.session_state.temp_task_save=None; st.rerun()

    tab_kanban,tab_project=st.tabs(["Kanban","By Project"])
    with tab_kanban:
        with st.expander("새 Task 추가"):
            tc1,tc2=st.columns(2)
            tt_new=tc1.text_input("제목",key="tt")
            proj_type=tc1.selectbox("구분",["General","Personal","Project"],key="proj_type")
            proj_name=""
            if proj_type=="Project": proj_name=tc1.text_input("Project 이름",key="proj_name_input")
            elif proj_type=="Personal": proj_name="Personal"
            tpr=tc2.selectbox("우선순위",["high","medium","low"],format_func=lambda x:PRIO_LABELS[x],index=1,key="tpr_new")
            tst=tc2.selectbox("초기 상태",["backlog","todo"],format_func=lambda x:{"backlog":"Backlog","todo":"To Do"}[x],key="tst_new")
            tdu=tc1.date_input("마감일",value=today_kst(),key="td")
            td_desc=tc2.text_input("설명",key="td_desc")
            if st.button("추가",type="primary",key="at"):
                if tt_new and DB: create_task(uid,tt_new,td_desc,tst,tpr,tdu,proj_name or None); st.success("추가됨"); st.rerun()

        if st.session_state.get("editing_task"):
            t=st.session_state.editing_task
            st.markdown(f'<div class="pa-editing-badge">수정 중: <b>{t.get("title","")}</b></div>',unsafe_allow_html=True)
            ec1,ec2=st.columns(2)
            new_title=ec1.text_input("제목",value=t.get("title",""),key="et_title")
            new_proj=ec1.text_input("Project",value=t.get("project","") or "",key="et_proj")
            new_desc=st.text_input("설명",value=t.get("description","") or "",key="et_desc")
            status_list=["backlog","todo","doing","done"]; prio_list=["high","medium","low"]
            status_labels={"backlog":"Backlog","todo":"To Do","doing":"Doing","done":"Done"}
            ec2a,ec2b=ec2.columns(2)
            new_prio=ec2a.selectbox("우선순위",prio_list,format_func=lambda x:PRIO_LABELS[x],index=prio_list.index(t.get("priority","medium")),key="et_prio")
            new_status=ec2b.selectbox("상태",status_list,format_func=lambda x:status_labels[x],index=status_list.index(t.get("status","todo")),key="et_status")
            due_val=today_kst()
            if t.get("due_date"):
                try: due_val=date.fromisoformat(t["due_date"])
                except: pass
            new_due=st.date_input("마감일",value=due_val,key="et_due")
            sc1,sc2=st.columns(2)
            if sc1.button("저장",type="primary",use_container_width=True):
                if DB:
                    update_task(t["id"],title=new_title,description=new_desc,status=new_status,priority=new_prio,due_date=str(new_due),project=new_proj or None)
                    st.session_state.editing_task=None; st.success("수정됨"); st.rerun()
            if sc2.button("취소",use_container_width=True): st.session_state.editing_task=None; st.rerun()
            st.markdown("---")

        if DB:
            at=get_tasks(uid)
            if not at:
                st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">✅</div><p style="color:{D["text3"]}">태스크 없음<br><small>위 버튼으로 추가하세요</small></p></div>',unsafe_allow_html=True)
            else:
                status_config=[("backlog","Backlog","#94A3B8"),("todo","To Do","#3B82F6"),("doing","Doing","#F97316"),("done","Done","#22C55E")]
                cols_k=st.columns(4)
                for col,(s,lb,col_color) in zip(cols_k,status_config):
                    with col:
                        tasks_in=[t for t in at if t["status"]==s]
                        st.markdown(f'<div style="border-top:2px solid {col_color};padding-top:10px;margin-bottom:8px"><span style="font-size:13px;font-weight:600;color:{D["text"]}">{lb}</span> <span style="font-size:12px;color:{D["text3"]}">({len(tasks_in)})</span></div>',unsafe_allow_html=True)
                        if not tasks_in:
                            st.markdown(f'<div style="text-align:center;color:{D["text3"]};font-size:12px;padding:16px">—</div>',unsafe_allow_html=True)
                        for t in tasks_in:
                            bc=PRIO_COLORS.get(t.get("priority","medium"),"#F59E0B")
                            p_icon=PRIO_ICONS.get(t.get("priority","medium"),"🟡")
                            grp=get_group(t)
                            meta=""
                            if grp=="personal": meta+=f'<div style="font-size:11px;color:#8B5CF6;margin-top:3px">Personal</div>'
                            elif grp=="project": meta+=f'<div style="font-size:11px;color:{D["accent"]};margin-top:3px">{t["project"]}</div>'
                            is_overdue=t.get("due_date") and t["due_date"]<str(today_kst())
                            is_today_due=t.get("due_date")==str(today_kst())
                            if t.get("due_date"):
                                if is_overdue: meta+=f'<div style="font-size:11px;color:#DC2626;margin-top:2px">기한초과 {t["due_date"]}</div>'
                                elif is_today_due: meta+=f'<div style="font-size:11px;color:#F97316;margin-top:2px">오늘 마감</div>'
                                else: meta+=f'<div style="font-size:11px;color:{D["text3"]};margin-top:2px">{t["due_date"]}</div>'
                            bg=D["surface"]
                            if is_today_due: bg="#FFF8F0" if th=="light" else "#2A1A0A"
                            elif is_overdue: bg="#FFF5F5" if th=="light" else "#2A0A0A"
                            st.markdown(f'<div style="background:{bg};border-radius:10px;padding:10px 12px;margin:4px 0;border-left:3px solid {bc};border:1px solid {D["border"]};border-left-width:3px"><div style="font-size:13.5px;font-weight:500;color:{D["text"]}">{t["title"]}</div>{meta}</div>',unsafe_allow_html=True)
                            b_cols=st.columns(4)
                            if b_cols[0].button("✏️",key=f"edit_{t['id']}"): st.session_state.editing_task=t; st.rerun()
                            if s=="backlog":
                                if b_cols[1].button("→",key=f"fwd_{t['id']}"): update_task(t["id"],status="todo"); st.rerun()
                            elif s=="todo":
                                if b_cols[1].button("←",key=f"bk_{t['id']}"): update_task(t["id"],status="backlog"); st.rerun()
                                if b_cols[2].button("→",key=f"fwd_{t['id']}"): update_task(t["id"],status="doing"); st.rerun()
                            elif s=="doing":
                                if b_cols[1].button("←",key=f"bk_{t['id']}"): update_task(t["id"],status="todo"); st.rerun()
                                if b_cols[2].button("✓",key=f"dn_{t['id']}"): update_task(t["id"],status="done"); st.rerun()
                            elif s=="done":
                                if b_cols[1].button("↩",key=f"bk_{t['id']}"): update_task(t["id"],status="doing"); st.rerun()
                            if b_cols[3].button("🗑",key=f"x_{t['id']}"):
                                st.session_state.delete_confirm=f"task_{t['id']}"; st.rerun()
                            if (st.session_state.get("delete_confirm") or "")==f"task_{t['id']}":
                                st.warning(f"**{t['title']}** 삭제?")
                                dy1,dy2=st.columns(2)
                                if dy1.button("삭제",type="primary",key=f"del_yes_{t['id']}"): delete_task(t["id"]); st.session_state.delete_confirm=None; st.rerun()
                                if dy2.button("취소",key=f"del_no_{t['id']}"): st.session_state.delete_confirm=None; st.rerun()
                            st.markdown(f'<div style="height:1px;background:{D["border"]};margin:4px 0;opacity:0.5"></div>',unsafe_allow_html=True)

    with tab_project:
        if DB:
            at=get_tasks(uid)
            if not at:
                st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">📁</div><p style="color:{D["text3"]}">프로젝트 없음</p></div>',unsafe_allow_html=True)
            else:
                sort_opt=st.selectbox("정렬",["마감 임박순","이름순","Task 수 많은순"],key="proj_sort",label_visibility="collapsed")
                general=[t for t in at if get_group(t)=="general"]
                personal=[t for t in at if get_group(t)=="personal"]
                proj_map={}
                for t in at:
                    if get_group(t)=="project": proj_map.setdefault(t.get("project","기타"),[]).append(t)
                def proj_sort_key(item):
                    pn,tasks=item; dues=[t["due_date"] for t in tasks if t.get("due_date")]
                    if sort_opt=="마감 임박순": return min(dues) if dues else "9999"
                    if sort_opt=="이름순": return pn
                    return -len(tasks)
                sorted_projs=sorted(proj_map.items(),key=proj_sort_key)
                def render_group(name,tasks,icon,hc):
                    if not tasks: return
                    done_c=len([t for t in tasks if t["status"]=="done"]); pct=int(done_c/len(tasks)*100)
                    st.markdown(f'<div style="background:{hc}10;border:1px solid {hc}25;border-radius:12px;padding:12px 16px;margin:12px 0 6px"><span style="font-size:14px;font-weight:600;color:{hc}">{icon} {name}</span> <span style="color:{D["text3"]};font-size:12px">{done_c}/{len(tasks)} 완료</span></div>',unsafe_allow_html=True)
                    st.progress(pct/100)
                    for t in tasks:
                        s_icon={"backlog":"·","todo":"○","doing":"◑","done":"●"}.get(t["status"],"·")
                        p_icon=PRIO_ICONS.get(t.get("priority","medium"),"🟡")
                        due_str=f" · {t['due_date']}" if t.get("due_date") else ""
                        st.markdown(f'<div style="margin-left:16px;padding:3px 8px;font-size:13px;color:{D["text2"]}">{s_icon} {p_icon} {t["title"]}{due_str}</div>',unsafe_allow_html=True)
                render_group("General",general,"◎",D["accent"])
                render_group("Personal",personal,"◈","#8B5CF6")
                for pn,tasks in sorted_projs: render_group(pn,tasks,"◉","#22C55E")

# ===== NOTES =====
elif page=="📝 Notes":
    if st.session_state.get("temp_note_save"):
        temp=st.session_state.temp_note_save
        st.warning(f"임시저장된 노트: **'{temp.get('title','(제목 없음)')}'**")
        rb1,rb2=st.columns(2)
        if rb1.button("이어서 편집",use_container_width=True,key="restore_note"):
            restored=dict(temp["note"]) if temp.get("note") else {}
            restored["content"]=temp.get("content",""); restored["title"]=temp.get("title","")
            st.session_state.editing_note=restored; clear_nc(); clear_ai()
            st.session_state["temp_note_save"]=None; st.rerun()
        if rb2.button("버리기",use_container_width=True,key="discard_note"):
            st.session_state["temp_note_save"]=None; st.rerun()

    if st.session_state.editing_note:
        note=st.session_state.editing_note
        all_notes=get_notes(uid) if DB else []
        # Breadcrumb + 뒤로가기
        bc1,bc2=st.columns([1,6])
        if bc1.button("← 목록",key="back_to_list"):
            temp_c=st.session_state.get("nc",note.get("content",""))
            temp_t=st.session_state.get("nt",note.get("title",""))
            if temp_c or temp_t: st.session_state["temp_note_save"]={"note":note,"content":temp_c,"title":temp_t}
            st.session_state.editing_note=None; clear_nc(); clear_ai(); st.rerun()
        bc2.markdown(f'<div class="pa-breadcrumb">📝 Notes › {"편집 중" if note.get("id") and note["id"]!="demo" else "새 노트"}</div>',unsafe_allow_html=True)

        new_title=st.text_input("",value=note.get("title",""),key="nt",placeholder="제목",label_visibility="collapsed")
        type_map={"note":"Note","meeting":"Meeting","daily":"Daily","idea":"Idea","project":"Project"}
        type_icons={"note":"📝","meeting":"📋","daily":"📅","idea":"💡","project":"📁"}
        nt_sel=st.selectbox("",list(type_map.keys()),format_func=lambda x:f"{type_icons[x]} {type_map[x]}",
                            index=list(type_map.keys()).index(note.get("note_type","note")) if note.get("note_type","note") in type_map else 0,
                            key="nt_sel",label_visibility="collapsed")
        if DB:
            all_tmps=get_templates(uid)
            note_tmps=[t for t in all_tmps if t.get("note_type") not in ["report_template","ai_prompt","pomo_prompt"] and not t.get("note_type","").startswith("default_")]
            if note_tmps:
                tc=st.columns(min(len(note_tmps)+1,6))
                for i,t in enumerate(note_tmps):
                    if tc[i].button(f"{t.get('icon','📄')} {t['name']}",key=f"tmp_{t['id']}"):
                        st.session_state["_tmpl"]=t["content"]; clear_nc(); st.rerun()

        default_content=st.session_state.pop("_tmpl",None)
        if default_content is None:
            existing=note.get("content","")
            default_content=existing if existing and existing.strip() else get_note_template(uid,nt_sel)

        # 툴바
        _tb_items=[
            ("B","**텍스트**","굵게"),("I","_텍스트_","기울임"),("S","~~텍스트~~","취소선"),
            ("H1","# 제목\n","제목1"),("H2","## 소제목\n","제목2"),("H3","### 항목\n","제목3"),
            ("- 목록","- 항목\n","글머리"),("1. 번","1. 항목\n","번호"),
            ("[ ]","- [ ] 할일\n","Task (자동생성)"),
            ("> 인용","> 인용문\n","인용"),("코드","```\n코드\n```\n","코드"),("---","---\n","구분선"),
        ]
        _tc=st.columns(12)
        for _i,(_lbl,_insert,_tip) in enumerate(_tb_items):
            if _tc[_i].button(_lbl,key=f"tb_{_i}",use_container_width=True,help=_tip):
                _cur=st.session_state.get("nc",default_content or "")
                _sep="" if (not _cur or _cur.endswith("\n")) else "\n"
                st.session_state["_tmpl"]=_cur+_sep+_insert; clear_nc(); st.rerun()

        content=st.text_area("",value=default_content,height=360,label_visibility="collapsed",key="nc",
                             placeholder="내용 입력...\n\nTip: - [ ] 항목 형식으로 입력 → 저장 시 Task 자동 생성")

        uploaded=st.file_uploader("파일 첨부",type=["txt","md","docx","xlsx","csv","png","jpg","jpeg","pdf"],key="nf_upload",label_visibility="collapsed")
        if uploaded:
            if uploaded.type.startswith("image"):
                st.image(uploaded)
                if st.button("OCR 텍스트 추출",key="ocr_btn"):
                    with st.spinner("..."):
                        ocr_text=ocr_image(uploaded.read(),uploaded.type); st.markdown(ocr_text)
                        st.session_state["_tmpl"]=content+"\n\n---\n"+ocr_text; clear_nc(); st.rerun()
            else:
                if st.button("노트에 가져오기",key="import_btn"):
                    with st.spinner("..."):
                        imported=file_to_markdown(uploaded); st.session_state["_tmpl"]=content+"\n\n---\n"+imported; clear_nc(); st.rerun()

        tag_input=st.text_input("태그",placeholder="#work, #project-a",key="ntags",label_visibility="collapsed")

        # AI Tools
        st.markdown(f"<div class='pa-section-header'>AI 도구</div>",unsafe_allow_html=True)
        ac=st.columns(4)
        btn_sum=ac[0].button("요약",use_container_width=True,help="입력 내용만 기반으로 요약")
        btn_rel=ac[1].button("연결 노트",use_container_width=True,help="노트 링크 패널")
        btn_exp=ac[2].button("확장",use_container_width=True,help="입력 내용 기반으로 확장")
        btn_md=ac[3].button("MD 변환",use_container_width=True,help="Markdown 형식으로 변환")

        if content and content.strip():
            md_toggle=st.toggle("Markdown 미리보기",value=st.session_state.get("md_preview_mode",False),key="md_toggle")
            if md_toggle!=st.session_state.get("md_preview_mode",False):
                st.session_state.md_preview_mode=md_toggle; st.rerun()
        if st.session_state.get("md_preview_mode",False) and content:
            st.markdown("---"); st.markdown(content); st.markdown("---")

        ai_prompts_db=[]
        if DB:
            all_tmps_ai=get_templates(uid)
            ai_prompts_db=[t for t in all_tmps_ai if t.get("note_type")=="ai_prompt"]
        sum_prompts=["기본 요약"]+[t["name"] for t in ai_prompts_db if t.get("icon","")=="📝"]
        exp_prompts=["기본 확장"]+[t["name"] for t in ai_prompts_db if t.get("icon","")=="✨"]
        pc1,pc2,_,_=st.columns(4)
        sel_sum=pc1.selectbox("",sum_prompts,key="sel_sum",label_visibility="collapsed")
        sel_exp=pc2.selectbox("",exp_prompts,key="sel_exp",label_visibility="collapsed")

        if btn_sum and content:
            custom_p=None
            if sel_sum!="기본 요약":
                m=[t for t in ai_prompts_db if t["name"]==sel_sum]
                if m: custom_p=m[0]["content"]
            with st.spinner("..."): result=summarize_note(content,custom_p); st.session_state.ai_result=result; st.session_state.ai_result_type="summary"; st.rerun()
        if btn_rel: st.session_state.show_related=not st.session_state.get("show_related",False); st.rerun()
        if btn_exp and content:
            custom_p=None
            if sel_exp!="기본 확장":
                m=[t for t in ai_prompts_db if t["name"]==sel_exp]
                if m: custom_p=m[0]["content"]
            with st.spinner("..."): result=expand_note(content,custom_p); st.session_state.ai_result=result; st.session_state.ai_result_type="expand"; st.rerun()
        if btn_md and content:
            with st.spinner("..."):
                result=get_ai(f"다음 내용을 깔끔한 마크다운으로 정리. 외부 정보 없이 원본만:\n\n{content}",st.session_state.ai_engine,"content")
                st.session_state.ai_result=result; st.session_state.ai_result_type="md"; st.rerun()

        if st.session_state.get("ai_result"):
            res=st.session_state.ai_result; rtype=st.session_state.ai_result_type
            type_labels={"summary":"요약 결과","expand":"확장 결과","md":"MD 변환 결과"}
            st.markdown("---")
            st.markdown(f"**{type_labels.get(rtype,'AI 결과')}**")
            st.markdown(f'<div style="background:{D["surface"]};border:1px solid {D["border"]};border-radius:10px;padding:16px;font-size:13.5px">{res}</div>',unsafe_allow_html=True)
            st.markdown("**노트에 반영:**")
            rb1,rb2,rb3,rb4=st.columns(4)
            if rb1.button("맨 위에",use_container_width=True,key="ai_top"):
                sep="\n\n---\n\n"; new_c=f"## 요약\n{res}{sep}{content}" if rtype=="summary" else f"{res}{sep}{content}"
                st.session_state["_tmpl"]=new_c; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb2.button("맨 아래",use_container_width=True,key="ai_bot"):
                st.session_state["_tmpl"]=f"{content}\n\n---\n\n{res}"; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb3.button("대체",use_container_width=True,key="ai_rep"):
                st.session_state["_tmpl"]=res; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb4.button("무시",use_container_width=True,key="ai_ign"):
                st.session_state.ai_result=None; st.rerun()

        if st.session_state.get("show_related") and note.get("id") and note["id"]!="demo":
            st.markdown("---")
            r_col1,r_col2=st.columns(2)
            with r_col1:
                st.markdown("**연결된 노트**")
                linked=get_linked_notes(note["id"]); linked_ids=[l["target_id"] for l in linked]
                linked_objs=[n for n in all_notes if n["id"] in linked_ids]
                if linked_objs:
                    for ln in linked_objs: st.markdown(f"📝 {ln['title']}")
                else: st.caption("연결된 노트 없음")
                st.caption("`[[노트제목]]` 입력 → 저장 시 자동 링크")
            with r_col2:
                st.markdown("**검색 후 연결**")
                link_search=st.text_input("",key="link_search_input",placeholder="제목 검색...",label_visibility="collapsed")
                if link_search:
                    matching=[n for n in all_notes if link_search.lower() in n["title"].lower() and n["id"]!=note.get("id")]
                    for mn in matching[:5]:
                        if st.button(f"🔗 {mn['title']}",key=f"link_{mn['id']}"): link_notes(note["id"],mn["id"]); st.success("연결됨"); st.rerun()
                if st.button("AI 추천",key="ai_related"):
                    if content and all_notes:
                        with st.spinner("..."):
                            suggested=suggest_related(content,all_notes)
                            if suggested:
                                for sid in suggested:
                                    m=[n for n in all_notes if n["id"]==sid]
                                    if m: st.markdown(f"- 📝 {m[0]['title']}")

        st.markdown("---")
        sc=st.columns([2,1,1,1])
        if sc[0].button("저장",type="primary",use_container_width=True):
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
                existing_tasks=get_tasks(uid); existing_titles={t["title"].lower() for t in existing_tasks}
                checkbox_items=re.findall(r'- \[ \] (.+)',content)
                new_tasks_cnt=0
                for item in checkbox_items:
                    item=item.strip()
                    if item and item.lower() not in existing_titles:
                        create_task(uid,item,desc=f"노트 '{new_title}'에서 자동 생성",status="todo",nid=note["id"])
                        existing_titles.add(item.lower()); new_tasks_cnt+=1
                if new_tasks_cnt>0: st.success(f"저장됨 (Task {new_tasks_cnt}개 생성)")
                else: st.success("저장됨")
        if sc[1].button("← 닫기",use_container_width=True):
            st.session_state.editing_note=None; st.session_state.show_related=False; clear_nc(); clear_ai(); st.rerun()
        if sc[2].button("삭제",use_container_width=True):
            st.session_state.delete_confirm=f"note_{note.get('id','')}"; st.rerun()
        if (st.session_state.get("delete_confirm") or "").startswith("note_"):
            st.error("정말 삭제할까요? 복구 불가합니다.")
            dy1,dy2=st.columns(2)
            if dy1.button("삭제",type="primary",key="note_del_yes"):
                if DB: delete_note(note["id"])
                st.session_state.editing_note=None; st.session_state.delete_confirm=None; clear_nc(); clear_ai(); st.rerun()
            if dy2.button("취소",key="note_del_no"): st.session_state.delete_confirm=None; st.rerun()
        if sc[3].button("내보내기",use_container_width=True):
            st.download_button("⬇️ .md",f"# {new_title}\n\n{content}",file_name=f"{new_title}.md",mime="text/markdown")
    else:
        section("Notes")
        nc1,nc2,nc3,nc4=st.columns([2,1,1,1])
        sq=nc1.text_input("",placeholder="검색...",label_visibility="collapsed")
        sort_notes=nc2.selectbox("",["최신순","업데이트순","이름순"],label_visibility="collapsed",key="note_sort")
        if nc3.button("Today",use_container_width=True,help="오늘의 일지"):
            if DB:
                today_all_notes=[n for n in get_notes(uid) if n.get("updated_at","")[:10]==str(today_kst())]
                today_note=get_daily_note(uid)
                if today_note:
                    if today_all_notes and (not today_note.get("content") or not today_note["content"].strip()):
                        with st.spinner("오늘 노트 기반 일지 초안 작성 중..."):
                            summary_list="\n".join([f"- {n['title']}: {n.get('content','')[:100]}" for n in today_all_notes[:10]])
                            draft=get_ai(f"오늘({today_kst()}) 작성된 노트들을 기반으로 일일 요약 일지 초안을 작성해주세요.\n노트:\n{summary_list}\n\n형식:\n# {today_kst().strftime('%Y-%m-%d %A')}\n\n## 오늘 요약\n\n## 주요 메모\n\n## 내일 할 일\n",st.session_state.ai_engine,"summary")
                            today_note["content"]=draft
                    st.session_state.editing_note=today_note; clear_nc(); clear_ai(); st.rerun()
        if nc4.button("+ New",type="primary",use_container_width=True):
            if DB:
                new_note=create_note(uid,"","")
                if new_note: st.session_state.editing_note=new_note; st.session_state.show_related=False; clear_nc(); clear_ai(); st.rerun()

        if DB:
            with st.expander("폴더"):
                folders=get_folders(uid)
                fc1,fc2=st.columns([3,1])
                fn=fc1.text_input("",key="fn",placeholder="새 폴더 이름",label_visibility="collapsed")
                if fc2.button("생성",key="cf"):
                    if fn: create_folder(uid,fn); st.rerun()
                if folders:
                    for f in folders:
                        f1,f2=st.columns([5,1])
                        is_active=st.session_state.get("folder_filter")==f["id"]
                        if f1.button(f"{'📂' if is_active else '📁'} {f['name']}",key=f"fld_{f['id']}",use_container_width=True):
                            st.session_state["folder_filter"]=f["id"]; st.rerun()
                        if f2.button("삭제",key=f"df_{f['id']}"): delete_folder(f["id"]); st.rerun()
                if st.session_state.get("folder_filter"):
                    if st.button("전체 보기",use_container_width=True): st.session_state.pop("folder_filter",None); st.rerun()

            fid=st.session_state.get("folder_filter")
            notes=get_notes(uid,search=sq or None,folder_id=fid)
            if sort_notes=="이름순": notes=sorted(notes,key=lambda x:x.get("title",""))
            elif sort_notes=="업데이트순": notes=sorted(notes,key=lambda x:x.get("updated_at",""),reverse=True)
            else: notes=sorted(notes,key=lambda x:x.get("created_at",""),reverse=True)

            if not notes:
                st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">📝</div><p style="color:{D["text3"]}">노트 없음<br><small>+ New로 첫 노트를 만들어보세요</small></p></div>',unsafe_allow_html=True)
            else:
                for n in notes:
                    type_icons2={"meeting":"📋","daily":"📅","idea":"💡","project":"📁"}
                    icon=type_icons2.get(n.get("note_type"),"📝")
                    fav="⭐ " if n.get("is_favorite") else ""
                    preview=n.get("content","")[:100].replace("\n"," ").strip() if n.get("content") else ""
                    cn,ca=st.columns([5,1])
                    cn.markdown(f'<div style="margin:2px 0"><span style="font-size:14px;font-weight:500;color:{D["text"]}">{fav}{icon} {n["title"]}</span> <span style="font-size:11px;color:{D["text3"]}">{relative_date(n.get("updated_at",""))}</span></div>{"<div style=font-size:12px;color:"+D["text3"]+";margin-top:2px>"+preview+"</div>" if preview else ""}',unsafe_allow_html=True)
                    if ca.button("열기",key=f"o_{n['id']}"):
                        st.session_state.editing_note=n; st.session_state.show_related=False; clear_nc(); clear_ai(); st.rerun()

            st.markdown("---")
            if st.checkbox("Note Graph"):
                all_n=get_notes(uid); all_l=get_all_links(uid); nmap={n["id"]:n["title"] for n in all_n}
                if all_l:
                    for l in all_l: st.markdown(f"📝 {nmap.get(l['source_id'],'?')} ↔️ 📝 {nmap.get(l['target_id'],'?')}")
                else: st.caption("연결된 노트 없음")
            if st.checkbox("전체 백업"):
                st.download_button("⬇️ 모든 노트 (.md)",export_all_notes_md(uid),"all_notes_backup.md","text/markdown")

# ===== 목표 & 습관 =====
elif page=="🎯 목표 & 습관":
    section("목표 & 습관")
    if DB:
        habits=get_habits(uid); logs=get_habit_logs(uid,today_kst(),today_kst())
        done_ids={l["habit_id"] for l in logs if l.get("completed")}
        log_values={l["habit_id"]:l.get("value",0) for l in logs}
        if habits:
            st.markdown(f"<div class='pa-section-header'>오늘 ({today_kst().strftime('%m월 %d일')})</div>",unsafe_allow_html=True)
            cols=st.columns(min(len(habits),3))
            for i,h in enumerate(habits):
                with cols[i%min(len(habits),3)]:
                    htype=h.get("habit_type","check")
                    if htype=="numeric":
                        target=float(h.get("target_value",1)); unit=h.get("unit","")
                        cur_val=float(log_values.get(h["id"],0))
                        st.markdown(f"**{h.get('icon','🎯')} {h['name']}**")
                        new_val=st.number_input(f"/{target}{unit}",min_value=0.0,max_value=target*3,value=cur_val,step=0.5,key=f"hp_v_{h['id']}")
                        pct=min(new_val/target,1.0) if target>0 else 0
                        st.progress(pct,text=f"{new_val}/{target}{unit}")
                        done_check=st.checkbox("완료",value=h["id"] in done_ids or pct>=1.0,key=f"hp_nc_{h['id']}")
                        if st.button("저장",key=f"hp_sv_{h['id']}",use_container_width=True):
                            toggle_habit_value(h["id"],uid,new_val if done_check else 0); st.rerun()
                    else:
                        checked=st.checkbox(f"{h.get('icon','✅')} {h['name']}",value=h["id"] in done_ids,key=f"hp_{h['id']}")
                        if checked!=(h["id"] in done_ids): toggle_habit(h["id"],uid); st.rerun()
            st.markdown("---")
            st.markdown(f"<div class='pa-section-header'>이번 주</div>",unsafe_allow_html=True)
            ws_d=today_kst()-timedelta(days=today_kst().weekday()); wl=get_habit_logs(uid,ws_d,today_kst())
            wc=len([l for l in wl if l.get("completed")]); wt=len(habits)*(today_kst().weekday()+1)
            r=int(wc/wt*100) if wt>0 else 0
            st.progress(r/100,text=f"{r}% ({wc}/{wt})")
            for h in habits:
                h_logs=[l for l in wl if l["habit_id"]==h["id"] and l.get("completed")]
                days_done=len(h_logs); days_total=today_kst().weekday()+1
                pct_h=int(days_done/days_total*100) if days_total>0 else 0
                st.markdown(f'{h.get("icon","✅")} **{h["name"]}** {days_done}/{days_total}일 ({pct_h}%)')
        else:
            st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">🎯</div><p style="color:{D["text3"]}">목표/습관 없음<br><small>아래에서 추가하세요</small></p></div>',unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(f"<div class='pa-section-header'>추가</div>",unsafe_allow_html=True)
        hc1,hc2,hc3=st.columns([2,1,1])
        hn=hc1.text_input("이름",key="hn_page"); hi=hc2.text_input("아이콘",value="✅",key="hi_page")
        htype_p=hc3.selectbox("타입",["check","numeric"],format_func=lambda x:{"check":"체크","numeric":"수치"}[x],key="htype_page")
        htarget=1.0; hunit=""
        if htype_p=="numeric":
            hc4,hc5=st.columns(2); htarget=hc4.number_input("목표값",min_value=0.1,value=1.0,step=0.5,key="htarget_p"); hunit=hc5.text_input("단위",placeholder="km, 잔...",key="hunit_p")
        if st.button("추가",key="ah_page",type="primary"):
            if hn and DB: create_habit_v2(uid,hn,hi,htype_p,htarget,hunit); st.rerun()
        if habits:
            st.markdown("---")
            st.markdown(f"<div class='pa-section-header'>관리</div>",unsafe_allow_html=True)
            for h in habits:
                c1,c2=st.columns([5,1]); c1.markdown(f"{h.get('icon','✅')} {h['name']}")
                if c2.button("삭제",key=f"dh_p_{h['id']}"):
                    st.session_state.delete_confirm=f"habit_{h['id']}"; st.rerun()
                if (st.session_state.get("delete_confirm") or "")==f"habit_{h['id']}":
                    dy1,dy2=st.columns(2)
                    if dy1.button("삭제",type="primary",key=f"habit_del_{h['id']}"): delete_habit(h["id"]); st.session_state.delete_confirm=None; st.rerun()
                    if dy2.button("취소",key=f"habit_no_{h['id']}"): st.session_state.delete_confirm=None; st.rerun()

# ===== TRANSCRIPTION =====
elif page=="🎙️ Transcription":
    section("Transcription")
    tab1,tab2=st.tabs(["전사","사전"])
    with tab1:
        audio=st.file_uploader("오디오 업로드",type=["mp3","wav","m4a","ogg","webm"],label_visibility="collapsed")
        if audio:
            st.audio(audio)
            if st.button("전사 시작",type="primary"):
                with st.spinner("..."): t=transcribe(audio); t=apply_terms(uid,t) if DB else t; st.session_state.transcript=t
        st.markdown("---")
        manual=st.text_area("텍스트 직접 입력",height=200,key="mt",label_visibility="collapsed",placeholder="전사 텍스트를 붙여넣으세요...")
        if manual:
            corrected=apply_terms(uid,manual) if DB else manual
            if corrected!=manual: st.info("용어 자동 교정됨")
            st.session_state.transcript=corrected or manual
        if st.session_state.get("transcript"):
            st.text_area("전사 결과",value=st.session_state.transcript,height=200,key="tv",disabled=True)
            save_type=st.selectbox("저장 형식",["Meeting Notes","요약","액션아이템","원문"])
            if st.button("처리 후 저장",type="primary"):
                with st.spinner("..."):
                    result=""
                    if "Meeting" in save_type: result=summarize_meeting(st.session_state.transcript)
                    elif "요약" in save_type: result=get_ai(f"5줄 핵심 요약:\n\n{st.session_state.transcript}",st.session_state.ai_engine,"summary")
                    elif "액션" in save_type: result=get_ai(f"액션아이템 체크박스로:\n\n{st.session_state.transcript}",st.session_state.ai_engine,"analysis")
                    else: result=st.session_state.transcript
                    if DB:
                        title_map={"Meeting":"📋 Meeting","요약":"Summary","액션아이템":"Actions","원문":"Transcript"}
                        t_key=next((k for k in title_map if k in save_type),"원문")
                        create_note(uid,f"{title_map[t_key]} {today_kst()}",result,"meeting" if "Meeting" in save_type else "note"); st.success("저장됨")
                    if result and "원문" not in save_type: st.markdown(result)
    with tab2:
        tc1,tc2=st.columns(2)
        w_term=tc1.text_input("잘못된 표현",placeholder="케이피아이"); c_term=tc2.text_input("올바른 표현",placeholder="KPI")
        if st.button("추가",type="primary",key="at2"):
            if w_term and c_term and DB: add_term(uid,w_term,c_term); st.success(f"추가됨"); st.rerun()
        if DB:
            terms=get_terms(uid)
            if terms:
                for w,c in terms.items(): st.markdown(f"~~{w}~~ → **{c}**")
            else: st.caption("등록된 용어 없음")

# ===== AI CONTENT =====
elif page=="✨ AI Content":
    section("AI Content 생성")
    ct=st.selectbox("유형",["Blog","Instagram","Twitter Thread","Full Package"],label_visibility="collapsed")
    topic=st.text_area("주제",placeholder="예: AI가 업무 생산성을 높이는 5가지 방법",label_visibility="collapsed",height=80)
    kw=st.text_input("키워드",placeholder="핵심 키워드 (선택)",label_visibility="collapsed")
    img=st.file_uploader("이미지 (선택)",type=["png","jpg","jpeg"],key="ci",label_visibility="collapsed")
    eng=st.radio("AI 엔진",["Auto","Gemini","Claude"],horizontal=True,label_visibility="collapsed")
    if st.button("생성",type="primary",use_container_width=True):
        if topic:
            with st.spinner("생성 중..."):
                result=""
                if img: result=analyze_image_for_content(img.read(),img.type,ct); st.markdown(result)
                else:
                    em={"Auto":"auto","Gemini":"gemini","Claude":"claude"}
                    prompts={"Blog":f"주제:{topic}\n키워드:{kw}\n\n블로그: 제목3개, SEO메타, 본문1500-2000자, 해시태그10개",
                             "Instagram":f"주제:{topic}\n키워드:{kw}\n\n인스타: 훅, 본문2000자이내, 해시태그30개",
                             "Twitter Thread":f"주제:{topic}\n키워드:{kw}\n\n트위터 5-8개, 각280자"}
                    if ct=="Full Package":
                        for t_n in ["Blog","Instagram","Twitter Thread"]:
                            st.markdown(f"### {t_n}"); part=get_ai(prompts[t_n],em[eng],"content"); st.markdown(part); result+=f"\n\n## {t_n}\n"+part; st.markdown("---")
                    else: result=get_ai(prompts[ct],em[eng],"content"); st.markdown(result)
                if result:
                    sc1,sc2=st.columns(2)
                    if sc1.button("노트에 저장",key="sc_note"):
                        if DB: create_note(uid,f"[Content] {topic[:30]}",result,"note"); st.success("저장됨")
                    sc2.download_button("다운로드",result,f"content_{ct}.txt","text/plain")

# ===== ECONOMY =====
elif page=="💹 Economy":
    section("Economy")
    tabs=st.tabs(["대시보드","수입/지출","시장","AI 분석"])
    with tabs[0]:
        if DB:
            cm=now_kst().strftime("%Y-%m"); exps=get_expenses(uid,cm); inc=get_income(uid,cm); loans=get_loans(uid)
            te=sum(e.get("amount",0) for e in exps); ti=sum(i.get("amount",0) for i in inc); tl=sum(l.get("remaining_amount",0) for l in loans)
            c1,c2,c3,c4=st.columns(4)
            c1.metric("수입",f"{ti:,}₩"); c2.metric("지출",f"{te:,}₩"); c3.metric("잔액",f"{ti-te:,}₩"); c4.metric("부채",f"{tl:,}₩")
            if exps:
                cats={}
                for e in exps: cats[e.get("category","기타")]=cats.get(e.get("category","기타"),0)+e.get("amount",0)
                st.markdown(f"<div class='pa-section-header'>카테고리별 지출</div>",unsafe_allow_html=True)
                for cat,amt in sorted(cats.items(),key=lambda x:-x[1]):
                    st.progress(min(amt/te,1) if te>0 else 0,text=f"{cat}: {amt:,}₩")
    with tabs[1]:
        sub=st.radio("",["지출","수입","대출","업로드"],horizontal=True,label_visibility="collapsed")
        if sub=="지출":
            fc1,fc2,fc3=st.columns(3)
            ea=fc1.number_input("금액(₩)",min_value=0,step=1000,key="ea"); ecat=fc2.selectbox("카테고리",["식비","교통비","쇼핑","생활비","의료","교육","여가","카페","구독","기타"]); edt=fc3.date_input("날짜",key="edt",label_visibility="collapsed")
            edsc=st.text_input("메모",key="edsc",label_visibility="collapsed",placeholder="메모")
            if st.button("기록",type="primary",key="re"):
                if ea>0 and DB: add_expense(uid,ea,ecat,edsc,edt); st.success("기록됨"); st.rerun()
            if DB:
                for e in get_expenses(uid,now_kst().strftime("%Y-%m"))[:20]:
                    st.markdown(f'<div style="font-size:13px;padding:4px 0;border-bottom:1px solid {D["border"]}">{e.get("expense_date","")} · {e.get("category","")} · {e.get("amount",0):,}₩</div>',unsafe_allow_html=True)
        elif sub=="수입":
            ic1,ic2=st.columns(2); ia=ic1.number_input("금액(₩)",min_value=0,step=100000,key="ia"); isrc=ic2.text_input("출처",key="isrc")
            if st.button("기록",type="primary",key="ri"):
                if ia>0 and DB: add_income(uid,ia,isrc); st.success("기록됨"); st.rerun()
            if DB:
                for i in get_income(uid,now_kst().strftime("%Y-%m")): st.markdown(f'{i.get("income_date","")} · {i.get("source","")} · {i.get("amount",0):,}₩')
        elif sub=="대출":
            lc1,lc2=st.columns(2); ln=lc1.text_input("이름"); lt=lc2.number_input("총액(₩)",min_value=0,step=1000000,key="lt")
            lr=lc1.number_input("잔액(₩)",min_value=0,step=1000000,key="lr"); li=lc2.number_input("금리(%)",min_value=0.0,step=0.1,key="li")
            if st.button("추가",type="primary",key="al"):
                if ln and DB: add_loan(uid,ln,lt,lr,li); st.success("추가됨"); st.rerun()
            if DB:
                for l in get_loans(uid):
                    pct=(1-l.get("remaining_amount",0)/max(l.get("total_amount",1),1))*100
                    st.progress(pct/100,text=f"{l['name']}: {l.get('remaining_amount',0):,}₩")
        elif sub=="업로드":
            uploaded=st.file_uploader("Excel/CSV",type=["csv","xlsx","txt"],key="eu",label_visibility="collapsed")
            if st.button("AI 분류 후 가져오기",type="primary"):
                if uploaded:
                    data=""
                    if uploaded.name.endswith(".csv"):
                        import pandas as pd; data=pd.read_csv(uploaded).to_string()
                    elif uploaded.name.endswith(".xlsx"):
                        import pandas as pd; data=pd.read_excel(uploaded).to_string()
                    else: data=uploaded.read().decode("utf-8")
                    if data:
                        with st.spinner("..."):
                            items=classify_expenses(data)
                            if items:
                                for c in items: st.markdown(f"{c.get('date','')} · {c.get('category','')} · {c.get('amount',0):,}₩")
                                if st.button("전체 가져오기",key="imp"):
                                    if DB: bulk_add_expenses(uid,items); st.success(f"{len(items)}개 가져옴")
    with tabs[2]:
        if st.button("최신 시장 정보",type="primary"):
            with st.spinner("..."): st.markdown(get_ai("US(S&P500,NASDAQ,DOW)+KR(KOSPI,KOSDAQ)+환율+경제뉴스5개. 간결하게.",st.session_state.ai_engine,"analysis"))
        st.markdown("---")
        st.markdown(f"<div class='pa-section-header'>관심 종목</div>",unsafe_allow_html=True)
        wc1,wc2,wc3=st.columns([2,2,1])
        ws_sym=wc1.text_input("종목코드",key="ws",label_visibility="collapsed",placeholder="종목코드")
        wn_name=wc2.text_input("이름",key="wn",label_visibility="collapsed",placeholder="종목명")
        wm=wc3.selectbox("",["KR","US"],key="wm",label_visibility="collapsed")
        if st.button("추가",key="aw"):
            if ws_sym and wn_name and DB: add_watch(uid,ws_sym,wn_name,wm); st.rerun()
        if DB:
            for w in get_watchlist(uid):
                c1,c2=st.columns([5,1]); c1.markdown(f"{'🇺🇸' if w.get('market')=='US' else '🇰🇷'} **{w['name']}** ({w['symbol']})")
                if c2.button("삭제",key=f"dw_{w['id']}"): del_watch(w["id"]); st.rerun()
    with tabs[3]:
        if st.button("재정 AI 분석",type="primary"):
            if DB:
                cm=now_kst().strftime("%Y-%m")
                with st.spinner("..."): st.markdown(analyze_finances(get_expenses(uid,cm),get_income(uid,cm),get_loans(uid)))

# ===== EMAIL =====
elif page=="📧 Email":
    section("Email 발송")
    st.info("Gmail 앱 비밀번호 필요: Gmail → 보안 → 2단계 인증 → 앱 비밀번호 (16자리)")
    to=st.text_input("받는 사람",placeholder="someone@example.com"); subj=st.text_input("제목"); body=st.text_area("내용",height=200)
    with st.expander("Gmail 설정"):
        ga=st.text_input("Gmail 주소",key="ga"); gp=st.text_input("앱 비밀번호",type="password",key="gp")
    if st.button("발송",type="primary"):
        if all([to,subj,body,ga,gp]):
            ok,msg=send_gmail(to,subj,body,ga,gp)
            st.success(msg) if ok else st.error(msg)
        else: st.warning("모든 필드를 입력해주세요.")

# ===== WEB CLIPPER =====
elif page=="🔗 Web Clipper":
    section("Web Clipper")
    url=st.text_input("URL",placeholder="https://...",label_visibility="collapsed")
    if st.button("저장 및 요약",type="primary"):
        if url:
            with st.spinner("..."):
                s=web_summary(url); st.markdown(s)
                if DB: create_note(uid,f"🔗 {url[:50]}",f"URL: {url}\n\n---\n{s}","note"); st.success("저장됨")
    if DB:
        clips=[n for n in get_notes(uid) if n.get("content","").startswith("URL:")]
        if clips:
            st.markdown(f"<div class='pa-section-header'>저장된 클립</div>",unsafe_allow_html=True)
            for c in clips[:10]: st.markdown(f"🔗 **{c['title']}** · {relative_date(c.get('updated_at',''))}")

# ===== POMODORO =====
elif page=="🍅 Pomodoro":
    section("Pomodoro 타이머")
    pc1,pc2,pc3=st.columns(3)
    focus_min=pc1.number_input("집중 시간(분)",min_value=1,max_value=90,value=25,step=5,key="focus_min")
    break_min=pc2.number_input("휴식 시간(분)",min_value=1,max_value=30,value=5,step=1,key="break_min")
    tn_work=pc3.text_input("작업 내용",key="pt",placeholder="오늘 할 일...")
    timer_html=f"""<style>
.pc{{text-align:center;padding:20px;font-family:-apple-system,sans-serif;background:transparent}}
.td{{font-size:72px;font-weight:800;color:#EF4444;font-family:'Courier New',monospace;letter-spacing:6px;margin:8px 0;line-height:1}}
.td.brk{{color:#22C55E}}
.ts{{font-size:14px;color:#888;margin-bottom:16px;min-height:20px}}
.prog{{width:280px;height:6px;background:#E5E7EB;border-radius:99px;margin:0 auto 20px;overflow:hidden}}
.pb{{height:100%;background:linear-gradient(90deg,#EF4444,#F97316);border-radius:99px;transition:width 1s linear}}
.pb.brk{{background:linear-gradient(90deg,#22C55E,#14B8A6)}}
.br{{display:flex;gap:8px;justify-content:center}}
.btn{{padding:10px 20px;font-size:14px;font-weight:600;border-radius:8px;border:none;cursor:pointer;transition:all .15s}}
.btn:hover{{opacity:0.85;transform:translateY(-1px)}}
.bs{{background:#EF4444;color:#fff}}.bb{{background:#22C55E;color:#fff}}.br2{{background:#6B7280;color:#fff}}
.sc{{font-size:13px;color:#9B9B9B;margin-top:12px}}
</style>
<div class="pc">
<div class="td" id="td">{focus_min:02d}:00</div>
<div class="ts" id="ts">시작할 준비가 되셨나요?</div>
<div class="prog"><div class="pb" id="pb" style="width:100%"></div></div>
<div class="br">
<button class="btn bs" id="sb" onclick="toggle()">▶ 시작</button>
<button class="btn bb" onclick="startBreak()">휴식</button>
<button class="btn br2" onclick="reset()">리셋</button>
</div>
<div class="sc" id="sc">오늘 완료: 0 🍅</div>
</div>
<script>
const F={focus_min}*60,B={break_min}*60;
let left=F,total=F,run=false,brk=false,iv=null,sess=0;
function fmt(t){{return String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0')}}
function ui(){{document.getElementById('td').textContent=fmt(left);document.getElementById('td').className='td'+(brk?' brk':'');document.getElementById('pb').style.width=(left/total*100)+'%';document.getElementById('pb').className='pb'+(brk?' brk':'')}}
function beep(){{try{{const a=new AudioContext(),o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.type='sine';o.frequency.setValueAtTime(880,a.currentTime);o.frequency.setValueAtTime(660,a.currentTime+0.2);o.frequency.setValueAtTime(880,a.currentTime+0.4);g.gain.setValueAtTime(0.25,a.currentTime);g.gain.exponentialRampToValueAtTime(0.01,a.currentTime+0.7);o.start();o.stop(a.currentTime+0.7)}}catch(e){{}}}}
function toggle(){{if(run){{clearInterval(iv);run=false;document.getElementById('sb').textContent='▶ 재개';document.getElementById('ts').textContent='일시정지'}}else{{run=true;document.getElementById('sb').textContent='⏸ 일시정지';document.getElementById('ts').textContent=brk?'휴식 중...':'집중 중!';iv=setInterval(()=>{{if(left>0){{left--;ui()}}else{{clearInterval(iv);run=false;document.getElementById('sb').textContent='▶ 시작';if(!brk){{sess++;document.getElementById('sc').textContent='오늘 완료: '+sess+' 🍅';document.getElementById('ts').textContent='완료! 아래에서 기록하세요';beep()}}else{{document.getElementById('ts').textContent='휴식 완료! 다시 시작해봐요';brk=false;left=F;total=F;ui()}}}}}}),1000)}}}}
function startBreak(){{clearInterval(iv);run=false;brk=true;left=B;total=B;document.getElementById('sb').textContent='▶ 시작';document.getElementById('ts').textContent='휴식 시작';ui()}}
function reset(){{clearInterval(iv);run=false;brk=false;left=F;total=F;document.getElementById('sb').textContent='▶ 시작';document.getElementById('ts').textContent='시작할 준비가 되셨나요?';ui()}}
</script>"""
    components.html(timer_html,height=280)
    st.markdown("---")
    col_r1,col_r2,col_r3=st.columns(3)
    interruptions=col_r2.number_input("방해 횟수",min_value=0,max_value=20,value=0,key="pomo_int")
    is_complete=col_r3.checkbox("완주",value=True,key="pomo_complete")
    if col_r1.button("세션 기록",type="primary",use_container_width=True):
        if DB:
            status="complete" if is_complete else "interrupted"
            log_pomo(uid,focus_min,tn_work,status=status,interruptions=interruptions)
            st.success(f"기록됨! ({'완주' if is_complete else '중단'})")
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
            with st.expander("최근 기록"):
                for l in logs[:10]:
                    s_icon="✓" if l.get("status","complete")=="complete" else "✗"
                    intr=l.get("interruptions",0)
                    st.markdown(f'{s_icon} {l.get("task_name","(미입력)")} · {relative_date(l.get("completed_at",""))} · {l.get("duration_minutes",25)}분{" · 방해"+str(intr)+"회" if intr else ""}')
            st.markdown(f"<div class='pa-section-header'>AI Insight</div>",unsafe_allow_html=True)
            pomo_prompts_db=[t for t in get_templates(uid) if t.get("note_type")=="pomo_prompt"] if DB else []
            pomo_prompt_opts=["기본 분석"]+[t["name"] for t in pomo_prompts_db]
            sel_pomo_prompt=st.selectbox("",pomo_prompt_opts,key="sel_pomo_p",label_visibility="collapsed")
            if st.button("분석",type="primary",use_container_width=True):
                custom_pp=None
                if sel_pomo_prompt!="기본 분석":
                    m=[t for t in pomo_prompts_db if t["name"]==sel_pomo_prompt]
                    if m: custom_pp=m[0]["content"]
                with st.spinner("분석 중..."): insight=pomodoro_insight(logs,custom_pp); st.markdown(insight)

# ===== WEEKLY REPORT =====
elif page=="📊 Weekly Report":
    section("Weekly Report")
    col_d1,col_d2=st.columns(2)
    use_preset=col_d1.selectbox("기간",["이번 주","지난 7일","지난 14일","이번 달","사용자 지정"],label_visibility="collapsed")
    if use_preset=="이번 주": start=today_kst()-timedelta(days=today_kst().weekday()); end=today_kst()
    elif use_preset=="지난 7일": start=today_kst()-timedelta(7); end=today_kst()
    elif use_preset=="지난 14일": start=today_kst()-timedelta(14); end=today_kst()
    elif use_preset=="이번 달": start=today_kst().replace(day=1); end=today_kst()
    else:
        start=col_d1.date_input("시작일",value=today_kst()-timedelta(7)); end=col_d2.date_input("종료일",value=today_kst())
    col_d2.caption(f"{start} ~ {end}")
    DEFAULT_FORMAT="형식:\n## 주간 업무 보고\n### 1. 핵심 성과\n### 2. 진행 중 업무\n### 3. 회의 요약\n### 4. 이슈/리스크\n### 5. 다음 주 계획"
    if DB:
        all_tmps=get_templates(uid); report_tmps=[t for t in all_tmps if t.get("note_type")=="report_template"]
        tmpl_names=["기본 템플릿"]+[t["name"] for t in report_tmps]
        sel_tmpl=st.selectbox("",tmpl_names,label_visibility="collapsed")
        if sel_tmpl=="기본 템플릿": prompt_val=DEFAULT_FORMAT
        else:
            tmpl_obj=next((t for t in report_tmps if t["name"]==sel_tmpl),None)
            prompt_val=tmpl_obj["content"] if tmpl_obj else DEFAULT_FORMAT
        custom_prompt=st.text_area("리포트 형식",value=prompt_val,height=180,label_visibility="collapsed")
        with st.expander("템플릿으로 저장"):
            new_t_name=st.text_input("이름",placeholder="템플릿 이름"); 
            if st.button("저장",key="save_rpt"):
                if new_t_name: create_template(uid,new_t_name,custom_prompt,note_type="report_template",icon="📊"); st.success("저장됨"); st.rerun()
    else: custom_prompt=DEFAULT_FORMAT
    if st.button("보고서 생성",type="primary",use_container_width=True):
        if DB:
            with st.spinner("생성 중..."):
                notes=[n for n in get_notes(uid) if n.get("updated_at","")[:10]>=str(start)]
                tasks=get_tasks(uid); exps=get_expenses(uid,now_kst().strftime("%Y-%m"))
                report=weekly_report(notes,tasks,exps,custom_format=custom_prompt); st.markdown(report)
                sc1,sc2=st.columns(2)
                if sc1.button("저장",key="sr"): create_note(uid,f"Report {start}~{end}",report,"note"); st.success("저장됨")
                sc2.download_button("다운로드",report,f"report_{start}_{end}.md","text/markdown")

# ===== SEARCH =====
elif page=="🔍 Search":
    section("Search")
    kw=st.text_input("",placeholder="노트, 태스크, 일정 통합 검색... (엔터로 검색)",label_visibility="collapsed",key="smart_search_kw")
    if kw and DB:
        results=search_all(uid,kw)
        if results:
            st.caption(f"{len(results)}개 결과")
            note_results=[r for r in results if r["type"]=="note"]
            task_results=[r for r in results if r["type"]=="task"]
            event_results=[r for r in results if r["type"]=="event"]
            all_n=get_notes(uid); all_t=get_tasks(uid)
            if note_results:
                st.markdown(f"<div class='pa-section-header'>노트</div>",unsafe_allow_html=True)
                for r in note_results:
                    target=[n for n in all_n if n["id"]==r["id"]]
                    preview=target[0].get("content","")[:80].replace("\n"," ") if target else ""
                    col1,col2=st.columns([5,1])
                    col1.markdown(f'<div><b style="color:{D["text"]}">{r["title"]}</b> <span style="color:{D["text3"]};font-size:11px">{r.get("date","")}</span></div>{"<div style=font-size:12px;color:"+D["text3"]+">"+preview+"</div>" if preview else ""}',unsafe_allow_html=True)
                    if col2.button("열기",key=f"sr_n_{r['id']}"):
                        if target: st.session_state.editing_note=target[0]; st.session_state.current_page="📝 Notes"; clear_nc(); clear_ai(); st.rerun()
            if task_results:
                st.markdown(f"<div class='pa-section-header'>태스크</div>",unsafe_allow_html=True)
                for r in task_results:
                    col1,col2=st.columns([5,1])
                    col1.markdown(f'<b style="color:{D["text"]}">{r["title"]}</b> <span style="color:{D["text3"]};font-size:11px">{r.get("date","")}</span>',unsafe_allow_html=True)
                    if col2.button("열기",key=f"sr_t_{r['id']}"):
                        target=[t for t in all_t if t["id"]==r["id"]]
                        if target: st.session_state.editing_task=target[0]; st.session_state.current_page="✅ Tasks"; st.rerun()
            if event_results:
                st.markdown(f"<div class='pa-section-header'>일정</div>",unsafe_allow_html=True)
                for r in event_results:
                    col1,col2=st.columns([5,1])
                    col1.markdown(f'<b style="color:{D["text"]}">{r["title"]}</b> <span style="color:{D["text3"]};font-size:11px">{r.get("date","")}</span>',unsafe_allow_html=True)
                    if col2.button("열기",key=f"sr_e_{r['id']}"):
                        try: st.session_state.cal_prefill_date=date.fromisoformat(r.get("date",""))
                        except: st.session_state.cal_prefill_date=today_kst()
                        st.session_state.current_page="📅 Calendar"; st.rerun()
        else:
            st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">🔍</div><p style="color:{D["text3"]}">결과 없음</p></div>',unsafe_allow_html=True)

# ===== SETTINGS =====
elif page=="⚙️ Settings":
    section("Settings")
    tabs_s=st.tabs(["프로필","API 키","AI 엔진","목표&습관","캘린더 라벨","템플릿","AI 프롬프트","통계"])

    with tabs_s[0]:
        st.markdown(f"<div class='pa-section-header'>프로필</div>",unsafe_allow_html=True)
        nn=st.text_input("이름",value=dname,key="sn")
        if st.button("업데이트",type="primary"):
            if DB: update_profile(uid,display_name=nn); st.session_state.user["display_name"]=nn; st.success("업데이트됨"); st.rerun()
        st.markdown("---")
        st.markdown(f"<div class='pa-section-header'>비밀번호 변경</div>",unsafe_allow_html=True)
        cur_pw=st.text_input("현재 비밀번호",type="password",key="cur_pw")
        new_pw=st.text_input("새 비밀번호",type="password",key="new_pw"); new_pw2=st.text_input("새 비밀번호 확인",type="password",key="new_pw2")
        if st.button("변경",key="chg_pw"):
            if new_pw!=new_pw2: st.error("비밀번호 불일치")
            elif not cur_pw: st.error("현재 비밀번호 입력")
            elif DB:
                import hashlib
                u,err=login_user(user.get("email",""),cur_pw)
                if u: update_profile(uid,password_hash=hashlib.sha256(new_pw.encode()).hexdigest()); st.success("변경됨!")
                else: st.error("현재 비밀번호 틀림")

    with tabs_s[1]:
        st.markdown(f"<div class='pa-section-header'>API 키</div>",unsafe_allow_html=True)
        gk=st.text_input("Gemini API Key",value=st.session_state.gemini_api_key,type="password",key="sgk")
        ck=st.text_input("Claude API Key",value=st.session_state.claude_api_key,type="password",key="sck")
        if st.button("저장",type="primary"):
            st.session_state.gemini_api_key=gk; st.session_state.claude_api_key=ck; st.success("저장됨")
        st.caption("영구 저장: Streamlit Secrets에 GEMINI_API_KEY 추가")
        st.markdown("---")
        st.markdown(f"<div class='pa-section-header'>Google Calendar</div>",unsafe_allow_html=True)
        st.caption("Secrets에 추가 필요: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI")
        st.code("""GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "your-secret"
REDIRECT_URI = "https://your-app.streamlit.app" """)

    with tabs_s[2]:
        st.session_state.ai_engine=st.radio("엔진",["auto","gemini","claude"],format_func=lambda x:{"auto":"Auto","gemini":"Gemini","claude":"Claude"}[x],horizontal=True)
        from ai_engine import GEMINI_MODELS,DEFAULT_MODEL
        current_model=st.session_state.get("gemini_model",DEFAULT_MODEL); model_keys=list(GEMINI_MODELS.keys())
        selected=st.selectbox("Gemini 모델",model_keys,format_func=lambda x:GEMINI_MODELS[x],index=model_keys.index(current_model) if current_model in model_keys else 0)
        st.session_state.gemini_model=selected

    with tabs_s[3]:
        st.markdown(f"<div class='pa-section-header'>목표 & 습관 관리</div>",unsafe_allow_html=True)
        hc1,hc2,hc3=st.columns([2,1,1])
        hn=hc1.text_input("이름"); hi=hc2.text_input("아이콘",value="✅",key="hi"); htype=hc3.selectbox("타입",["check","numeric"],format_func=lambda x:{"check":"체크","numeric":"수치"}[x],key="htype")
        htarget=1.0; hunit=""
        if htype=="numeric":
            hc4,hc5=st.columns(2); htarget=hc4.number_input("목표값",min_value=0.1,value=1.0,step=0.5,key="htarget"); hunit=hc5.text_input("단위",placeholder="km, 잔...",key="hunit")
        if st.button("추가",key="ah",type="primary"):
            if hn and DB: create_habit_v2(uid,hn,hi,htype,htarget,hunit); st.rerun()
        if DB:
            for h in get_habits(uid):
                c1,c2=st.columns([5,1]); c1.markdown(f"{h.get('icon','✅')} {h['name']}")
                if c2.button("삭제",key=f"dh_{h['id']}"): delete_habit(h["id"]); st.rerun()

    with tabs_s[4]:
        st.markdown(f"<div class='pa-section-header'>캘린더 라벨</div>",unsafe_allow_html=True)
        if DB:
            custom_labels=get_color_labels(uid)
            for color_key,hex_val in COLOR_PRESETS.items():
                current_label=custom_labels.get(color_key,{}).get("label",color_key.capitalize())
                ca,cb,cc=st.columns([1,3,1])
                ca.markdown(f'<div style="width:20px;height:20px;background:{hex_val};border-radius:50%;margin-top:8px"></div>',unsafe_allow_html=True)
                new_label=cb.text_input(f"",value=current_label,key=f"lbl_{color_key}",label_visibility="collapsed")
                if cc.button("저장",key=f"slbl_{color_key}"): set_color_label(uid,color_key,new_label,hex_val); st.success("저장됨"); st.rerun()

    with tabs_s[5]:
        st.markdown(f"<div class='pa-section-header'>기본 타입별 템플릿 편집</div>",unsafe_allow_html=True)
        with st.expander("기본 템플릿 수정"):
            st.caption("노트 타입 선택 시 자동 적용되는 기본 양식")
            default_tmps=get_default_templates()
            type_sel=st.selectbox("타입",["meeting","idea","project","daily"],format_func=lambda x:{"meeting":"Meeting","idea":"Idea","project":"Project","daily":"Daily"}[x],key="def_type_sel")
            existing_default=get_note_template(uid,type_sel) if DB else default_tmps.get(type_sel,"")
            new_default=st.text_area("내용",value=existing_default,height=200,key="def_tmpl_content",label_visibility="collapsed")
            if st.button("저장",key="save_default_tmpl",type="primary"):
                if DB:
                    all_tmps=get_templates(uid)
                    for t in all_tmps:
                        if t.get("note_type")==f"default_{type_sel}": delete_template(t["id"])
                    create_template(uid,f"기본_{type_sel}",new_default,note_type=f"default_{type_sel}",icon="📝")
                    st.success("저장됨!")
        st.markdown("---")
        st.markdown(f"<div class='pa-section-header'>커스텀 템플릿</div>",unsafe_allow_html=True)
        tn_t=st.text_input("이름",key="tn"); ti_t=st.text_input("아이콘",value="📄",key="ti"); tc_t=st.text_area("내용",height=150,key="tc",label_visibility="collapsed")
        if st.button("저장",key="st_btn",type="primary"):
            if tn_t and tc_t and DB: create_template(uid,tn_t,tc_t,icon=ti_t); st.success("저장됨"); st.rerun()
        if DB:
            for t in get_templates(uid):
                if t.get("note_type") not in ["report_template","ai_prompt","pomo_prompt"] and not t.get("note_type","").startswith("default_"):
                    c1,c2=st.columns([5,1]); c1.markdown(f"{t.get('icon','📄')} {t['name']}")
                    if c2.button("삭제",key=f"dt_{t['id']}"): delete_template(t["id"]); st.rerun()

    with tabs_s[6]:
        st.caption("노트 Summary/Expand 및 Pomodoro 분석용 커스텀 프롬프트")
        pt_cat=st.selectbox("카테고리",["Summary용","Expand용","Pomodoro 분석용"],key="pt_cat")
        pt_name=st.text_input("이름",key="pt_name"); pt_content=st.text_area("내용",height=120,key="pt_content",label_visibility="collapsed")
        cat_map={"Summary용":("ai_prompt","📝"),"Expand용":("ai_prompt","✨"),"Pomodoro 분석용":("pomo_prompt","🍅")}
        if st.button("저장",key="save_ai_p",type="primary"):
            if pt_name and pt_content and DB:
                nt_type,icon=cat_map[pt_cat]; create_template(uid,pt_name,pt_content,note_type=nt_type,icon=icon); st.success("저장됨"); st.rerun()
        if DB:
            for t in get_templates(uid):
                if t.get("note_type") in ["ai_prompt","pomo_prompt"]:
                    c1,c2=st.columns([5,1]); c1.markdown(f"{t.get('icon','🤖')} {t['name']}")
                    if c2.button("삭제",key=f"dap_{t['id']}"): delete_template(t["id"]); st.rerun()

    with tabs_s[7]:
        if DB:
            c1,c2,c3=st.columns(3)
            c1.metric("노트",len(get_notes(uid))); c2.metric("태스크",len(get_tasks(uid))); c3.metric("DB","연결됨")
            st.caption("다른 이메일로 가입 시 완전히 독립된 계정으로 사용 가능합니다.")

st.markdown(f"<div style='height:1px;background:{D['border']};margin:24px 0 8px'></div>",unsafe_allow_html=True)
st.markdown(f"<p style='font-size:11px;color:{D['text3']};text-align:center'>Personal Assistant v5.0</p>",unsafe_allow_html=True)
