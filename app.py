import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta, timezone
import json, calendar, math, re

st.set_page_config(page_title="Personal Assistant", page_icon="🚀", layout="wide", initial_sidebar_state="auto")

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
    "logged_in":False,"user":None,"current_page":"Dashboard","prev_page":"Dashboard",
    "gemini_api_key":"","claude_api_key":"","ai_engine":"auto",
    "editing_note":None,"editing_task":None,"theme":"light",
    "transcript":"","gemini_model":"gemini-2.5-flash",
    "show_related":False,"qc_preview":None,"qc_text":"",
    "temp_note_save":None,"temp_task_save":None,
    "ai_result":None,"ai_result_type":None,
    "time_reset_key":0,"cal_prefill_date":None,
    "md_preview_mode":False,"delete_confirm":None,
    "gcal_synced_at":None,
    "cal_year":today_kst().year,"cal_month":today_kst().month,
    "cal_selected_day":None,
    "dash_widget_order":["quote","reminders","habits","pinned","recent","tasks"],
    "dash_widgets":{"habits":True,"pinned":True,"recent":True,"tasks":True,"reminders":True,"quote":True},
    "chat_messages":[],
    "chat_model":"gemini",
    "share_view_uid":None,
    "sidebar_pages_order":None,
    "fab_rendered":False,
    "chat_input_key":0,
    "chat_unsaved":False,
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

# ===== CACHE WRAPPERS (속도 개선) =====
@st.cache_data(ttl=60)
def cached_get_notes(uid, search=None, folder_id=None):
    return get_notes(uid, search=search, folder_id=folder_id) if DB else []

@st.cache_data(ttl=60)
def cached_get_tasks(uid):
    return get_tasks(uid) if DB else []

@st.cache_data(ttl=60)
def cached_get_habits(uid):
    return get_habits(uid) if DB else []

@st.cache_data(ttl=120)
def cached_get_events(uid, start, end):
    return get_events(uid, start, end) if DB else []

def invalidate_cache():
    cached_get_notes.clear()
    cached_get_tasks.clear()
    cached_get_habits.clear()
    cached_get_events.clear()

# ===== iPhone Safari LocalStorage =====
ls_html = """<script>
(function(){
  var uid=localStorage.getItem('pa_uid');
  if(uid){var p=new URLSearchParams(window.location.search);if(!p.get('uid')){p.set('uid',uid);window.history.replaceState({},'',window.location.pathname+'?'+p.toString());window.location.reload();}}
  var theme=localStorage.getItem('pa_theme');
  if(theme){window.parent.postMessage({type:'restore_theme',theme:theme},'*');}
  window.addEventListener('message',function(e){
    if(e.data&&e.data.type==='store_uid'){localStorage.setItem('pa_uid',e.data.uid);}
    else if(e.data&&e.data.type==='clear_uid'){localStorage.removeItem('pa_uid');}
  });
})();
</script>"""
components.html(ls_html, height=0)

# ===== 로그인 유지 =====
if not st.session_state.logged_in and DB:
    uid_param = st.query_params.get("uid","")
    if uid_param:
        restored = get_user_by_id(uid_param)
        if restored:
            st.session_state.logged_in=True
            st.session_state.user=restored
            saved_theme = restored.get("theme","light")
            if saved_theme in ["light","dark"]:
                st.session_state.theme = saved_theme

# ===== Google OAuth =====
oauth_code = st.query_params.get("code","")
if oauth_code and GCAL and DB:
    if not st.session_state.get("gcal_code_processed"):
        _uid = None
        if st.session_state.logged_in and st.session_state.get("user"):
            _uid = st.session_state.user["id"]
        elif st.session_state.get("pre_oauth_uid"):
            _uid = st.session_state["pre_oauth_uid"]
            restored = get_user_by_id(_uid)
            if restored:
                st.session_state.logged_in=True
                st.session_state.user=restored
        if _uid:
            token_data = exchange_code_for_token(oauth_code)
            if token_data:
                expiry=(now_kst()+timedelta(seconds=token_data.get("expires_in",3600))).isoformat()
                save_google_tokens(_uid,token_data.get("access_token"),token_data.get("refresh_token",""),expiry)
                st.session_state["gcal_code_processed"]=True
                st.session_state.pop("pre_oauth_uid",None)
                st.query_params.clear()
                st.query_params["uid"]=str(_uid)
                st.rerun()

# ===== DESIGN SYSTEM =====
th = st.session_state.theme
D = {
    "light":{
        "bg":"#FFFFFF","surface":"#F7F6F3","surface2":"#EFEDE8",
        "border":"#E9E9E7","border2":"#D3D1CB",
        "text":"#37352F","text2":"#787774","text3":"#AEACAA",
        "accent":"#818CF8","accent_h":"#6D5FD8",
        "success":"#059669","warning":"#D97706","danger":"#DC2626",
        "sidebar":"#F7F6F3","input_bg":"#FFFFFF",
        "placeholder":"#AEACAA",
    },
    "dark":{
        "bg":"#191919","surface":"#252525","surface2":"#2F2F2F",
        "border":"#373737","border2":"#474747",
        "text":"#CFCFCF","text2":"#9B9B9B","text3":"#606060",
        "accent":"#818CF8","accent_h":"#6D5FD8",
        "success":"#10B981","warning":"#F59E0B","danger":"#DC2626",
        "sidebar":"#202020","input_bg":"#252525",
        "placeholder":"#555555",
    }
}[th]

# ===== CSS (캐시 최적화 — 문자열 재생성 방지) =====
@st.cache_data(max_entries=2)
def _build_css(theme):
    d = {
        "light":{
            "bg":"#FFFFFF","surface":"#F7F6F3","surface2":"#EFEDE8",
            "border":"#E9E9E7","border2":"#D3D1CB",
            "text":"#37352F","text2":"#787774","text3":"#AEACAA",
            "accent":"#818CF8","accent_h":"#6D5FD8",
            "success":"#059669","warning":"#D97706","danger":"#DC2626",
            "sidebar":"#F7F6F3","input_bg":"#FFFFFF","placeholder":"#AEACAA",
        },
        "dark":{
            "bg":"#191919","surface":"#252525","surface2":"#2F2F2F",
            "border":"#373737","border2":"#474747",
            "text":"#CFCFCF","text2":"#9B9B9B","text3":"#606060",
            "accent":"#818CF8","accent_h":"#6D5FD8",
            "success":"#10B981","warning":"#F59E0B","danger":"#DC2626",
            "sidebar":"#202020","input_bg":"#252525","placeholder":"#555555",
        }
    }[theme]
    return f"""<style>
*, *::before, *::after {{ box-sizing: border-box; }}
.stApp {{ background:{d['bg']} !important; font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif !important; }}

/* ✅ FIX 1: 헤더 투명화 (완전 숨김 제거 → 사이드바 버튼 살림) */
#MainMenu, footer {{ display:none !important; }}
header[data-testid="stHeader"] {{ visibility:hidden !important; }}
.stDeployButton {{ display:none !important; }}
[data-testid="stToolbar"] {{ display:none !important; }}
[data-testid="stSidebarCollapsedControl"] {{ 
    display:flex !important; opacity:1 !important; z-index:9999 !important;
    position:fixed !important; top:8px !important; left:8px !important;
    background:{d['surface']} !important; border:1px solid {d['border']} !important;
    border-radius:8px !important; padding:4px !important;
    box-shadow:0 2px 8px rgba(0,0,0,0.12) !important;
}}
[data-testid="stSidebarCollapsedControl"] button {{ color:{d['text']} !important; }}

.stApp p, .stApp span, .stApp div, .stApp label {{ color:{d['text']}; font-size:14px; line-height:1.6; }}
h1,h2,h3,h4 {{ color:{d['text']} !important; font-weight:600 !important; letter-spacing:-0.02em; }}
h2 {{ font-size:1.4rem !important; margin-bottom:16px !important; }}
h3 {{ font-size:1.05rem !important; }}
section[data-testid="stSidebar"] {{ background:{d['sidebar']} !important; border-right:1px solid {d['border']} !important; }}
section[data-testid="stSidebar"] > div {{ background:{d['sidebar']} !important; padding-top:0 !important; }}
section[data-testid="stSidebar"] p {{ color:{d['text']} !important; }}
section[data-testid="stSidebar"] span {{ color:{d['text']} !important; }}
section[data-testid="stSidebar"] div {{ color:{d['text']} !important; }}
section[data-testid="stSidebar"] label {{ color:{d['text']} !important; }}
section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {{
    display:flex; flex-direction:column; gap:1px;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label {{
    font-size:14px !important; color:{d['text2']} !important;
    padding:5px 10px !important; border-radius:6px !important;
    cursor:pointer !important; transition:background 0.1s !important;
    display:flex !important; align-items:center !important;
    background:transparent !important; width:100% !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {{
    background:{d['surface2']} !important; color:{d['text']} !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has([aria-checked="true"]) {{
    background:{d['surface2']} !important; color:{d['text']} !important; font-weight:500 !important;
}}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {{
    display:none !important;
}}
.stTextInput input, .stTextArea textarea, .stNumberInput input {{
    background:{d['input_bg']} !important; color:{d['text']} !important;
    border:1px solid {d['border']} !important; border-radius:8px !important; font-size:14px !important;
}}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {{
    color:{d['text3']} !important; opacity:0.75 !important; font-style:italic;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color:{d['accent']} !important;
    box-shadow:0 0 0 3px {d['accent']}25 !important; outline:none !important;
}}
.stSelectbox > div > div {{
    background:{d['input_bg']} !important; color:{d['text']} !important;
    border:1px solid {d['border']} !important; border-radius:8px !important;
}}
.stSelectbox svg {{ fill:{d['text2']} !important; }}
[data-baseweb="select"] [data-testid="stMarkdownContainer"] p {{ color:{d['text']} !important; }}
[data-baseweb="popover"] {{ background:{d['surface']} !important; border:1px solid {d['border']} !important; }}
[data-baseweb="menu"] {{ background:{d['surface']} !important; }}
[role="option"] {{ background:{d['surface']} !important; color:{d['text']} !important; }}
[role="option"]:hover {{ background:{d['surface2']} !important; }}
.stButton > button {{
    border-radius:6px !important; font-size:13.5px !important; font-weight:500 !important;
    padding:5px 14px !important; border:1px solid {d['border']} !important;
    background:{d['surface']} !important; color:{d['text2']} !important;
    transition:all 0.12s !important; box-shadow:none !important; line-height:1.5 !important;
}}
.stButton > button:hover {{
    background:{d['surface2']} !important; border-color:{d['border2']} !important; color:{d['text']} !important;
}}
.stButton > button[kind="primary"], button[kind="primary"] {{
    background:{d['accent']} !important; color:#FFFFFF !important;
    border:1px solid {d['accent']} !important; font-weight:600 !important;
}}
.stButton > button[kind="primary"]:hover {{
    background:{d['accent_h']} !important; color:#FFFFFF !important; border-color:{d['accent_h']} !important;
}}
[data-testid="stButton"] button[kind="primary"] *, [data-testid="stButton"] button[kind="primary"] p,
[data-testid="stButton"] button[kind="primary"] span {{ color:#FFFFFF !important; }}
div[data-testid="stMetric"] {{
    background:{d['surface']} !important; border:1px solid {d['border']} !important;
    border-radius:12px !important; padding:16px !important; cursor:pointer; transition:border-color 0.15s;
}}
div[data-testid="stMetric"]:hover {{ border-color:{d['accent']} !important; }}
div[data-testid="stMetricValue"] {{ color:{d['text']} !important; font-size:1.8rem !important; font-weight:700 !important; }}
div[data-testid="stMetricLabel"] {{ color:{d['text2']} !important; font-size:12px !important; text-transform:uppercase; letter-spacing:0.05em; }}
div[data-baseweb="tab-list"] {{ background:transparent !important; border-bottom:1px solid {d['border']} !important; gap:0 !important; }}
button[data-baseweb="tab"] {{ color:{d['text2']} !important; font-size:13.5px !important; font-weight:500 !important; padding:8px 16px !important; background:transparent !important; border:none !important; border-bottom:2px solid transparent !important; }}
button[data-baseweb="tab"]:hover {{ color:{d['text']} !important; background:{d['surface']} !important; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color:{d['accent']} !important; border-bottom:2px solid {d['accent']} !important; }}
div[data-testid="stExpander"] {{ border:1px solid {d['border']} !important; border-radius:10px !important; background:{d['surface']} !important; overflow:hidden; }}
div[data-testid="stExpander"] summary {{ color:{d['text']} !important; font-weight:500 !important; background:{d['surface']} !important; }}
div[data-testid="stExpander"] summary:hover {{ background:{d['surface2']} !important; }}
div[data-testid="stInfo"] {{ background:{d['accent']}15 !important; border:1px solid {d['accent']}35 !important; border-radius:8px !important; color:{d['text']} !important; }}
div[data-testid="stInfo"] p {{ color:{d['text']} !important; }}
div[data-testid="stSuccess"] {{ background:{d['success']}15 !important; border:1px solid {d['success']}35 !important; border-radius:8px !important; }}
div[data-testid="stSuccess"] p {{ color:{d['text']} !important; }}
div[data-testid="stWarning"] {{ background:{d['warning']}15 !important; border:1px solid {d['warning']}35 !important; border-radius:8px !important; }}
div[data-testid="stWarning"] p {{ color:{d['text']} !important; }}
div[data-testid="stError"] {{ background:{d['danger']}15 !important; border:1px solid {d['danger']}35 !important; border-radius:8px !important; }}
div[data-testid="stError"] p {{ color:{d['text']} !important; }}
div[data-testid="stProgressBar"] > div {{ background:{d['surface2']} !important; border-radius:99px !important; }}
div[data-testid="stProgressBar"] > div > div {{ background:{d['accent']} !important; border-radius:99px !important; }}
div[data-testid="stCheckbox"] label {{ color:{d['text']} !important; }}
div[data-testid="stRadio"] label {{ color:{d['text']} !important; }}
div[data-testid="stToggle"] label {{ color:{d['text']} !important; }}
hr {{ border:none !important; border-top:1px solid {d['border']} !important; margin:16px 0 !important; }}
code {{ background:{d['surface2']} !important; color:{d['accent']} !important; border-radius:4px !important; padding:1px 6px !important; font-size:12px !important; }}
div[data-testid="stFileUploader"] {{ background:{d['surface']} !important; border:1px dashed {d['border2']} !important; border-radius:10px !important; }}
div[data-testid="stFileUploader"] p {{ color:{d['text2']} !important; }}
.stDateInput input {{ background:{d['input_bg']} !important; color:{d['text']} !important; border:1px solid {d['border']} !important; border-radius:8px !important; }}
.stTimeInput input {{ background:{d['input_bg']} !important; color:{d['text']} !important; border:1px solid {d['border']} !important; border-radius:8px !important; }}
div[data-testid="stNumberInput"] input {{ background:{d['input_bg']} !important; color:{d['text']} !important; }}
div[data-testid="stNumberInput"] button {{ background:{d['surface2']} !important; color:{d['text']} !important; border-color:{d['border']} !important; }}
@media(max-width:768px){{
  [data-testid="stHorizontalBlock"]>div{{flex:100%!important;max-width:100%!important}}
  h2{{font-size:1.2rem!important}}
  .stApp p{{font-size:13px}}
}}
div[data-baseweb="radio"] div {{ background:{d['surface']} !important; border-color:{d['border']} !important; }}
div[data-baseweb="radio"] div[data-checked="true"] {{ background:{d['accent']} !important; border-color:{d['accent']} !important; }}
div[data-baseweb="checkbox"] div {{ background:{d['surface']} !important; border-color:{d['border']} !important; }}
div[data-baseweb="checkbox"] div[data-checked="true"] {{ background:{d['accent']} !important; border-color:{d['accent']} !important; }}
div[data-testid="stToggle"] {{ background:{d['surface']} !important; }}
div[data-testid="stToggle"] > div {{ background:{d['surface2']} !important; }}
div[data-baseweb="tag"] {{ background:{d['accent']}30 !important; color:{d['text']} !important; }}
div[data-testid="stDateInput"] input {{ background:{d['input_bg']} !important; color:{d['text']} !important; border-color:{d['border']} !important; }}
div[data-testid="stTimeInput"] input {{ background:{d['input_bg']} !important; color:{d['text']} !important; border-color:{d['border']} !important; }}
div[data-testid="stDateInput"] > div {{ background:{d['input_bg']} !important; }}
div[data-testid="stTimeInput"] > div {{ background:{d['input_bg']} !important; }}
[data-baseweb="calendar"] {{ background:{d['surface']} !important; color:{d['text']} !important; }}
[data-baseweb="calendar"] * {{ color:{d['text']} !important; }}
[data-baseweb="calendar"] button {{ background:{d['surface']} !important; color:{d['text']} !important; }}
div[data-testid="stSlider"] div {{ background:{d['surface2']} !important; }}
div[data-testid="stSlider"] div[role="slider"] {{ background:{d['accent']} !important; border-color:{d['accent']} !important; }}
::-webkit-scrollbar {{ width:6px; height:6px; }}
::-webkit-scrollbar-track {{ background:{d['surface']} !important; }}
::-webkit-scrollbar-thumb {{ background:{d['border2']} !important; border-radius:3px; }}
div[data-testid="stMarkdownContainer"] {{ background:transparent !important; }}
div[data-testid="stDownloadButton"] button {{ background:{d['surface']} !important; color:{d['text']} !important; border-color:{d['border']} !important; }}
div[data-testid="stNumberInput"] {{ background:transparent !important; }}
div[data-testid="stNumberInput"] > div {{ background:{d['input_bg']} !important; border-color:{d['border']} !important; border-radius:8px; }}
.pa-logo {{ font-size:1.6rem; font-weight:700; color:{d['text']}; letter-spacing:-0.03em; padding:20px 0 2px; cursor:pointer; transition:opacity 0.15s; font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif; line-height:1.2; }}
.pa-logo:hover {{ opacity:0.7; }}
.pa-logo-sub {{ font-size:11px; color:{d['text3']}; letter-spacing:0.04em; text-transform:uppercase; margin-top:2px; padding-bottom:12px; }}
.pa-section {{ font-size:11px; font-weight:600; color:{d['text3']}; letter-spacing:0.06em; text-transform:uppercase; margin:16px 0 6px; padding:0 2px; }}
.pa-card {{ background:{d['surface']}; border:1px solid {d['border']}; border-radius:12px; padding:14px 16px; margin:6px 0; }}
.pa-breadcrumb {{ font-size:12px; color:{d['text3']}; margin-bottom:10px; display:flex; align-items:center; gap:6px; }}
.pa-empty {{ text-align:center; padding:40px 20px; color:{d['text3']}; }}
.pa-empty-icon {{ font-size:2.5rem; margin-bottom:10px; }}
.pa-editing-badge {{ background:{d['warning']}15; border:1px solid {d['warning']}40; border-radius:8px; padding:8px 14px; margin-bottom:12px; font-size:13px; color:{d['text']}; }}
.pa-quote {{ background:linear-gradient(135deg,{d['accent']}18,{d['surface']}); border-left:3px solid {d['accent']}; border-radius:0 12px 12px 0; padding:16px 20px; margin:16px 0; }}
.pa-quote-text {{ font-size:1.05rem; font-weight:500; color:{d['text']}; line-height:1.6; font-style:italic; }}
.pa-quote-ref {{ font-size:12px; color:{d['text3']}; margin-top:6px; }}
.cal-event-pill {{ font-size:10px; font-weight:500; padding:1px 5px; border-radius:3px; margin:1px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer; }}

/* ✅ FIX 4: AI Chat 말풍선 가독성 개선 (반투명 → 불투명 + 흰 글씨) */
.chat-container {{ display:flex; flex-direction:column; gap:12px; padding:8px 0; }}
.chat-user {{ display:flex; justify-content:flex-end; }}
.chat-ai {{ display:flex; justify-content:flex-start; gap:8px; align-items:flex-start; }}
.chat-bubble-user {{ background:{d['accent']}; color:#ffffff; padding:10px 14px; border-radius:18px 18px 4px 18px; font-size:14px; line-height:1.5; max-width:75%; border:none; font-weight:400; }}
.chat-bubble-ai {{ background:{d['surface']}; color:{d['text']}; padding:10px 14px; border-radius:18px 18px 18px 4px; font-size:14px; line-height:1.5; max-width:75%; border:1px solid {d['border']}; }}
.chat-avatar {{ width:28px; height:28px; border-radius:50%; background:{d['accent']}20; display:flex; align-items:center; justify-content:center; font-size:13px; flex-shrink:0; margin-top:2px; }}

/* ✅ FIX 3: 로고 클릭 영역 오버레이 */
.home-btn-wrap {{ position:relative; margin-top:-76px; height:76px; z-index:5; }}
.home-btn-wrap button {{ opacity:0 !important; width:100% !important; height:76px !important; padding:0 !important; margin:0 !important; min-height:76px !important; border:none !important; background:transparent !important; cursor:pointer !important; position:absolute; top:0; left:0; }}
</style>"""

st.markdown(_build_css(th), unsafe_allow_html=True)

# ===== FAB (✅ FIX 2: 부모 DOM에 직접 주입 — iframe 스크롤 가려짐 해결) =====
if not st.session_state.fab_rendered:
    components.html(f"""<script>
(function(){{
    if(window.parent.document.getElementById('pa-fab-btn')) return;
    var s=window.parent.document.createElement('style');
    s.id='pa-fab-style';
    s.textContent='#pa-fab-btn{{position:fixed;top:14px;left:14px;z-index:99999;width:44px;height:44px;border-radius:50%;background:{D["accent"]};color:#fff;border:none;font-size:20px;cursor:pointer;box-shadow:0 4px 16px rgba(79,70,229,0.35);transition:transform .15s;display:none;align-items:center;justify-content:center;line-height:1}}#pa-fab-btn:hover{{transform:scale(1.1)}}@media(max-width:768px){{#pa-fab-btn{{display:flex!important}}}}';
    window.parent.document.head.appendChild(s);
    var b=window.parent.document.createElement('button');
    b.id='pa-fab-btn'; b.title='메뉴'; b.innerHTML='☰';
    b.onclick=function(){{
        var sb=window.parent.document.querySelector('[data-testid="stSidebarCollapsedControl"] button') ||
               window.parent.document.querySelector('[data-testid="stSidebarCollapseButton"]');
        if(sb) sb.click();
    }};
    window.parent.document.body.appendChild(b);
}})();
</script>""", height=0)
    st.session_state.fab_rendered = True

# ===== CONSTANTS =====
COLOR_PRESETS={"blue":"#3B82F6","red":"#EF4444","green":"#22C55E","purple":"#8B5CF6",
               "orange":"#F97316","pink":"#EC4899","teal":"#14B8A6","yellow":"#EAB308",
               "gray":"#6B7280","indigo":"#6366F1"}
COLOR_DOTS={"blue":"🔵","red":"🔴","green":"🟢","purple":"🟣","orange":"🟠",
            "pink":"🩷","teal":"🩵","yellow":"🟡","gray":"⚫","indigo":"🔷"}
PRIO_COLORS={"high":"#F97316","medium":"#F59E0B","low":"#10B981"}
PRIO_ICONS={"high":"●","medium":"●","low":"●"}
PRIO_LABELS={"high":"High","medium":"Medium","low":"Low"}

# ===== DEFAULT PAGES ORDER =====
DEFAULT_PAGES = [
    "AI Chat","Dashboard","Calendar","Tasks","Notes",
    "Transcription","Web Clipper","목표 & 습관","Pomodoro",
    "Search","Statistics","AI Content","Economy","Email","Settings"
]

def get_pages():
    custom = st.session_state.get("sidebar_pages_order")
    if custom and isinstance(custom, list) and len(custom) == len(DEFAULT_PAGES):
        return custom
    return DEFAULT_PAGES

def get_label(ck,cl): return cl.get(ck,{}).get("label",ck.capitalize()) if cl and ck in cl else ck.capitalize()
def get_group(t):
    p=t.get("project","") or ""
    if p.lower()=="personal": return "personal"
    if p: return "project"
    return "general"
def clear_nc():
    for k in ["nc","nt","ntags","nt_sel"]:
        if k in st.session_state: del st.session_state[k]
def clear_ai():
    st.session_state.ai_result=None; st.session_state.ai_result_type=None; st.session_state.md_preview_mode=False
def relative_date(s):
    if not s: return ""
    try:
        d=date.fromisoformat(s[:10]); diff=(today_kst()-d).days
        if diff==0: return "오늘"
        if diff==1: return "어제"
        if diff<7: return f"{diff}일 전"
        return f"{d.month}월 {d.day}일"
    except: return s[:10]

def get_default_templates():
    return {
        "meeting":"## Meeting\n- Date: \n- Attendees: \n\n## Agenda\n1. \n\n## Discussion\n\n## Decisions\n\n## Action Items\n- [ ] \n\n## Next Steps\n",
        "idea":"## Idea\n\n### Core Concept\n\n### Background\n\n### Expected Impact\n\n### Action Plan\n1. ",
        "project":"## Project\n- Start: \n- Deadline: \n- Status: \n\n## Goals\n1. \n\n## Tasks\n- [ ] \n\n## Notes\n\n## Resources\n",
        "daily":f"# {today_kst().strftime('%Y-%m-%d %A')}\n\n## 오늘의 메모\n\n\n## To Do\n- [ ] \n\n## 아이디어\n\n",
        "note":"",
    }

def get_note_template(uid, note_type):
    if DB:
        try:
            tmps=get_templates(uid)
            for t in tmps:
                if t.get("note_type")==f"default_{note_type}": return t["content"]
        except: pass
    return get_default_templates().get(note_type,"")

def get_avatar_url(uid):
    cache_key = f"avatar_url_{uid}"
    if st.session_state.get(cache_key): return st.session_state[cache_key]
    try:
        sb=get_sb()
        if not sb: return None
        files=sb.storage.from_("avatars").list(uid)
        if files and len(files)>0:
            fname=files[0]["name"]
            url=sb.storage.from_("avatars").get_public_url(f"{uid}/{fname}")
            st.session_state[cache_key] = url
            return url
    except: pass
    return None

def upload_avatar(uid, file_bytes, file_type):
    try:
        sb=get_sb()
        if not sb: return False
        ext={"image/jpeg":"jpg","image/png":"png","image/gif":"gif","image/webp":"webp"}.get(file_type,"jpg")
        path=f"{uid}/avatar.{ext}"
        try: sb.storage.from_("avatars").remove([f"{uid}/avatar.jpg",f"{uid}/avatar.png",f"{uid}/avatar.webp"])
        except: pass
        sb.storage.from_("avatars").upload(path, file_bytes, {"content-type":file_type,"upsert":"true"})
        cache_key = f"avatar_url_{uid}"
        if cache_key in st.session_state: del st.session_state[cache_key]
        return True
    except: return False

def get_daily_quote(uid, quote_type="motivational"):
    today_str=str(today_kst())
    cache_key=f"quote_{quote_type}_{today_str}"
    if st.session_state.get(cache_key): return st.session_state[cache_key]
    if DB:
        try:
            u=get_user_by_id(uid)
            if u:
                settings_str=u.get("settings") or "{}"
                us=json.loads(settings_str) if isinstance(settings_str,str) else (settings_str or {})
                db_cache_key=f"quote_cache_{quote_type}_{today_str}"
                if us.get(db_cache_key):
                    st.session_state[cache_key]=us[db_cache_key]
                    return us[db_cache_key]
        except: pass
    try:
        prompts={
            "bible":"오늘 날짜 기준으로 개역개정 성경에서 힘이 되는 구절 하나를 알려줘. 형식: 구절 내용\n(책 장:절) 으로만 답해줘.",
            "motivational":"오늘 하루를 위한 세계적으로 유명한 동기부여 명언 하나를 한국어로 번역해서 알려줘. 형식: 명언 내용\n— 저자 이름 으로만 답해줘.",
        }
        result=get_ai(prompts.get(quote_type,prompts["motivational"]),st.session_state.ai_engine,"summary")
        st.session_state[cache_key]=result
        if DB:
            try:
                u=get_user_by_id(uid)
                settings_str=u.get("settings") or "{}"
                us=json.loads(settings_str) if isinstance(settings_str,str) else (settings_str or {})
                us[f"quote_cache_{quote_type}_{today_str}"]=result
                update_profile(uid,settings=json.dumps(us,ensure_ascii=False))
            except: pass
        return result
    except: return ""

# ===== SHARING =====
def get_shared_users(uid):
    q = _q("shared_access") if DB else None
    if not q: return []
    try: return q.select("*").eq("owner_id", uid).execute().data or []
    except: return []

def add_shared_access(owner_id, shared_email, permission="view"):
    if not DB: return False
    try:
        sb = get_sb()
        r = sb.table("profiles").select("id,display_name").eq("email", shared_email).execute()
        if not r.data: return None, "해당 이메일 사용자를 찾을 수 없습니다"
        shared_uid = r.data[0]["id"]
        shared_name = r.data[0].get("display_name", shared_email)
        sb.table("shared_access").upsert({
            "owner_id": owner_id, "shared_with_id": shared_uid,
            "shared_email": shared_email, "permission": permission
        }).execute()
        return shared_name, None
    except Exception as e: return None, str(e)

def remove_shared_access(owner_id, shared_with_id):
    if not DB: return False
    try: get_sb().table("shared_access").delete().eq("owner_id", owner_id).eq("shared_with_id", shared_with_id).execute(); return True
    except: return False

def get_my_accesses(uid):
    if not DB: return []
    try: return get_sb().table("shared_access").select("owner_id,permission,profiles(display_name,email)").eq("shared_with_id", uid).execute().data or []
    except: return []

# ===== EMOJI PICKER =====
EMOJI_CATEGORIES = {
    "자주 쓰는": ["✅","📝","💡","📅","🎯","🔥","⭐","❤️","👍","🙏","💪","🎉","📌","🔔","⚡","🌟","✨","🚀","💰","📊"],
    "감정/활동": ["😊","😎","🤔","😅","🥳","💻","📚","🏃","🧘","🎵","🎨","🍎","☕","🌙","☀️","🌈","❄️","🔑","🎁","🏆"],
    "업무/생산성": ["📋","📂","🗂️","📊","📈","📉","🖊️","📧","📞","💬","🔍","🔎","⚙️","🛠️","📐","💾","🖥️","📱","🌐","🔗"],
    "건강/운동": ["🏋️","🚴","🧗","⚽","🏀","🎾","🏊","🤸","🥗","💊","🩺","❤️‍🔥","🧠","🦷","👁️","💤","🛏️","🥤","🍵","🥦"],
}

def emoji_picker(key, current=""):
    with st.expander(f"{current or '😊'} 이모지 선택", expanded=False):
        for cat, emojis in EMOJI_CATEGORIES.items():
            st.caption(cat)
            cols = st.columns(10)
            for i, em in enumerate(emojis):
                if cols[i%10].button(em, key=f"ep_{key}_{cat}_{i}"):
                    return em
    return current

# ===== 임시저장 =====
cpn=st.session_state.current_page; ppn=st.session_state.get("prev_page",cpn)
if ppn=="Notes" and cpn!="Notes":
    if st.session_state.get("editing_note"):
        n=st.session_state.editing_note
        st.session_state["temp_note_save"]={"note":n,"content":st.session_state.get("nc",n.get("content","")),"title":st.session_state.get("nt",n.get("title",""))}
        st.session_state.editing_note=None; clear_ai()
if ppn=="Tasks" and cpn!="Tasks":
    if st.session_state.get("editing_task"):
        st.session_state["temp_task_save"]=st.session_state.editing_task; st.session_state.editing_task=None
st.session_state.prev_page=cpn

# ===== SIDEBAR =====
with st.sidebar:
    if not st.session_state.logged_in:
        st.markdown(f'<div class="pa-logo">PA</div><div class="pa-logo-sub">Personal Assistant</div>',unsafe_allow_html=True)
        # ✅ FIX: label 경고 수정 (빈 문자열 → label_visibility="collapsed")
        tab=st.radio("메뉴선택",["Login","Sign Up"],horizontal=True,label_visibility="collapsed")
        if tab=="Login":
            em=st.text_input("이메일",key="le",placeholder="you@example.com")
            pw=st.text_input("비밀번호",type="password",key="lp",placeholder="••••••••")
            if st.button("로그인",use_container_width=True,type="primary"):
                if DB:
                    u,err=login_user(em,pw)
                    if u:
                        st.session_state.logged_in=True; st.session_state.user=u
                        st.query_params["uid"]=str(u["id"])
                        components.html(f"<script>window.parent.postMessage({{type:'store_uid',uid:'{u['id']}'}}, '*');localStorage.setItem('pa_theme','{u.get('theme','light')}');</script>",height=0)
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

        avatar_url=get_avatar_url(uid) if DB else None
        if avatar_url:
            st.markdown(f'''<div style="padding:20px 4px 6px;display:flex;align-items:center;gap:12px">
<img src="{avatar_url}" style="width:48px;height:48px;border-radius:50%;object-fit:cover;border:2px solid {D["border"]}">
<div>
<div style="font-size:1.4rem;font-weight:800;color:{D["text"]};letter-spacing:-0.03em;line-height:1.1">{dname.upper()}</div>
<div style="font-size:10px;color:{D["text3"]};letter-spacing:0.08em;text-transform:uppercase;margin-top:2px">Personal Assistant</div>
</div></div>''',unsafe_allow_html=True)
        else:
            st.markdown(f'''<div style="padding:20px 4px 6px">
<div style="font-size:1.8rem;font-weight:800;color:{D["text"]};letter-spacing:-0.04em;line-height:1">{dname.upper()}</div>
<div style="font-size:10px;color:{D["text3"]};letter-spacing:0.1em;text-transform:uppercase;margin-top:4px;margin-bottom:4px">Personal Assistant</div>
</div>''',unsafe_allow_html=True)

        # ✅ FIX 3: 로고 클릭 → 홈 이동 (투명 버튼이 로고 영역 오버레이)
        with st.container():
            if st.button("home",key="home_btn",use_container_width=True):
                st.session_state.current_page="Dashboard"; st.rerun()

        # Quick Capture
        st.markdown(f'<div class="pa-section">Quick Capture</div>',unsafe_allow_html=True)
        qtext=st.text_input("빠른입력",placeholder="무엇이든 입력...",label_visibility="collapsed",key="qi")
        if qtext:
            qc1,qc2=st.columns(2)
            if qc1.button("분류",use_container_width=True,key="qp"):
                if DB:
                    with st.spinner("..."): c=smart_classify(qtext); st.session_state.qc_preview=c; st.session_state.qc_text=qtext
            if qc2.button("저장",use_container_width=True,key="qs"):
                if DB: create_note(uid,qtext[:50],qtext); invalidate_cache(); st.success("저장됨"); st.rerun()
        if st.session_state.get("qc_preview"):
            c=st.session_state.qc_preview; ct=c.get("type","note")
            st.info(f"{'✅' if ct=='task' else '💰' if ct=='expense' else '📝'} {ct.upper()}: {c.get('title',qtext)[:30]}")
            cc1,cc2=st.columns(2)
            if cc1.button("확인",use_container_width=True,key="qcs"):
                if DB:
                    qt=st.session_state.get("qc_text","")
                    if ct=="task": create_task(uid,c.get("title",qt))
                    elif ct=="expense" and c.get("amount"): add_expense(uid,int(c["amount"]),c.get("category","기타"),qt)
                    else: create_note(uid,c.get("title",qt[:50]),qt)
                    invalidate_cache()
                    st.session_state.qc_preview=None; st.session_state.qc_text=""; st.rerun()
            if cc2.button("취소",use_container_width=True,key="qcx"): st.session_state.qc_preview=None; st.rerun()

        # Quick Search
        st.markdown(f'<div class="pa-section">Search</div>',unsafe_allow_html=True)
        qs_kw=st.text_input("검색",placeholder="🔍 노트, 태스크, 일정...",label_visibility="collapsed",key="qs_kw")
        if qs_kw and DB:
            qs_r=search_all(uid,qs_kw)
            if qs_r:
                for r in qs_r[:5]:
                    icon={"note":"📝","task":"✅","event":"📅"}.get(r["type"],"📄")
                    c1,c2=st.columns([3,1])
                    c1.caption(f"{icon} {r['title'][:18]}")
                    if c2.button("→",key=f"qs_{r['id']}"):
                        if r["type"]=="note":
                            all_n=cached_get_notes(uid); t=[n for n in all_n if n["id"]==r["id"]]
                            if t: st.session_state.editing_note=t[0]; clear_nc(); clear_ai(); st.session_state.current_page="Notes"
                        elif r["type"]=="task":
                            all_t=cached_get_tasks(uid); t=[x for x in all_t if x["id"]==r["id"]]
                            if t: st.session_state.editing_task=t[0]; st.session_state.current_page="Tasks"
                        elif r["type"]=="event":
                            try: st.session_state.cal_prefill_date=date.fromisoformat(r.get("date",""))
                            except: st.session_state.cal_prefill_date=today_kst()
                            st.session_state.current_page="Calendar"
                        st.rerun()
            else: st.caption("결과 없음")

        # Navigation
        st.markdown(f'<div class="pa-section">메뉴</div>',unsafe_allow_html=True)
        PAGES = get_pages()
        cur_idx = PAGES.index(st.session_state.current_page) if st.session_state.current_page in PAGES else 0
        new_page=st.radio("페이지",PAGES,label_visibility="collapsed",index=cur_idx)
        if new_page!=st.session_state.current_page:
            st.session_state.current_page=new_page
            if new_page=="Calendar": st.session_state.gcal_synced_at=None
            st.rerun()
        # #7: 같은 페이지(Notes) 재클릭 시 편집 화면 → 목록으로
        elif new_page=="Notes" and st.session_state.get("editing_note"):
            st.session_state.editing_note=None; clear_nc(); clear_ai(); st.rerun()

        st.markdown(f'<hr style="border-color:{D["border"]};margin:12px 0">',unsafe_allow_html=True)
        st.markdown(f'<style>.theme-toggle div[data-testid="stRadio"] > div{{flex-direction:row !important;gap:8px !important;}}</style>',unsafe_allow_html=True)
        st.markdown('<div class="theme-toggle">',unsafe_allow_html=True)
        tt=st.radio("테마",["☀️ Light","🌙 Dark"],horizontal=True,label_visibility="collapsed",index=0 if th=="light" else 1,key="theme_radio")
        st.markdown('</div>',unsafe_allow_html=True)
        new_theme="light" if "Light" in tt else "dark"
        if new_theme!=th:
            st.session_state.theme=new_theme
            if DB and st.session_state.logged_in:
                update_profile(st.session_state.user["id"],theme=new_theme)
                st.session_state.user["theme"]=new_theme
            components.html(f"<script>localStorage.setItem('pa_theme','{new_theme}');</script>",height=0)
            st.rerun()
        if st.button("로그아웃",use_container_width=True):
            st.query_params.clear()
            components.html("<script>window.parent.postMessage({type:'clear_uid'},'*');</script>",height=0)
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

if not st.session_state.logged_in:
    # 메인 영역 로그인 폼 — 사이드바 숨겨져도 항상 접근 가능
    st.markdown(f'''<div style="display:flex;flex-direction:column;align-items:center;padding-top:60px">
<div style="font-size:2.4rem;font-weight:800;color:{D["text"]};letter-spacing:-0.04em;margin-bottom:4px">Personal Assistant</div>
<p style="color:{D["text2"]};margin-bottom:32px;font-size:14px">Notes · Tasks · Calendar · AI</p>
</div>''', unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        st.markdown(f'<div style="background:{D["surface"]};border:1px solid {D["border"]};border-radius:16px;padding:28px 24px">',unsafe_allow_html=True)
        main_tab = st.radio("로그인탭", ["로그인", "회원가입"], horizontal=True, label_visibility="collapsed", key="main_login_tab")

        if main_tab == "로그인":
            m_em = st.text_input("이메일", key="m_le", placeholder="you@example.com")
            m_pw = st.text_input("비밀번호", type="password", key="m_lp", placeholder="••••••••")
            if st.button("로그인", use_container_width=True, type="primary", key="m_login_btn"):
                if DB:
                    u, err = login_user(m_em, m_pw)
                    if u:
                        st.session_state.logged_in = True
                        st.session_state.user = u
                        st.query_params["uid"] = str(u["id"])
                        components.html(f"<script>window.parent.postMessage({{type:'store_uid',uid:'{u['id']}'}}, '*');localStorage.setItem('pa_theme','{u.get('theme','light')}');</script>", height=0)
                        st.rerun()
                    else:
                        st.error(err)
                else:
                    st.session_state.logged_in = True
                    st.session_state.user = {"id": "demo", "email": m_em, "display_name": m_em.split("@")[0]}
                    st.rerun()
        else:
            m_nm = st.text_input("이름", key="m_rn", placeholder="홍길동")
            m_em2 = st.text_input("이메일", key="m_re", placeholder="you@example.com")
            m_pw2 = st.text_input("비밀번호", type="password", key="m_rp", placeholder="8자 이상")
            m_pw3 = st.text_input("비밀번호 확인", type="password", key="m_rp2", placeholder="••••••••")
            if st.button("회원가입", use_container_width=True, type="primary", key="m_reg_btn"):
                if m_pw2 != m_pw3:
                    st.error("비밀번호가 일치하지 않습니다")
                elif DB:
                    u, err = register_user(m_em2, m_pw2, m_nm)
                    if u:
                        st.success("가입 완료! 로그인해주세요.")
                    else:
                        st.error(err)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

user=st.session_state.user; uid=user["id"]; dname=user.get("display_name","User")
page=st.session_state.current_page

def section(title,sub=None):
    s=f'<div style="margin:0 0 20px"><h2 style="color:{D["text"]};margin:0">{title}</h2>'
    if sub: s+=f'<p style="color:{D["text2"]};font-size:13px;margin:4px 0 0">{sub}</p>'
    s+='</div>'; st.markdown(s,unsafe_allow_html=True)

# ===== AI CHAT =====
if page=="AI Chat":
    st.markdown(f'<div style="margin:0 0 12px;display:flex;align-items:center;justify-content:space-between"><h2 style="color:{D["text"]};margin:0">AI Chat</h2></div>',unsafe_allow_html=True)

    ctrl1,ctrl2,ctrl3=st.columns([2,1,1])
    chat_model_sel=ctrl1.radio("모델선택",["Gemini","Claude"],horizontal=True,label_visibility="collapsed",key="chat_model_sel")
    if ctrl2.button("새 대화",use_container_width=True):
        if st.session_state.get("chat_messages") and st.session_state.get("chat_unsaved",False):
            st.session_state["chat_new_confirm"]=True; st.rerun()
        else:
            st.session_state.chat_messages=[]; st.session_state.chat_input_key+=1; st.session_state.chat_unsaved=False; st.rerun()
    if st.session_state.get("chat_new_confirm"):
        st.warning("⚠️ 현재 대화가 저장되지 않았습니다. 새 대화를 시작하면 사라집니다.")
        cn1,cn2=st.columns(2)
        if cn1.button("저장 없이 시작",type="primary",use_container_width=True,key="cnf_ok"):
            st.session_state.chat_messages=[]; st.session_state.chat_input_key+=1
            st.session_state.chat_unsaved=False; st.session_state.chat_new_confirm=False; st.rerun()
        if cn2.button("취소",use_container_width=True,key="cnf_no"):
            st.session_state.chat_new_confirm=False; st.rerun()
    if ctrl3.button("노트 저장",use_container_width=True):
        st.session_state["chat_save_mode"]=True; st.rerun()

    msgs=st.session_state.get("chat_messages",[])

    chat_html='<div class="chat-container">'
    for msg in msgs:
        if msg["role"]=="user":
            content=msg["content"].replace("<","&lt;").replace(">","&gt;")
            chat_html+=f'<div class="chat-user"><div class="chat-bubble-user">{content}</div></div>'
        else:
            content=msg["content"].replace("<","&lt;").replace(">","&gt;")
            model_icon="G" if msg.get("model","gemini")=="gemini" else "C"
            chat_html+=f'<div class="chat-ai"><div class="chat-avatar">{model_icon}</div><div class="chat-bubble-ai">{content}</div></div>'
    chat_html+='</div>'
    if msgs:
        st.markdown(chat_html,unsafe_allow_html=True)
        st.markdown("")
    else:
        st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">🤖</div><p style="color:{D["text3"]}">AI와 대화를 시작해보세요<br><small>Gemini 또는 Claude 선택 후 메시지 입력</small></p></div>',unsafe_allow_html=True)

    if st.session_state.get("chat_save_mode") and msgs:
        sc1,sc2,sc3=st.columns([3,1,1])
        chat_title=sc1.text_input("노트제목",placeholder="노트 제목...",label_visibility="collapsed",key="chat_save_title")
        if sc2.button("저장",type="primary",use_container_width=True):
            if chat_title and DB:
                content2="\n\n".join([f"**{'나' if m['role']=='user' else 'AI'}**: {m['content']}" for m in msgs])
                create_note(uid,chat_title,content2,"note"); invalidate_cache()
                st.success("저장됨!"); st.session_state["chat_save_mode"]=False; st.session_state.chat_unsaved=False; st.rerun()
            elif not chat_title: st.warning("제목 입력")
        if sc3.button("취소",use_container_width=True): st.session_state["chat_save_mode"]=False; st.rerun()

    input_key=f"chat_input_{st.session_state.chat_input_key}"
    ci1,ci2=st.columns([5,1])
    user_input=ci1.text_input("메시지입력",placeholder="메시지 입력... (Enter 또는 전송)",label_visibility="collapsed",key=input_key)
    send_clicked=ci2.button("전송",type="primary",use_container_width=True)

    if send_clicked and user_input:
        msgs.append({"role":"user","content":user_input,"model":chat_model_sel.lower()})
        engine2="gemini" if chat_model_sel=="Gemini" else "claude"
        with st.spinner("답변 생성 중..."):
            ctx="\n".join([f"{'User' if m['role']=='user' else 'AI'}: {m['content']}" for m in msgs[-8:]])
            try: response=get_ai(f"대화 맥락:\n{ctx}\n\n위 대화에 자연스럽게 답해줘. 마크다운 형식 사용 가능.",engine2,"chat")
            except: response=get_ai(f"대화:\n{ctx}\n\n답해줘.","gemini","chat")
            msgs.append({"role":"assistant","content":response,"model":engine2})
        st.session_state.chat_messages=msgs
        st.session_state.chat_unsaved=True
        st.session_state.chat_input_key+=1
        st.rerun()

# ===== DASHBOARD =====
elif page=="Dashboard":
    col_t,col_c=st.columns([5,1])
    col_t.markdown(f'<h2 style="color:{D["text"]};margin:0">안녕하세요, {dname}님 👋</h2><p style="color:{D["text2"]};font-size:13px;margin:4px 0 0">{now_kst().strftime("%Y년 %m월 %d일 %A")}</p>',unsafe_allow_html=True)
    with col_c.expander("위젯"):
        dw=st.session_state.dash_widgets; order=st.session_state.dash_widget_order
        wlabels={"reminders":"리마인더","habits":"목표 & 습관","pinned":"핀","recent":"최근 노트","tasks":"오늘 할 일","quote":"오늘의 문구"}
        for i,wk in enumerate(order):
            w1,w2,w3=st.columns([4,1,1])
            dw[wk]=w1.checkbox(wlabels.get(wk,wk),value=dw.get(wk,True),key=f"dw_{wk}")
            if i>0 and w2.button("↑",key=f"up_{wk}"): order[i],order[i-1]=order[i-1],order[i]; st.session_state.dash_widget_order=order; st.rerun()
            if i<len(order)-1 and w3.button("↓",key=f"dn_{wk}"): order[i],order[i+1]=order[i+1],order[i]; st.session_state.dash_widget_order=order; st.rerun()
        st.session_state.dash_widgets=dw

    if DB:
        tasks=cached_get_tasks(uid)
        backlog=[t for t in tasks if t["status"]=="backlog"]
        todo=[t for t in tasks if t["status"]=="todo"]
        doing=[t for t in tasks if t["status"]=="doing"]
        done_t=[t for t in tasks if t["status"]=="done"]

        if dw.get("quote",True):
            user_data=user if user else {}
            settings_str=user_data.get("settings") or "{}"
            try: user_settings=json.loads(settings_str) if isinstance(settings_str,str) else (settings_str or {})
            except: user_settings={}
            qt=user_settings.get("quote_type","motivational")
            manual_q=user_settings.get("manual_quote","")
            if qt=="manual" and manual_q:
                st.markdown(f'<div class="pa-quote"><div class="pa-quote-text">"{manual_q}"</div></div>',unsafe_allow_html=True)
            elif qt in ["bible","motivational","both"] and qt!="none":
                for qt2 in (["bible","motivational"] if qt=="both" else [qt]):
                    q=get_daily_quote(uid,qt2)
                    if q:
                        lines2=q.strip().split("\n"); text2=lines2[0]; ref2=lines2[1] if len(lines2)>1 else ""
                        st.markdown(f'<div class="pa-quote"><div class="pa-quote-text">"{text2}"</div>{"<div class=pa-quote-ref>"+ref2+"</div>" if ref2 else ""}</div>',unsafe_allow_html=True)

        c1,c2,c3,c4=st.columns(4)
        c1.metric("Backlog",len(backlog)); c2.metric("To Do",len(todo))
        c3.metric("진행 중",len(doing)); c4.metric("완료",len(done_t))

        for wk in st.session_state.dash_widget_order:
            if wk=="quote": continue
            if not dw.get(wk,True): continue
            if wk=="reminders":
                upcoming=[t for t in todo+doing if t.get("due_date") and t["due_date"]<=str(today_kst()+timedelta(days=2))]
                if upcoming:
                    st.warning(f"마감 임박 {len(upcoming)}개")
                    for t in upcoming:
                        is_today=t["due_date"]==str(today_kst())
                        st.markdown(f"- **{t['title']}** — {'🔥 오늘!' if is_today else t['due_date']}")
            elif wk=="habits":
                st.markdown("---")
                st.markdown(f'<div class="pa-section">목표 & 습관</div>',unsafe_allow_html=True)
                habits=cached_get_habits(uid)
                if habits:
                    logs=get_habit_logs(uid,today_kst(),today_kst())
                    done_ids={l["habit_id"] for l in logs if l.get("completed")}
                    log_vals={l["habit_id"]:l.get("value",0) for l in logs}
                    cols=st.columns(min(len(habits),4))
                    for i,h in enumerate(habits):
                        with cols[i%min(len(habits),4)]:
                            if h.get("habit_type")=="numeric":
                                target=float(h.get("target_value",1)); unit=h.get("unit","")
                                cur=float(log_vals.get(h["id"],0))
                                st.markdown(f"**{h.get('icon','🎯')} {h['name']}**")
                                nv=st.number_input(f"/{target}{unit}",min_value=0.0,max_value=target*3,value=cur,step=0.5,key=f"hv_{h['id']}")
                                pct=min(nv/target,1.0) if target>0 else 0
                                st.progress(pct,text=f"{nv}/{target}{unit}")
                                dc=st.checkbox("완료",value=h["id"] in done_ids or pct>=1.0,key=f"hnc_{h['id']}")
                                if st.button("저장",key=f"hsv_{h['id']}",use_container_width=True): toggle_habit_value(h["id"],uid,nv if dc else 0)
                            else:
                                chk=st.checkbox(f"{h.get('icon','✅')} {h['name']}",value=h["id"] in done_ids,key=f"h_{h['id']}")
                                if chk!=(h["id"] in done_ids): toggle_habit(h["id"],uid)
                    ws_d=today_kst()-timedelta(days=today_kst().weekday())
                    wl=get_habit_logs(uid,ws_d,today_kst())
                    wc=len([l for l in wl if l.get("completed")]); wt=len(habits)*(today_kst().weekday()+1)
                    r=int(wc/wt*100) if wt>0 else 0
                    st.progress(r/100,text=f"이번 주 {r}%")
                else: st.caption("목표 & 습관 메뉴에서 추가하세요")
            elif wk=="recent":
                st.markdown("---"); st.markdown(f'<div class="pa-section">최근 노트</div>',unsafe_allow_html=True)
                notes=cached_get_notes(uid)[:5]
                if notes:
                    for n in notes:
                        c1,c2=st.columns([5,1])
                        c1.markdown(f'**{n["title"]}** <span style="color:{D["text3"]};font-size:11px">{relative_date(n.get("updated_at",""))}</span>',unsafe_allow_html=True)
                        if c2.button("열기",key=f"db_n_{n['id']}"): st.session_state.editing_note=n; clear_nc(); clear_ai(); st.session_state.current_page="Notes"; st.rerun()
                else: st.caption("아직 노트가 없습니다")
            elif wk=="tasks":
                st.markdown("---"); st.markdown(f'<div class="pa-section">오늘 할 일</div>',unsafe_allow_html=True)
                if todo:
                    for t in todo[:5]:
                        is_urgent=t.get("due_date")==str(today_kst())
                        st.markdown(f"{'🔥' if is_urgent else '·'} {t['title']}")
                else: st.caption("모든 할 일 완료! 🎉")

        st.markdown("---")
        bc1,bc2=st.columns(2)
        if bc1.button("Morning Briefing",type="primary",use_container_width=True):
            with st.spinner("..."): st.markdown(get_ai(f"오늘:{now_kst().strftime('%Y-%m-%d %A')}. 할일:{len(todo)}, 진행:{len(doing)}.\n간결한 아침 브리핑: 1)오늘 집중 2)팁 3)동기부여",st.session_state.ai_engine,"summary"))
        if bc2.button("Daily Review",use_container_width=True):
            with st.spinner("..."):
                tn=[n for n in cached_get_notes(uid) if n.get("updated_at","")[:10]==str(today_kst())]
                st.markdown(get_ai(f"오늘 노트:{len(tn)}개, 완료:{len(done_t)}개.\n회고: 1)한일 2)배운점 3)내일계획",st.session_state.ai_engine,"summary"))

# ===== CALENDAR =====
elif page=="Calendar":
    section("캘린더")
    if DB:
        gcal_tokens=get_google_tokens(uid)
        gcal_connected=gcal_tokens and gcal_tokens.get("refresh_token")
    else: gcal_connected=False

    gc1,gc2,gc3=st.columns([4,1,1])
    if gcal_connected:
        gc1.success("Google Calendar 연결됨 ✅")
        if gc2.button("연결 해제"): clear_google_tokens(uid); st.rerun()
        if GCAL:
            last=st.session_state.get("gcal_synced_at")
            elapsed=(now_kst()-last).total_seconds() if last else 999
            if elapsed<600: gc1.caption(f"동기화: {int(elapsed//60)}분 {int(elapsed%60)}초 전")
            force_sync=gc3.button("🔄 동기화",key="force_gcal_sync")
            if force_sync or elapsed>=600:
                with st.spinner("Google Calendar 동기화 중..."):
                    try:
                        gs=datetime.combine(today_kst().replace(day=1),datetime.min.time())
                        ge=gs+timedelta(days=60)
                        result=gcal_get_events(uid,gs,ge)
                        if isinstance(result,tuple): gevs,gcal_err=result
                        else: gevs,gcal_err=result,None
                        if gcal_err:
                            st.warning(f"Google Calendar 오류: {gcal_err}")
                        else:
                            existing=get_events(uid,gs,ge)
                            ex_ids={e.get("gcal_id") for e in existing if e.get("gcal_id")}
                            added=0
                            for ge2 in gevs:
                                p=parse_gcal_event(ge2)
                                if not p.get("gcal_id"): continue
                                if p["gcal_id"] not in ex_ids:
                                    try:
                                        s=p["start_time"]; e2=p["end_time"]
                                        if "T" in s:
                                            sdt=datetime.fromisoformat(s.replace("Z","+00:00"))
                                            if sdt.tzinfo: sdt=sdt.astimezone(KST).replace(tzinfo=None)
                                        else: sdt=datetime.combine(date.fromisoformat(s),datetime.min.time())
                                        if e2 and "T" in e2:
                                            edt=datetime.fromisoformat(e2.replace("Z","+00:00"))
                                            if edt.tzinfo: edt=edt.astimezone(KST).replace(tzinfo=None)
                                        elif e2: edt=datetime.combine(date.fromisoformat(e2),datetime.min.time())
                                        else: edt=sdt+timedelta(hours=1)
                                        r=create_event(uid,p["title"],sdt,edt,p.get("description",""),"indigo",p["gcal_id"],"google")
                                        if r: added+=1
                                    except: pass
                            st.session_state.gcal_synced_at=now_kst()
                            cached_get_events.clear()
                            if added>0: st.success(f"✅ {added}개 일정 추가됨"); st.rerun()
                            elif gevs: st.info(f"{len(gevs)}개 확인 (이미 동기화됨)")
                            else: st.info("해당 기간 Google Calendar 일정 없음")
                    except Exception as ex: st.warning(f"동기화 실패: {ex}")
    else:
        if GCAL:
            auth_url=build_auth_url()
            if auth_url:
                st.session_state["pre_oauth_uid"]=uid
                gc1.info("Google Calendar 연동 시 10분마다 자동 동기화됩니다")
                gc2.markdown(f'<a href="{auth_url}" target="_blank" style="display:inline-block;background:{D["accent"]};color:#fff;border-radius:8px;padding:8px 14px;font-size:13px;font-weight:600;text-decoration:none">Google 연결</a>',unsafe_allow_html=True)

    view=st.radio("뷰선택",["Monthly","Weekly","Daily","List"],horizontal=True,label_visibility="collapsed")
    custom_labels=get_color_labels(uid) if DB else {}
    prefill=st.session_state.get("cal_prefill_date") or today_kst()
    ds=get_default_event_time()
    de=(datetime.combine(today_kst(),ds)+timedelta(hours=1)).time()
    tkey=st.session_state.time_reset_key

    form_expanded = bool(st.session_state.get("cal_prefill_date"))
    with st.expander("➕ 새 일정 추가", expanded=form_expanded):
        et=st.text_input("제목",key="et",placeholder="일정 제목")
        dc1,dc2,dc3=st.columns([2,1,1])
        ed=dc1.date_input("날짜",value=prefill,key=f"ed_{tkey}")
        ets=dc2.time_input("시작",value=ds,key=f"ets_{tkey}",step=timedelta(minutes=15))
        ete=dc3.time_input("종료",value=de,key=f"ete_{tkey}",step=timedelta(minutes=15))
        dc4,dc5=st.columns([1,3])
        if dc4.button("지금",key="rt",use_container_width=True): st.session_state.time_reset_key+=1; st.rerun()
        dc5.caption(f"현재 KST: {now_kst().strftime('%H:%M')}")
        lo={k:get_label(k,custom_labels) for k in COLOR_PRESETS}
        cl=st.selectbox("라벨",list(lo.keys()),format_func=lambda x:f"{COLOR_DOTS.get(x,'🔵')} {lo[x]}",key="ev_label")
        edesc=st.text_area("메모",key="edesc",height=80,placeholder="메모 (선택)")
        if st.button("추가",type="primary",key="ae"):
            if not et: st.warning("제목을 입력해주세요.")
            elif DB:
                try:
                    sdt=datetime.combine(ed,ets); edt=datetime.combine(ed,ete)
                    r=create_event(uid,et,sdt,end=edt,desc=edesc,color_label=cl)
                    if r:
                        if GCAL and gcal_connected:
                            gid=gcal_create_event(uid,et,sdt,edt,edesc)
                            if gid:
                                sb=get_sb()
                                if sb: sb.table("calendar_events").update({"gcal_id":gid,"source":"both"}).eq("id",r["id"]).execute()
                        cached_get_events.clear()
                        st.success("추가됨!"); st.session_state.cal_prefill_date=None; st.rerun()
                except Exception as ex: st.error(f"오류: {ex}")

    if DB:
        today=today_kst()
        cy=st.session_state.cal_year; cm=st.session_state.cal_month

        if view=="Monthly":
            nav1,nav2,nav3,nav4,nav5=st.columns([1,1,4,1,1])
            if nav1.button("«",key="py",help="이전 년도"): st.session_state.cal_year-=1; st.rerun()
            if nav2.button("‹",key="pm",help="이전 달"):
                if cm==1: st.session_state.cal_month=12; st.session_state.cal_year-=1
                else: st.session_state.cal_month-=1
                st.rerun()
            nav3.markdown(f'<div style="text-align:center;font-size:1rem;font-weight:600;color:{D["text"]};padding:8px 0">{cy}년 {cm}월</div>',unsafe_allow_html=True)
            if nav4.button("›",key="nm",help="다음 달"):
                if cm==12: st.session_state.cal_month=1; st.session_state.cal_year+=1
                else: st.session_state.cal_month+=1
                st.rerun()
            if nav5.button("»",key="ny",help="다음 년도"): st.session_state.cal_year+=1; st.rerun()
            c_today_col,_=st.columns([1,5])
            if c_today_col.button("오늘",key="today_btn"): st.session_state.cal_year=today.year; st.session_state.cal_month=today.month; st.rerun()

            ms=date(cy,cm,1); last_day=calendar.monthrange(cy,cm)[1]; me=ms.replace(day=last_day)
            evs=cached_get_events(uid,datetime.combine(ms,datetime.min.time()),datetime.combine(me,datetime.max.time()))
            all_tasks_cal=cached_get_tasks(uid)

            hcols=st.columns(7)
            for i,dn in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
                color=D["danger"] if i==6 else D["accent"] if i==5 else D["text3"]
                hcols[i].markdown(f'<div style="text-align:center;font-size:11px;font-weight:600;color:{color};padding:4px 0;border-bottom:1px solid {D["border"]}">{dn}</div>',unsafe_allow_html=True)

            for week in calendar.monthcalendar(cy,cm):
                cols=st.columns(7)
                for i,day in enumerate(week):
                    with cols[i]:
                        if day==0:
                            st.markdown(f'<div style="min-height:80px;border-bottom:1px solid {D["border"]}20"></div>',unsafe_allow_html=True)
                        else:
                            day_str=f"{cy}-{cm:02d}-{day:02d}"
                            day_evs=[e for e in evs if e.get("start_time","")[:10]==day_str]
                            day_tasks_cal=[t for t in all_tasks_cal if t.get("due_date")==day_str and t["status"]!="done"]
                            is_today=(day==today.day and cy==today.year and cm==today.month)
                            is_selected=st.session_state.get("cal_selected_day")==day_str

                            day_color=D["danger"] if i==6 else D["accent"] if i==5 else D["text"]
                            if is_today:
                                num_html=f'<div style="display:inline-flex;width:24px;height:24px;background:{D["accent"]};border-radius:50%;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;margin-bottom:2px">{day}</div>'
                            elif is_selected:
                                num_html=f'<div style="display:inline-flex;width:24px;height:24px;background:{D["accent"]}30;border-radius:50%;border:1px solid {D["accent"]};align-items:center;justify-content:center;font-size:12px;font-weight:600;color:{D["accent"]};margin-bottom:2px">{day}</div>'
                            else:
                                num_html=f'<div style="font-size:13px;font-weight:500;color:{day_color};margin-bottom:2px">{day}</div>'

                            event_pills=""
                            shown=0
                            for e in day_evs[:2]:
                                c2=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                                title=e["title"][:9]+"…" if len(e["title"])>9 else e["title"]
                                event_pills+=f'<div style="background:{c2}22;border-left:2px solid {c2};padding:1px 4px;font-size:10px;font-weight:500;color:{c2};border-radius:0 3px 3px 0;margin:1px 0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{title}</div>'
                                shown+=1
                            remaining=len(day_evs)-shown
                            if day_tasks_cal: event_pills+=f'<div style="background:{D["warning"]}20;border-left:2px solid {D["warning"]};padding:1px 4px;font-size:10px;color:{D["warning"]};border-radius:0 3px 3px 0;margin:1px 0">◆ {day_tasks_cal[0]["title"][:8]}</div>'
                            if remaining>0: event_pills+=f'<div style="font-size:10px;color:{D["text3"]};padding:1px 4px">+{remaining}개 더</div>'

                            bg=f"background:{D['accent']}08;" if is_selected else ""
                            cell=f'<div style="min-height:80px;padding:4px 3px;border-bottom:1px solid {D["border"]}20;{bg}">{num_html}{event_pills}</div>'
                            st.markdown(cell,unsafe_allow_html=True)

                            if st.button(f"{day}",key=f"cd_{cy}{cm}{day}",use_container_width=True):
                                if st.session_state.get("cal_selected_day")==day_str:
                                    st.session_state.cal_prefill_date=date(cy,cm,day)
                                    st.session_state.cal_selected_day=None
                                else:
                                    st.session_state.cal_selected_day=day_str
                                    st.session_state.cal_prefill_date=date(cy,cm,day)
                                st.rerun()

            st.markdown(f'''<style>
[data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] .stButton > button {{
    opacity:0 !important; height:6px !important; min-height:6px !important;
    padding:0 !important; margin:-6px 0 0 0 !important; border:none !important;
    background:transparent !important; cursor:pointer !important;
}}
</style>''',unsafe_allow_html=True)

            selected_day=st.session_state.get("cal_selected_day")
            if selected_day:
                try: sel_date=date.fromisoformat(selected_day)
                except: sel_date=None
                if sel_date:
                    st.markdown(f'<div style="margin-top:16px;padding:16px;background:{D["surface"]};border:1px solid {D["border"]};border-radius:12px"><div style="font-size:14px;font-weight:600;color:{D["text"]};margin-bottom:12px">📅 {sel_date.strftime("%Y년 %m월 %d일 (%A)")}</div>',unsafe_allow_html=True)
                    sel_evs=[e for e in evs if e.get("start_time","")[:10]==selected_day]
                    sel_tasks=[t for t in all_tasks_cal if t.get("due_date")==selected_day]

                    if sel_evs:
                        for e in sel_evs:
                            color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                            gcal_b="☁ " if e.get("source") in ["google","both"] else ""
                            c1,c2=st.columns([6,1])
                            c1.markdown(f'<div style="border-left:3px solid {color};padding:6px 10px;background:{color}08;border-radius:0 8px 8px 0;margin:3px 0;font-size:13px">{gcal_b}<b>{e.get("start_time","")[11:16]}</b>{" — "+e.get("end_time","")[11:16] if e.get("end_time") else ""} {e["title"]}{"<br><small style=color:"+D["text3"]+">"+e["description"]+"</small>" if e.get("description") else ""}</div>',unsafe_allow_html=True)
                            if c2.button("삭제",key=f"del_sel_{e['id']}"):
                                if e.get("gcal_id") and GCAL and gcal_connected: gcal_delete_event(uid,e["gcal_id"])
                                delete_event(e["id"]); cached_get_events.clear()
                                st.session_state.cal_selected_day=None; st.rerun()
                    if sel_tasks:
                        st.markdown(f'<div style="font-size:12px;color:{D["text3"]};margin:8px 0 4px">마감 태스크</div>',unsafe_allow_html=True)
                        for t in sel_tasks:
                            st.markdown(f'<div style="font-size:13px;padding:4px 0;color:{D["text2"]}">◆ {t["title"]}</div>',unsafe_allow_html=True)
                    if not sel_evs and not sel_tasks:
                        st.markdown(f'<div style="font-size:13px;color:{D["text3"]};padding:8px 0">일정 없음</div>',unsafe_allow_html=True)

                    cp1,cp2=st.columns(2)
                    if cp1.button("➕ 일정 추가",type="primary",use_container_width=True,key="add_from_panel"):
                        st.session_state.cal_prefill_date=sel_date
                        st.session_state.cal_selected_day=None
                        st.rerun()
                    if cp2.button("닫기",use_container_width=True,key="close_panel"):
                        st.session_state.cal_selected_day=None
                        st.session_state.cal_prefill_date=None
                        st.rerun()
                    st.markdown('</div>',unsafe_allow_html=True)

        elif view=="Weekly":
            nav1,nav2,nav3,nav4=st.columns([1,1,4,1])
            ws=today-timedelta(days=today.weekday())
            if "week_offset" not in st.session_state: st.session_state.week_offset=0
            wo=st.session_state.week_offset
            ws=ws+timedelta(weeks=wo)
            if nav1.button("◀◀",key="pw2"): st.session_state.week_offset-=1; st.rerun()
            if nav4.button("▶▶",key="nw2"): st.session_state.week_offset+=1; st.rerun()
            nav3.markdown(f'<div style="text-align:center;font-weight:600;color:{D["text"]};padding:8px">{ws.strftime("%Y.%m.%d")} ~ {(ws+timedelta(6)).strftime("%m.%d")}</div>',unsafe_allow_html=True)
            if nav2.button("이번 주",key="tw2"): st.session_state.week_offset=0; st.rerun()
            evs=cached_get_events(uid,datetime.combine(ws,datetime.min.time()),datetime.combine(ws+timedelta(6),datetime.max.time()))
            hc=st.columns(7)
            for i,(col,dn) in enumerate(zip(hc,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])):
                day=ws+timedelta(i); it=(day==today)
                if it: col.markdown(f'<div style="text-align:center;background:{D["accent"]}20;border-radius:8px;padding:6px 2px"><b style="color:{D["accent"]}">{dn}</b><br><small style="color:{D["accent"]}">{day.strftime("%m/%d")}</small></div>',unsafe_allow_html=True)
                else:
                    dc=D["danger"] if i==6 else D["text2"]
                    col.markdown(f'<div style="text-align:center;padding:6px 2px"><b style="color:{dc}">{dn}</b><br><small style="color:{D["text3"]}">{day.strftime("%m/%d")}</small></div>',unsafe_allow_html=True)
            st.markdown(f'<hr style="margin:6px 0;border-color:{D["border"]}">',unsafe_allow_html=True)
            ec=st.columns(7)
            for i,col in enumerate(ec):
                day=ws+timedelta(i); devs=[e for e in evs if e.get("start_time","")[:10]==str(day)]
                with col:
                    day_tasks_w=[t for t in cached_get_tasks(uid) if t.get("due_date")==str(day) and t["status"]!="done"]
                    if devs or day_tasks_w:
                        for e in devs:
                            color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                            gcal_badge="☁" if e.get("source") in ["google","both"] else ""
                            st.markdown(f'<div style="background:{color}18;border-left:2px solid {color};padding:4px 6px;margin:2px 0;border-radius:4px;font-size:11px"><b>{e.get("start_time","")[11:16]}</b>{gcal_badge}<br><span style="overflow:hidden;display:block;text-overflow:ellipsis;white-space:nowrap">{e["title"]}</span></div>',unsafe_allow_html=True)
                        for t in day_tasks_w[:2]:
                            st.markdown(f'<div style="background:{D["warning"]}18;border-left:2px solid {D["warning"]};padding:3px 6px;margin:2px 0;border-radius:4px;font-size:11px">◆ {t["title"][:14]}</div>',unsafe_allow_html=True)
                    else:
                        col.markdown(f'<div style="text-align:center;color:{D["text3"]};font-size:20px;padding:12px">·</div>',unsafe_allow_html=True)

        elif view=="Daily":
            jd=st.session_state.pop("cal_jump_daily",None)
            sd=st.date_input("날짜선택",value=jd or prefill,label_visibility="collapsed")
            evs=cached_get_events(uid,datetime.combine(sd,datetime.min.time()),datetime.combine(sd,datetime.max.time()))
            st.markdown(f'**{sd.strftime("%Y년 %m월 %d일 (%A)")}**')
            dt=[t for t in cached_get_tasks(uid) if t.get("due_date")==str(sd) and t["status"]!="done"]
            if dt:
                st.markdown(f'<div class="pa-section">마감 태스크</div>',unsafe_allow_html=True)
                for t in dt: st.markdown(f"· {t['title']}")
            if evs:
                st.markdown(f'<div class="pa-section">일정</div>',unsafe_allow_html=True)
                for e in evs:
                    color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                    gcal_b=f'<span style="background:{D["accent"]}15;color:{D["accent"]};font-size:10px;padding:1px 5px;border-radius:4px;margin-left:6px">Google</span>' if e.get("source") in ["google","both"] else ""
                    c1,c2=st.columns([6,1])
                    c1.markdown(f'<div style="border-left:3px solid {color};padding:8px 12px;background:{color}08;border-radius:0 8px 8px 0;margin:4px 0"><b>{e.get("start_time","")[11:16]}</b>{" — "+e.get("end_time","")[11:16] if e.get("end_time") else ""} {e["title"]}{gcal_b}{"<br><small style=color:"+D["text3"]+">"+e["description"]+"</small>" if e.get("description") else ""}</div>',unsafe_allow_html=True)
                    if c2.button("삭제",key=f"de_{e['id']}"):
                        if (st.session_state.get("delete_confirm") or "")==f"ev_{e['id']}":
                            if e.get("gcal_id") and GCAL and gcal_connected: gcal_delete_event(uid,e["gcal_id"])
                            delete_event(e["id"]); cached_get_events.clear(); st.session_state.delete_confirm=None; st.rerun()
                        else: st.session_state.delete_confirm=f"ev_{e['id']}"; st.rerun()
                if (st.session_state.get("delete_confirm") or "").startswith("ev_"):
                    st.warning("삭제할까요?")
                    dy1,dy2=st.columns(2)
                    if dy1.button("삭제",type="primary",key="evd_y"):
                        eid=st.session_state.delete_confirm.replace("ev_","")
                        ev=[e for e in evs if e["id"]==eid]
                        if ev and ev[0].get("gcal_id") and GCAL and gcal_connected: gcal_delete_event(uid,ev[0]["gcal_id"])
                        delete_event(eid); cached_get_events.clear(); st.session_state.delete_confirm=None; st.rerun()
                    if dy2.button("취소",key="evd_n"): st.session_state.delete_confirm=None; st.rerun()
            else: st.markdown(f'<div class="pa-empty"><p style="color:{D["text3"]}">일정 없음<br><small>위 새 일정 추가에서 추가하세요</small></p></div>',unsafe_allow_html=True)
        else:
            evs=cached_get_events(uid,datetime.combine(today,datetime.min.time()),datetime.combine(today+timedelta(30),datetime.max.time()))
            if evs:
                for e in evs:
                    color=COLOR_PRESETS.get(e.get("color_label","blue"),"#3B82F6")
                    gcal_b="☁ " if e.get("source") in ["google","both"] else ""
                    st.markdown(f'<div style="border-left:3px solid {color};padding:8px 12px;background:{color}08;border-radius:0 8px 8px 0;margin:4px 0">{gcal_b}<b>{e.get("start_time","")[:10]}</b> {e.get("start_time","")[11:16]} <b>{e["title"]}</b></div>',unsafe_allow_html=True)
            else: st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">📅</div><p style="color:{D["text3"]}">향후 30일 일정 없음</p></div>',unsafe_allow_html=True)

# ===== TASKS =====
elif page=="Tasks":
    section("Tasks")
    if st.session_state.get("temp_task_save"):
        t=st.session_state.temp_task_save
        st.warning(f"수정 중이던 Task: **'{t.get('title','')}'**")
        r1,r2=st.columns(2)
        if r1.button("이어서 수정",use_container_width=True,key="rt"): st.session_state.editing_task=t; st.session_state.temp_task_save=None; st.rerun()
        if r2.button("버리기",use_container_width=True,key="dt"): st.session_state.temp_task_save=None; st.rerun()

    tab_k,tab_p=st.tabs(["Kanban","By Project"])
    with tab_k:
        with st.expander("새 Task 추가"):
            tc1,tc2=st.columns(2)
            tt2=tc1.text_input("제목",key="tt"); pt=tc1.selectbox("구분",["General","Personal","Project"],key="pt2")
            pn=""
            if pt=="Project": pn=tc1.text_input("Project 이름",key="pni")
            elif pt=="Personal": pn="Personal"
            tpr=tc2.selectbox("우선순위",["high","medium","low"],format_func=lambda x:{"high":"High","medium":"Medium","low":"Low"}[x],index=1,key="tpr")
            tst=tc2.selectbox("상태",["backlog","todo"],format_func=lambda x:{"backlog":"Backlog","todo":"To Do"}[x],key="tst")
            tdu=tc1.date_input("마감일",value=today_kst(),key="tdu"); td2=tc2.text_input("설명",key="td2")
            if st.button("추가",type="primary",key="at"):
                if tt2 and DB: create_task(uid,tt2,td2,tst,tpr,tdu,pn or None); invalidate_cache(); st.success("추가됨"); st.rerun()

        if st.session_state.get("editing_task"):
            t=st.session_state.editing_task
            st.markdown(f'<div class="pa-editing-badge">수정 중: <b>{t.get("title","")}</b></div>',unsafe_allow_html=True)
            ec1,ec2=st.columns(2)
            nt=ec1.text_input("제목",value=t.get("title",""),key="et_t"); np=ec1.text_input("Project",value=t.get("project","") or "",key="et_p")
            nd=st.text_input("설명",value=t.get("description","") or "",key="et_d")
            sl=["backlog","todo","doing","done"]; pl=["high","medium","low"]
            sl_lbl={"backlog":"Backlog","todo":"To Do","doing":"Doing","done":"Done"}
            ea,eb=ec2.columns(2)
            npr=ea.selectbox("우선순위",pl,format_func=lambda x:{"high":"High","medium":"Medium","low":"Low"}[x],index=pl.index(t.get("priority","medium")),key="et_pr")
            nst=eb.selectbox("상태",sl,format_func=lambda x:sl_lbl[x],index=sl.index(t.get("status","todo")),key="et_st")
            dv=today_kst()
            if t.get("due_date"):
                try: dv=date.fromisoformat(t["due_date"])
                except: pass
            ndu=st.date_input("마감일",value=dv,key="et_du")
            s1,s2=st.columns(2)
            if s1.button("저장",type="primary",use_container_width=True):
                if DB: update_task(t["id"],title=nt,description=nd,status=nst,priority=npr,due_date=str(ndu),project=np or None); invalidate_cache(); st.session_state.editing_task=None; st.success("수정됨"); st.rerun()
            if s2.button("← 취소",use_container_width=True): st.session_state.editing_task=None; st.rerun()
            st.markdown("---")

        if DB:
            at=cached_get_tasks(uid)
            if not at:
                st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">✅</div><p style="color:{D["text3"]}">태스크 없음<br><small>위에서 추가하세요</small></p></div>',unsafe_allow_html=True)
            else:
                with st.expander("🗑 일괄 삭제"):
                    task_options={t["id"]:f"[{t['status'].upper()}] {t['title']}" for t in at}
                    sel_del_tasks=st.multiselect("삭제할 태스크 선택",options=list(task_options.keys()),format_func=lambda x:task_options[x],label_visibility="collapsed",placeholder="삭제할 항목 선택...")
                    if sel_del_tasks:
                        if st.button(f"선택 {len(sel_del_tasks)}개 삭제",type="primary",use_container_width=True,key="bulk_del_tasks"):
                            for tid in sel_del_tasks: delete_task(tid)
                            invalidate_cache(); st.success(f"{len(sel_del_tasks)}개 삭제됨"); st.rerun()
                sc=st.columns(4)
                sc_cfg=[("backlog","Backlog","#94A3B8"),("todo","To Do","#3B82F6"),("doing","Doing","#F97316"),("done","Done","#22C55E")]
                for col,(s,lb,cc) in zip(sc,sc_cfg):
                    with col:
                        ti=[t for t in at if t["status"]==s]
                        st.markdown(f'<div style="border-top:2px solid {cc};padding-top:10px;margin-bottom:8px"><span style="font-size:13px;font-weight:600;color:{D["text"]}">{lb}</span> <span style="font-size:11px;color:{D["text3"]}">({len(ti)})</span></div>',unsafe_allow_html=True)
                        if not ti: st.markdown(f'<div style="text-align:center;color:{D["text3"]};padding:16px;font-size:20px">·</div>',unsafe_allow_html=True)
                        for t in ti:
                            bc=PRIO_COLORS.get(t.get("priority","medium"),"#F59E0B")
                            grp=get_group(t); meta=""
                            if grp=="personal": meta+=f'<div style="font-size:11px;color:#8B5CF6;margin-top:3px">Personal</div>'
                            elif grp=="project": meta+=f'<div style="font-size:11px;color:{D["accent"]};margin-top:3px">{t["project"]}</div>'
                            ov=t.get("due_date") and t["due_date"]<str(today_kst()); td_=t.get("due_date")==str(today_kst())
                            if t.get("due_date"):
                                if ov: meta+=f'<div style="font-size:11px;color:{D["danger"]};margin-top:2px">기한초과 {t["due_date"]}</div>'
                                elif td_: meta+=f'<div style="font-size:11px;color:{D["warning"]};margin-top:2px">오늘 마감</div>'
                                else: meta+=f'<div style="font-size:11px;color:{D["text3"]};margin-top:2px">{t["due_date"]}</div>'
                            bg=D["surface"]
                            if td_: bg="#2A1A0A" if th=="dark" else "#FFF8F0"
                            elif ov: bg="#2A0A0A" if th=="dark" else "#FFF5F5"
                            st.markdown(f'<div style="background:{bg};border-radius:10px;padding:10px 12px;margin:4px 0;border-left:3px solid {bc};border:1px solid {D["border"]};border-left-width:3px"><div style="font-size:13.5px;font-weight:500;color:{D["text"]}">{t["title"]}</div>{meta}</div>',unsafe_allow_html=True)
                            bc2=st.columns(4)
                            if bc2[0].button("✏",key=f"e_{t['id']}"): st.session_state.editing_task=t; st.rerun()
                            if s=="backlog":
                                if bc2[1].button("→",key=f"f_{t['id']}"): update_task(t["id"],status="todo"); invalidate_cache(); st.rerun()
                            elif s=="todo":
                                if bc2[1].button("←",key=f"b_{t['id']}"): update_task(t["id"],status="backlog"); invalidate_cache(); st.rerun()
                                if bc2[2].button("→",key=f"f_{t['id']}"): update_task(t["id"],status="doing"); invalidate_cache(); st.rerun()
                            elif s=="doing":
                                if bc2[1].button("←",key=f"b_{t['id']}"): update_task(t["id"],status="todo"); invalidate_cache(); st.rerun()
                                if bc2[2].button("✓",key=f"d_{t['id']}"): update_task(t["id"],status="done"); invalidate_cache(); st.rerun()
                            elif s=="done":
                                if bc2[1].button("↩",key=f"b_{t['id']}"): update_task(t["id"],status="doing"); invalidate_cache(); st.rerun()
                            if bc2[3].button("🗑",key=f"x_{t['id']}"): st.session_state.delete_confirm=f"task_{t['id']}"; st.rerun()
                            if (st.session_state.get("delete_confirm") or "")==f"task_{t['id']}":
                                st.warning(f"**{t['title']}** 삭제?")
                                dy1,dy2=st.columns(2)
                                if dy1.button("삭제",type="primary",key=f"dy_{t['id']}"): delete_task(t["id"]); invalidate_cache(); st.session_state.delete_confirm=None; st.rerun()
                                if dy2.button("취소",key=f"dn_{t['id']}"): st.session_state.delete_confirm=None; st.rerun()
                            st.markdown(f'<div style="height:1px;background:{D["border"]};margin:4px 0;opacity:0.4"></div>',unsafe_allow_html=True)

    with tab_p:
        if DB:
            at=cached_get_tasks(uid)
            if not at: st.markdown(f'<div class="pa-empty"><p style="color:{D["text3"]}">프로젝트 없음</p></div>',unsafe_allow_html=True)
            else:
                general=[t for t in at if get_group(t)=="general"]
                personal=[t for t in at if get_group(t)=="personal"]
                pm={}
                for t in at:
                    if get_group(t)=="project": pm.setdefault(t.get("project","기타"),[]).append(t)
                def rg(name,tasks,icon,hc):
                    if not tasks: return
                    dc=len([t for t in tasks if t["status"]=="done"]); pct=int(dc/len(tasks)*100)
                    st.markdown(f'<div style="background:{hc}10;border:1px solid {hc}25;border-radius:12px;padding:12px 16px;margin:10px 0 6px"><span style="font-size:14px;font-weight:600;color:{hc}">{icon} {name}</span> <span style="color:{D["text3"]};font-size:12px">{dc}/{len(tasks)} 완료</span></div>',unsafe_allow_html=True)
                    st.progress(pct/100)
                    for t in tasks:
                        si={"backlog":"·","todo":"○","doing":"◑","done":"●"}.get(t["status"],"·")
                        st.markdown(f'<div style="margin-left:14px;padding:3px 8px;font-size:13px;color:{D["text2"]}">{si} {t["title"]}{" · "+t["due_date"] if t.get("due_date") else ""}</div>',unsafe_allow_html=True)
                rg("General",general,"◎",D["accent"]); rg("Personal",personal,"◈","#8B5CF6")
                for pn,tasks in sorted(pm.items()): rg(pn,tasks,"◉","#22C55E")

# ===== NOTES =====
elif page=="Notes":
    if st.session_state.get("temp_note_save"):
        temp=st.session_state.temp_note_save
        st.warning(f"⚠️ **저장하지 않고 나온 노트**: '{temp.get('title','(제목 없음)')}' — 이어서 편집하거나 버리기를 선택하세요.")
        r1,r2=st.columns(2)
        if r1.button("이어서 편집 (저장 안 된 내용 복원)",use_container_width=True,key="rn"):
            restored=dict(temp["note"]) if temp.get("note") else {}
            restored["content"]=temp.get("content",""); restored["title"]=temp.get("title","")
            st.session_state.editing_note=restored; clear_nc(); clear_ai(); st.session_state["temp_note_save"]=None; st.rerun()
        if r2.button("버리기",use_container_width=True,key="dn"): st.session_state["temp_note_save"]=None; st.rerun()

    if st.session_state.editing_note:
        note=st.session_state.editing_note
        all_notes=cached_get_notes(uid) if DB else []
        bc1,bc2=st.columns([1,6])
        if bc1.button("← 목록",key="bk"):
            tc=st.session_state.get("nc",note.get("content",""))
            tt3=st.session_state.get("nt",note.get("title",""))
            if tc or tt3: st.session_state["temp_note_save"]={"note":note,"content":tc,"title":tt3}
            st.session_state.editing_note=None; clear_nc(); clear_ai(); st.rerun()
        bc2.markdown(f'<div class="pa-breadcrumb">Notes › {"편집 중" if note.get("id") and note["id"]!="demo" else "새 노트"}</div>',unsafe_allow_html=True)

        # #14: 상단 저장 버튼 (스크롤 없이 저장)
        top_s1, top_s2, top_s3 = st.columns([2,1,3])
        top_save = top_s1.button("💾 저장",type="primary",use_container_width=True,key="top_save_btn")
        top_close = top_s2.button("닫기",use_container_width=True,key="top_close_btn")

        nt=st.text_input("노트제목",value=note.get("title",""),key="nt",placeholder="제목",label_visibility="collapsed")
        tm={"note":"Note","meeting":"Meeting","daily":"Daily","idea":"Idea","project":"Project"}
        ti={"note":"📝","meeting":"📋","daily":"📅","idea":"💡","project":"📁"}
        ns=st.selectbox("노트타입",list(tm.keys()),format_func=lambda x:f"{ti[x]} {tm[x]}",
                        index=list(tm.keys()).index(note.get("note_type","note")) if note.get("note_type","note") in tm else 0,
                        key="nt_sel",label_visibility="collapsed")
        if DB:
            all_tmps=get_templates(uid)
            ntmps=[t for t in all_tmps if t.get("note_type") not in ["report_template","ai_prompt","pomo_prompt"] and not t.get("note_type","").startswith("default_")]
            if ntmps:
                tc2=st.columns(min(len(ntmps),6))
                for i,t in enumerate(ntmps):
                    if tc2[i].button(f"{t.get('icon','📄')} {t['name']}",key=f"tmp_{t['id']}"): st.session_state["_tmpl"]=t["content"]; clear_nc(); st.rerun()

        dc=st.session_state.pop("_tmpl",None)
        if dc is None:
            ex=note.get("content","")
            dc=ex if ex and ex.strip() else get_note_template(uid,ns)

        _tbs=[("B","**텍스트**","굵게"),("I","_텍스트_","기울임"),("S","~~텍스트~~","취소선"),
              ("H1","# 제목\n","제목1"),("H2","## 소제목\n","제목2"),("H3","### 항목\n","제목3"),
              ("- 목록","- 항목\n","글머리"),("1. 번","1. 항목\n","번호"),
              ("[ ]","- [ ] 할일\n","Task"),
              ("> 인용","> 인용문\n","인용"),("코드","```\n코드\n```\n","코드"),("---","---\n","구분선")]
        _tc=st.columns(12)
        for _i,(_l,_ins,_tip) in enumerate(_tbs):
            if _tc[_i].button(_l,key=f"tb_{_i}",use_container_width=True,help=_tip):
                _cur=st.session_state.get("nc",dc or ""); _sep="" if (not _cur or _cur.endswith("\n")) else "\n"
                st.session_state["_tmpl"]=_cur+_sep+_ins; clear_nc(); st.rerun()

        content=st.text_area("노트내용",value=dc,height=360,label_visibility="collapsed",key="nc",placeholder="내용 입력...\nTip: - [ ] 항목 → 저장 시 Task 자동 생성")

        uf=st.file_uploader("파일 첨부",type=["txt","md","docx","xlsx","csv","png","jpg","jpeg","pdf"],key="nfu",label_visibility="collapsed")
        if uf:
            if uf.type.startswith("image"):
                st.image(uf)
                if st.button("OCR",key="ocr"):
                    with st.spinner("..."): ot=ocr_image(uf.read(),uf.type); st.session_state["_tmpl"]=content+"\n\n---\n"+ot; clear_nc(); st.rerun()
            else:
                if st.button("노트에 가져오기",key="imp"):
                    with st.spinner("..."): im=file_to_markdown(uf); st.session_state["_tmpl"]=content+"\n\n---\n"+im; clear_nc(); st.rerun()

        ti2=st.text_input("태그",placeholder="#work #project",key="ntags",label_visibility="collapsed")

        st.markdown(f'<div class="pa-section">AI 도구</div>',unsafe_allow_html=True)
        ac=st.columns(4)
        bs=ac[0].button("요약",use_container_width=True)
        br=ac[1].button("연결 노트",use_container_width=True)
        be=ac[2].button("확장",use_container_width=True)
        bm=ac[3].button("MD 변환",use_container_width=True)

        if content and content.strip():
            mt=st.toggle("Markdown 미리보기",value=st.session_state.get("md_preview_mode",False),key="mdt")
            if mt!=st.session_state.get("md_preview_mode",False): st.session_state.md_preview_mode=mt; st.rerun()
        if st.session_state.get("md_preview_mode") and content:
            st.markdown("---"); st.markdown(content); st.markdown("---")

        apd=[]
        if DB:
            atm=get_templates(uid); apd=[t for t in atm if t.get("note_type")=="ai_prompt"]
        sp=["기본 요약"]+[t["name"] for t in apd if t.get("icon","")=="📝"]
        ep=["기본 확장"]+[t["name"] for t in apd if t.get("icon","")=="✨"]
        pc1,pc2,_,_=st.columns(4)
        ss=pc1.selectbox("요약방식",sp,key="ss",label_visibility="collapsed")
        se=pc2.selectbox("확장방식",ep,key="se",label_visibility="collapsed")

        if bs and content:
            cp=None
            if ss!="기본 요약": m=[t for t in apd if t["name"]==ss]; cp=m[0]["content"] if m else None
            with st.spinner("요약 중..."): res=summarize_note(content,cp); st.session_state.ai_result=res; st.session_state.ai_result_type="summary"; st.rerun()
        if br: st.session_state.show_related=not st.session_state.get("show_related",False); st.rerun()
        if be and content:
            cp=None
            if se!="기본 확장": m=[t for t in apd if t["name"]==se]; cp=m[0]["content"] if m else None
            with st.spinner("확장 중..."): res=expand_note(content,cp); st.session_state.ai_result=res; st.session_state.ai_result_type="expand"; st.rerun()
        if bm and content:
            with st.spinner("변환 중..."): res=get_ai(f"다음을 깔끔한 마크다운으로 정리. 외부정보 없이:\n\n{content}",st.session_state.ai_engine,"content"); st.session_state.ai_result=res; st.session_state.ai_result_type="md"; st.rerun()

        if st.session_state.get("ai_result"):
            res=st.session_state.ai_result; rt=st.session_state.ai_result_type
            lbl={"summary":"요약","expand":"확장","md":"MD 변환"}.get(rt,"AI")
            st.markdown("---"); st.markdown(f"**{lbl} 결과**")
            st.markdown(f'<div style="background:{D["surface"]};border:1px solid {D["border"]};border-radius:10px;padding:16px;font-size:13.5px;line-height:1.6">{res}</div>',unsafe_allow_html=True)
            st.markdown("**반영:**"); rb=st.columns(4)
            if rb[0].button("맨 위",use_container_width=True,key="at"):
                nc=f"## 요약\n{res}\n\n---\n\n{content}" if rt=="summary" else f"{res}\n\n---\n\n{content}"
                st.session_state["_tmpl"]=nc; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb[1].button("맨 아래",use_container_width=True,key="ab"):
                st.session_state["_tmpl"]=f"{content}\n\n---\n\n{res}"; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb[2].button("대체",use_container_width=True,key="ar"):
                st.session_state["_tmpl"]=res; st.session_state.ai_result=None; clear_nc(); st.rerun()
            if rb[3].button("무시",use_container_width=True,key="ai"): st.session_state.ai_result=None; st.rerun()

        if st.session_state.get("show_related") and note.get("id") and note["id"]!="demo":
            st.markdown("---")
            rc1,rc2=st.columns(2)
            with rc1:
                st.markdown("**연결된 노트**")
                lnk=get_linked_notes(note["id"]); lids=[l["target_id"] for l in lnk]
                lo=[n for n in all_notes if n["id"] in lids]
                if lo:
                    for ln in lo: st.markdown(f"📝 {ln['title']}")
                else: st.caption("없음 · `[[노트제목]]` 입력 시 자동 링크")
            with rc2:
                st.markdown("**검색 후 연결**")
                ls=st.text_input("연결검색",key="ls",placeholder="제목 검색...",label_visibility="collapsed")
                if ls:
                    mx=[n for n in all_notes if ls.lower() in n["title"].lower() and n["id"]!=note.get("id")]
                    for mn in mx[:5]:
                        if st.button(f"🔗 {mn['title']}",key=f"lk_{mn['id']}"): link_notes(note["id"],mn["id"]); st.success("연결됨"); st.rerun()

        st.markdown("---")
        sc=st.columns([2,1,1,1])
        if sc[0].button("저장",type="primary",use_container_width=True) or top_save:
            if DB and note.get("id")!="demo":
                update_note(note["id"],title=nt,content=content,note_type=ns)
                invalidate_cache()
                # 저장 완료 시 임시저장 즉시 제거
                st.session_state["temp_note_save"]=None
                if ti2:
                    for tg in [t.strip().replace("#","") for t in ti2.split(",") if t.strip()]:
                        tgo=add_tag(uid,tg)
                        if tgo: tag_note(note["id"],tgo["id"])
                fls=re.findall(r'\[\[(.+?)\]\]',content)
                for fl in fls:
                    mx=[n for n in all_notes if n["title"].lower()==fl.lower() and n["id"]!=note["id"]]
                    if mx: link_notes(note["id"],mx[0]["id"])
                et=cached_get_tasks(uid); etitles={t["title"].lower() for t in et}
                cbi=re.findall(r'- \[ \] (.+)',content); nc2=0
                for item in cbi:
                    item=item.strip()
                    if item and item.lower() not in etitles:
                        create_task(uid,item,desc=f"노트 '{nt}'에서",status="todo",nid=note["id"]); etitles.add(item.lower()); nc2+=1
                if nc2>0: invalidate_cache()
                st.success(f"저장됨{' (Task '+str(nc2)+'개 생성)' if nc2>0 else ''}")
        if sc[1].button("← 닫기",use_container_width=True) or top_close: st.session_state.editing_note=None; st.session_state.show_related=False; clear_nc(); clear_ai(); st.rerun()
        if sc[2].button("삭제",use_container_width=True): st.session_state.delete_confirm=f"note_{note.get('id','')}"; st.rerun()
        if (st.session_state.get("delete_confirm") or "").startswith("note_"):
            st.error("정말 삭제할까요?")
            dy1,dy2=st.columns(2)
            if dy1.button("삭제",type="primary",key="ndy"):
                if DB: delete_note(note["id"]); invalidate_cache()
                st.session_state.editing_note=None; st.session_state.delete_confirm=None; clear_nc(); clear_ai(); st.rerun()
            if dy2.button("취소",key="ndn"): st.session_state.delete_confirm=None; st.rerun()
        if sc[3].button("내보내기",use_container_width=True):
            st.download_button("⬇️ .md",f"# {nt}\n\n{content}",f"{nt}.md","text/markdown")
    else:
        note_tab1, note_tab2 = st.tabs(["📝 노트 목록", "📊 주간 보고"])

        with note_tab1:
            nc1,nc2,nc3,nc4=st.columns([2,1,1,1])
            sq=nc1.text_input("노트검색",placeholder="검색...",label_visibility="collapsed")
            sn=nc2.selectbox("정렬",["최신순","업데이트순","이름순"],label_visibility="collapsed",key="ns")
            if nc3.button("Today",use_container_width=True,help="오늘의 일지"):
                if DB:
                    tans=[n for n in cached_get_notes(uid) if n.get("updated_at","")[:10]==str(today_kst())]
                    tn=get_daily_note(uid)
                    if tn:
                        if tans and (not tn.get("content") or not tn["content"].strip()):
                            with st.spinner("일지 초안 작성 중..."):
                                sl2="\n".join([f"- {n['title']}: {n.get('content','')[:100]}" for n in tans[:10]])
                                draft=get_ai(f"오늘({today_kst()}) 노트들 기반 일일 요약 초안:\n{sl2}\n\n형식:\n# {today_kst().strftime('%Y-%m-%d %A')}\n\n## 오늘 요약\n\n## 주요 메모\n\n## 내일 할 일\n",st.session_state.ai_engine,"summary")
                                tn["content"]=draft
                        st.session_state.editing_note=tn; clear_nc(); clear_ai(); st.rerun()
            if nc4.button("+ New",type="primary",use_container_width=True):
                if DB:
                    nn2=create_note(uid,"",""); invalidate_cache()
                    if nn2: st.session_state.editing_note=nn2; st.session_state.show_related=False; clear_nc(); clear_ai(); st.rerun()

            if DB:
                with st.expander("폴더"):
                    flds=get_folders(uid)
                    fc1,fc2=st.columns([3,1])
                    fn=fc1.text_input("폴더이름",key="fn",placeholder="새 폴더 이름",label_visibility="collapsed")
                    if fc2.button("생성",key="cf"):
                        if fn: create_folder(uid,fn); st.rerun()
                    if flds:
                        for f in flds:
                            f1,f2=st.columns([5,1])
                            ia=st.session_state.get("folder_filter")==f["id"]
                            if f1.button(f"{'📂' if ia else '📁'} {f['name']}",key=f"fld_{f['id']}",use_container_width=True): st.session_state["folder_filter"]=f["id"]; st.rerun()
                            if f2.button("삭제",key=f"df_{f['id']}"): delete_folder(f["id"]); st.rerun()
                    if st.session_state.get("folder_filter"):
                        if st.button("전체 보기",use_container_width=True): st.session_state.pop("folder_filter",None); st.rerun()

                fid=st.session_state.get("folder_filter")
                notes=cached_get_notes(uid,search=sq or None,folder_id=fid)
                if sn=="이름순": notes=sorted(notes,key=lambda x:x.get("title",""))
                elif sn=="업데이트순": notes=sorted(notes,key=lambda x:x.get("updated_at",""),reverse=True)
                else: notes=sorted(notes,key=lambda x:x.get("created_at",""),reverse=True)

                if not notes:
                    st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">📝</div><p style="color:{D["text3"]}">노트 없음<br><small>+ New로 첫 노트를 만들어보세요</small></p></div>',unsafe_allow_html=True)
                else:
                    with st.expander("🗑 일괄 삭제"):
                        note_options={n["id"]:n["title"] or "(제목 없음)" for n in notes}
                        sel_del_notes=st.multiselect("삭제할 노트 선택",options=list(note_options.keys()),format_func=lambda x:note_options[x],label_visibility="collapsed",placeholder="삭제할 항목 선택...")
                        if sel_del_notes:
                            if st.button(f"선택 {len(sel_del_notes)}개 삭제",type="primary",use_container_width=True,key="bulk_del_notes"):
                                for nid in sel_del_notes: delete_note(nid)
                                invalidate_cache(); st.success(f"{len(sel_del_notes)}개 삭제됨"); st.rerun()
                    for n in notes:
                        ticon={"meeting":"📋","daily":"📅","idea":"💡","project":"📁"}.get(n.get("note_type"),"📝")
                        fav="⭐ " if n.get("is_favorite") else ""
                        prev=n.get("content","")[:80].replace("\n"," ").strip() if n.get("content") else ""
                        cn,ca=st.columns([5,1])
                        # #13: 제목 클릭으로 열기
                        title_clicked=cn.button(
                            f"{fav}{ticon} {n['title'] or '(제목 없음)'}",
                            key=f"nt_{n['id']}",
                            use_container_width=True,
                            help="클릭하여 열기"
                        )
                        if prev:
                            cn.caption(prev)
                        cn.caption(relative_date(n.get("updated_at","")))
                        if title_clicked or ca.button("열기",key=f"o_{n['id']}"):
                            st.session_state.editing_note=n; st.session_state.show_related=False; clear_nc(); clear_ai(); st.rerun()
                        if ca.button("🗑",key=f"nd_{n['id']}",help="삭제"):
                            st.session_state.delete_confirm=f"note_{n['id']}"; st.rerun()
                        if (st.session_state.get("delete_confirm") or "")==f"note_{n['id']}":
                            st.error(f"**{n['title']}** 삭제할까요?")
                            nd1,nd2=st.columns(2)
                            if nd1.button("삭제",type="primary",key=f"ndly_{n['id']}"): delete_note(n["id"]); invalidate_cache(); st.session_state.delete_confirm=None; st.rerun()
                            if nd2.button("취소",key=f"ndln_{n['id']}"): st.session_state.delete_confirm=None; st.rerun()
                        st.markdown(f'<div style="height:1px;background:{D["border"]};margin:2px 0;opacity:0.3"></div>',unsafe_allow_html=True)

        with note_tab2:
            col_d1,col_d2=st.columns(2)
            up=col_d1.selectbox("기간선택",["이번 주","지난 7일","지난 14일","이번 달","사용자 지정"],label_visibility="collapsed")
            if up=="이번 주": start=today_kst()-timedelta(days=today_kst().weekday()); end=today_kst()
            elif up=="지난 7일": start=today_kst()-timedelta(7); end=today_kst()
            elif up=="지난 14일": start=today_kst()-timedelta(14); end=today_kst()
            elif up=="이번 달": start=today_kst().replace(day=1); end=today_kst()
            else: start=col_d1.date_input("시작",value=today_kst()-timedelta(7)); end=col_d2.date_input("종료",value=today_kst())
            col_d2.caption(f"{start} ~ {end}")
            DF="## 주간 보고\n### 1. 핵심 성과\n### 2. 진행 업무\n### 3. 이슈\n### 4. 다음 주 계획"
            cp2=st.text_area("보고서형식",value=DF,height=150,label_visibility="collapsed")
            if st.button("보고서 생성",type="primary",use_container_width=True):
                if DB:
                    with st.spinner("보고서 작성 중..."):
                        ns_wr=cached_get_notes(uid); ts_wr=cached_get_tasks(uid); es_wr=get_expenses(uid,now_kst().strftime("%Y-%m"))
                        ns_wr=[n for n in ns_wr if n.get("updated_at","")[:10]>=str(start)]
                        rpt=weekly_report(ns_wr,ts_wr,es_wr,custom_format=cp2); st.markdown(rpt)
                        s1,s2=st.columns(2)
                        if s1.button("저장",key="sr"): create_note(uid,f"Report {start}~{end}",rpt); invalidate_cache(); st.success("저장됨")
                        s2.download_button("다운로드",rpt,f"report.md","text/markdown")

# ===== 목표 & 습관 =====
elif page=="목표 & 습관":
    section("목표 & 습관")
    if DB:
        habits=cached_get_habits(uid); logs=get_habit_logs(uid,today_kst(),today_kst())
        done_ids={l["habit_id"] for l in logs if l.get("completed")}
        log_vals={l["habit_id"]:l.get("value",0) for l in logs}
        if habits:
            st.markdown(f'<div class="pa-section">오늘 ({today_kst().strftime("%m월 %d일")})</div>',unsafe_allow_html=True)
            cols=st.columns(min(len(habits),3))
            for i,h in enumerate(habits):
                with cols[i%min(len(habits),3)]:
                    if h.get("habit_type")=="numeric":
                        t2=float(h.get("target_value",1)); unit=h.get("unit","")
                        cv=float(log_vals.get(h["id"],0))
                        st.markdown(f"**{h.get('icon','🎯')} {h['name']}**")
                        nv=st.number_input(f"/{t2}{unit}",min_value=0.0,max_value=t2*3,value=cv,step=0.5,key=f"hpv_{h['id']}")
                        pct=min(nv/t2,1.0) if t2>0 else 0
                        st.progress(pct,text=f"{nv}/{t2}{unit}")
                        dc=st.checkbox("완료",value=h["id"] in done_ids or pct>=1.0,key=f"hpn_{h['id']}")
                        if st.button("저장",key=f"hps_{h['id']}",use_container_width=True): toggle_habit_value(h["id"],uid,nv if dc else 0); st.rerun()
                    else:
                        chk=st.checkbox(f"{h.get('icon','✅')} {h['name']}",value=h["id"] in done_ids,key=f"hp_{h['id']}")
                        if chk!=(h["id"] in done_ids): toggle_habit(h["id"],uid); st.rerun()
            st.markdown("---"); st.markdown(f'<div class="pa-section">이번 주</div>',unsafe_allow_html=True)
            ws_d=today_kst()-timedelta(days=today_kst().weekday()); wl=get_habit_logs(uid,ws_d,today_kst())
            wc=len([l for l in wl if l.get("completed")]); wt=len(habits)*(today_kst().weekday()+1)
            r=int(wc/wt*100) if wt>0 else 0
            st.progress(r/100,text=f"{r}% ({wc}/{wt})")
            for h in habits:
                hl=[l for l in wl if l["habit_id"]==h["id"] and l.get("completed")]
                dd=len(hl); dt2=today_kst().weekday()+1; ph=int(dd/dt2*100) if dt2>0 else 0
                st.markdown(f'{h.get("icon","✅")} **{h["name"]}** {dd}/{dt2}일 ({ph}%)')
        else: st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">🎯</div><p style="color:{D["text3"]}">아직 없음<br><small>아래에서 추가하세요</small></p></div>',unsafe_allow_html=True)
        st.markdown("---"); st.markdown(f'<div class="pa-section">추가</div>',unsafe_allow_html=True)
        hc1,hc2,hc3=st.columns([2,1,1])
        hn=hc1.text_input("습관이름",key="hn")
        hi_cur=st.session_state.get("hi2_val","✅")
        selected_em=emoji_picker("habit_add",hi_cur)
        if selected_em!=hi_cur: st.session_state["hi2_val"]=selected_em; st.rerun()
        hi=selected_em
        ht=hc3.selectbox("습관타입",["check","numeric"],format_func=lambda x:{"check":"체크","numeric":"수치"}[x],key="ht")
        htr=1.0; hu=""
        if ht=="numeric":
            hc4,hc5=st.columns(2); htr=hc4.number_input("목표값",min_value=0.1,value=1.0,step=0.5,key="htr"); hu=hc5.text_input("단위",placeholder="km, 잔...",key="hu")
        if st.button("추가",key="hah",type="primary"):
            if hn and DB: create_habit_v2(uid,hn,hi,ht,htr,hu); cached_get_habits.clear(); st.rerun()
        if habits:
            st.markdown("---"); st.markdown(f'<div class="pa-section">관리</div>',unsafe_allow_html=True)
            for h in habits:
                c1,c2=st.columns([5,1]); c1.markdown(f"{h.get('icon','✅')} {h['name']}")
                if c2.button("삭제",key=f"dhp_{h['id']}"): st.session_state.delete_confirm=f"habit_{h['id']}"; st.rerun()
                if (st.session_state.get("delete_confirm") or "")==f"habit_{h['id']}":
                    dy1,dy2=st.columns(2)
                    if dy1.button("삭제",type="primary",key=f"hdy_{h['id']}"): delete_habit(h["id"]); cached_get_habits.clear(); st.session_state.delete_confirm=None; st.rerun()
                    if dy2.button("취소",key=f"hdn_{h['id']}"): st.session_state.delete_confirm=None; st.rerun()

# ===== TRANSCRIPTION =====
elif page=="Transcription":
    section("Transcription")
    tab1,tab2=st.tabs(["전사","사전"])
    with tab1:
        audio=st.file_uploader("오디오파일",type=["mp3","wav","m4a","ogg","webm"],label_visibility="collapsed")
        if audio:
            st.audio(audio)
            if st.button("전사 시작",type="primary"):
                with st.spinner("전사 중..."): t=transcribe(audio); t=apply_terms(uid,t) if DB else t; st.session_state.transcript=t
        manual=st.text_area("텍스트붙여넣기",height=150,key="mt",label_visibility="collapsed",placeholder="전사 텍스트...")
        if manual:
            corrected=apply_terms(uid,manual) if DB else manual
            if corrected!=manual: st.info("용어 교정됨")
            st.session_state.transcript=corrected or manual
        if st.session_state.get("transcript"):
            st.text_area("전사결과",value=st.session_state.transcript,height=150,key="tv",disabled=True)
            sv=st.selectbox("저장형식",["Meeting Notes","요약","액션아이템","원문"])
            if st.button("처리 후 저장",type="primary"):
                with st.spinner("..."):
                    result=""
                    if "Meeting" in sv: result=summarize_meeting(st.session_state.transcript)
                    elif "요약" in sv: result=get_ai(f"5줄 요약:\n\n{st.session_state.transcript}",st.session_state.ai_engine,"summary")
                    elif "액션" in sv: result=get_ai(f"액션아이템:\n\n{st.session_state.transcript}",st.session_state.ai_engine,"analysis")
                    else: result=st.session_state.transcript
                    if DB: create_note(uid,f"Transcript {today_kst()}",result,"meeting" if "Meeting" in sv else "note"); invalidate_cache(); st.success("저장됨")
                    if result and "원문" not in sv: st.markdown(result)
    with tab2:
        tc1,tc2=st.columns(2)
        wt=tc1.text_input("잘못된표현",key="wt_input"); ct=tc2.text_input("올바른표현",key="ct_input")
        if st.button("추가",type="primary",key="at2"):
            if wt and ct and DB: add_term(uid,wt,ct); st.success("추가됨"); st.rerun()
        if DB:
            for w,c in get_terms(uid).items(): st.markdown(f"~~{w}~~ → **{c}**")

# ===== WEB CLIPPER =====
elif page=="Web Clipper":
    section("Web Clipper")
    url=st.text_input("URL입력",placeholder="https://...",label_visibility="collapsed")
    if st.button("저장 및 요약",type="primary"):
        if url:
            with st.spinner("..."): s=web_summary(url); st.markdown(s)
            if DB: create_note(uid,f"🔗 {url[:50]}",f"URL: {url}\n\n---\n{s}"); invalidate_cache(); st.success("저장됨")
    if DB:
        clips=[n for n in cached_get_notes(uid) if n.get("content","").startswith("URL:")]
        if clips:
            for c in clips[:10]: st.markdown(f"🔗 **{c['title']}** · {relative_date(c.get('updated_at',''))}")

# ===== POMODORO =====
elif page=="Pomodoro":
    section("Pomodoro")
    pc1,pc2,pc3=st.columns(3)
    fm=pc1.number_input("집중분",min_value=1,max_value=90,value=25,step=5,key="fm")
    bm2=pc2.number_input("휴식분",min_value=1,max_value=30,value=5,step=1,key="bm2")
    tw=pc3.text_input("작업내용",key="tw",placeholder="오늘 할 일...")
    timer_html=f"""<style>.pc{{text-align:center;padding:20px;font-family:-apple-system,sans-serif}}.td{{font-size:72px;font-weight:800;color:#EF4444;font-family:'Courier New',monospace;letter-spacing:6px;margin:8px 0;line-height:1}}.td.brk{{color:#22C55E}}.ts{{font-size:14px;color:#888;margin-bottom:16px;min-height:20px}}.prog{{width:280px;height:6px;background:#333;border-radius:99px;margin:0 auto 20px;overflow:hidden}}.pb{{height:100%;background:linear-gradient(90deg,#EF4444,#F97316);border-radius:99px;transition:width 1s linear}}.pb.brk{{background:linear-gradient(90deg,#22C55E,#14B8A6)}}.br{{display:flex;gap:8px;justify-content:center}}.btn{{padding:10px 20px;font-size:14px;font-weight:600;border-radius:8px;border:none;cursor:pointer}}.bs{{background:#EF4444;color:#fff}}.bb{{background:#22C55E;color:#fff}}.br2{{background:#6B7280;color:#fff}}.sc{{font-size:13px;color:#888;margin-top:12px}}</style>
<div class="pc"><div class="td" id="td">{fm:02d}:00</div><div class="ts" id="ts">시작할 준비가 되셨나요?</div><div class="prog"><div class="pb" id="pb" style="width:100%"></div></div><div class="br"><button class="btn bs" id="sb" onclick="toggle()">▶ 시작</button><button class="btn bb" onclick="startBreak()">휴식</button><button class="btn br2" onclick="reset()">리셋</button></div><div class="sc" id="sc">오늘 완료: 0 🍅</div></div>
<script>const F={fm}*60,B={bm2}*60;let left=F,total=F,run=false,brk=false,iv=null,sess=0;function fmt(t){{return String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0')}}function ui(){{document.getElementById('td').textContent=fmt(left);document.getElementById('td').className='td'+(brk?' brk':'');document.getElementById('pb').style.width=(left/total*100)+'%';document.getElementById('pb').className='pb'+(brk?' brk':'')}}function beep(){{try{{const a=new AudioContext(),o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=880;g.gain.setValueAtTime(0.25,a.currentTime);g.gain.exponentialRampToValueAtTime(0.01,a.currentTime+0.7);o.start();o.stop(a.currentTime+0.7)}}catch(e){{}}}}function toggle(){{if(run){{clearInterval(iv);run=false;document.getElementById('sb').textContent='▶ 재개';document.getElementById('ts').textContent='일시정지'}}else{{run=true;document.getElementById('sb').textContent='⏸ 일시정지';document.getElementById('ts').textContent=brk?'휴식 중...':'집중 중!';iv=setInterval(()=>{{if(left>0){{left--;ui()}}else{{clearInterval(iv);run=false;document.getElementById('sb').textContent='▶ 시작';if(!brk){{sess++;document.getElementById('sc').textContent='오늘 완료: '+sess+' 🍅';document.getElementById('ts').textContent='완료!';beep()}}else{{document.getElementById('ts').textContent='휴식 완료!';brk=false;left=F;total=F;ui()}}}}}}),1000)}}}}function startBreak(){{clearInterval(iv);run=false;brk=true;left=B;total=B;document.getElementById('sb').textContent='▶ 시작';ui()}}function reset(){{clearInterval(iv);run=false;brk=false;left=F;total=F;document.getElementById('sb').textContent='▶ 시작';document.getElementById('ts').textContent='시작할 준비가 되셨나요?';ui()}}</script>"""
    components.html(timer_html,height=260)
    st.markdown("---")
    cr1,cr2,cr3=st.columns(3)
    intr=cr2.number_input("방해횟수",min_value=0,value=0,key="intr")
    isc=cr3.checkbox("완주",value=True,key="isc")
    if cr1.button("세션 기록",type="primary",use_container_width=True):
        if DB: log_pomo(uid,fm,tw,"complete" if isc else "interrupted",intr); st.success("기록됨!")
        if isc: st.balloons()
    if DB:
        logs=get_pomo_logs(uid,7)
        if logs:
            cs1,cs2,cs3=st.columns(3); cl2=[l for l in logs if l.get("status","complete")=="complete"]
            cs1.metric("완료",f"{len(cl2)} 🍅"); cs2.metric("집중",f"{sum(l.get('duration_minutes',25) for l in cl2)}분"); cs3.metric("완주율",f"{int(len(cl2)/len(logs)*100)}%")
            if st.button("AI Insight",type="primary",use_container_width=True):
                with st.spinner("..."): st.markdown(pomodoro_insight(logs,None))

# ===== SEARCH =====
elif page=="Search":
    section("Search","노트 · 태스크 · 일정 통합 검색")
    kw2=st.text_input("검색어",placeholder="🔍 검색어 입력...",label_visibility="collapsed",key="sk")

    with st.expander("🔧 필터"):
        fc1,fc2,fc3=st.columns(3)
        ftype=fc1.multiselect("타입필터",["노트","태스크","일정"],default=["노트","태스크","일정"],label_visibility="collapsed")
        fdate=fc2.selectbox("기간필터",["전체","최근 7일","최근 30일","이번 달"],label_visibility="collapsed")
        fsort=fc3.selectbox("정렬필터",["최신순","관련도순"],label_visibility="collapsed")

    if kw2 and DB:
        results=search_all(uid,kw2)
        type_map={"note":"노트","task":"태스크","event":"일정"}
        if ftype: results=[r for r in results if type_map.get(r["type"],"") in ftype]
        if fdate!="전체":
            days_map={"최근 7일":7,"최근 30일":30,"이번 달":(today_kst()-today_kst().replace(day=1)).days+1}
            cutoff=str(today_kst()-timedelta(days=days_map.get(fdate,999)))
            results=[r for r in results if r.get("date","")>=cutoff]

        if results:
            st.caption(f"{len(results)}개 결과")
            all_n=cached_get_notes(uid); all_t=cached_get_tasks(uid)
            nr=[r for r in results if r["type"]=="note"]
            tr=[r for r in results if r["type"]=="task"]
            er=[r for r in results if r["type"]=="event"]
            if nr:
                st.markdown(f'<div class="pa-section">📝 노트 ({len(nr)})</div>',unsafe_allow_html=True)
                for r in nr:
                    tg=[n for n in all_n if n["id"]==r["id"]]
                    prev=tg[0].get("content","")[:60].replace("\n"," ") if tg else ""
                    c1,c2=st.columns([5,1])
                    c1.markdown(f'<b style="color:{D["text"]}">{r["title"]}</b> <span style="color:{D["text3"]};font-size:11px">{r.get("date","")}</span>{"<div style=font-size:12px;color:"+D["text3"]+">"+prev+"</div>" if prev else ""}',unsafe_allow_html=True)
                    if c2.button("열기",key=f"srn_{r['id']}"):
                        if tg: st.session_state.editing_note=tg[0]; st.session_state.current_page="Notes"; clear_nc(); clear_ai(); st.rerun()
            if tr:
                st.markdown(f'<div class="pa-section">✅ 태스크 ({len(tr)})</div>',unsafe_allow_html=True)
                for r in tr:
                    c1,c2=st.columns([5,1]); c1.markdown(f'<b style="color:{D["text"]}">{r["title"]}</b> <span style="color:{D["text3"]};font-size:11px">{r.get("date","")}</span>',unsafe_allow_html=True)
                    if c2.button("열기",key=f"srt_{r['id']}"):
                        tg=[t for t in all_t if t["id"]==r["id"]]
                        if tg: st.session_state.editing_task=tg[0]; st.session_state.current_page="Tasks"; st.rerun()
            if er:
                st.markdown(f'<div class="pa-section">📅 일정 ({len(er)})</div>',unsafe_allow_html=True)
                for r in er:
                    c1,c2=st.columns([5,1]); c1.markdown(f'<b style="color:{D["text"]}">{r["title"]}</b> <span style="color:{D["text3"]};font-size:11px">{r.get("date","")}</span>',unsafe_allow_html=True)
                    if c2.button("열기",key=f"sre_{r['id']}"):
                        try: st.session_state.cal_prefill_date=date.fromisoformat(r.get("date",""))
                        except: st.session_state.cal_prefill_date=today_kst()
                        st.session_state.current_page="Calendar"; st.rerun()
        else: st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">🔍</div><p style="color:{D["text3"]}">결과 없음</p></div>',unsafe_allow_html=True)
    elif not kw2:
        st.markdown(f'<div class="pa-empty"><div class="pa-empty-icon">🔍</div><p style="color:{D["text3"]}">검색어를 입력하세요<br><small>노트, 태스크, 일정을 한 번에 검색</small></p></div>',unsafe_allow_html=True)

# ===== STATISTICS =====
elif page=="Statistics":
    section("통계","노트, 태스크, 습관 활동 분석")
    if DB:
        today=today_kst()
        dr1,_=st.columns([2,3])
        stat_range=dr1.selectbox("통계기간",["최근 7일","최근 30일","이번 달","올해"],label_visibility="collapsed",key="stat_range")
        if stat_range=="최근 7일": s_start=today-timedelta(7)
        elif stat_range=="최근 30일": s_start=today-timedelta(30)
        elif stat_range=="이번 달": s_start=today.replace(day=1)
        else: s_start=today.replace(month=1,day=1)
        all_notes=cached_get_notes(uid); all_tasks=cached_get_tasks(uid); all_habits=cached_get_habits(uid)
        pomo_logs=get_pomo_logs(uid,(today-s_start).days+1)
        period_notes=[n for n in all_notes if n.get("updated_at","")[:10]>=str(s_start)]
        done_tasks=[t for t in all_tasks if t["status"]=="done"]
        complete_pomo=[l for l in pomo_logs if l.get("status","complete")=="complete"]
        ws_d=today-timedelta(days=today.weekday())
        wl=get_habit_logs(uid,ws_d,today)
        habit_rate=int(len([l for l in wl if l.get("completed")])/max(len(all_habits)*(today.weekday()+1),1)*100) if all_habits else 0
        m1,m2,m3,m4=st.columns(4)
        m1.metric("작성 노트",len(period_notes)); m2.metric("완료 태스크",len(done_tasks))
        m3.metric("뽀모도로",f"{len(complete_pomo)}회"); m4.metric("습관 달성률",f"{habit_rate}%")
        st.markdown("---")
        st.markdown(f'<div class="pa-section">노트 활동 (최근 14일)</div>', unsafe_allow_html=True)
        daily_counts={str(today-timedelta(i)):len([n for n in all_notes if n.get("updated_at","")[:10]==str(today-timedelta(i))]) for i in range(14)}
        max_c=max(daily_counts.values()) if any(daily_counts.values()) else 1
        chart_parts=['<div style="display:flex;align-items:flex-end;gap:3px;height:80px">']
        for i in range(13,-1,-1):
            d=str(today-timedelta(i)); cnt=daily_counts.get(d,0)
            h2=int((cnt/max(max_c,1))*70) if cnt>0 else 3
            col_c=D["accent"] if i==0 else D["accent"]+"55"
            chart_parts.append(f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:1px"><div style="font-size:9px;color:{D["text3"]}">{cnt if cnt>0 else ""}</div><div style="width:100%;height:{h2}px;background:{col_c};border-radius:2px 2px 0 0;min-height:3px"></div><div style="font-size:9px;color:{D["text3"]}">{(today-timedelta(i)).strftime("%d")}</div></div>')
        chart_parts.append('</div>')
        st.markdown("".join(chart_parts), unsafe_allow_html=True)
        st.markdown("---")
        cl1,cl2=st.columns(2)
        with cl1:
            st.markdown(f'<div class="pa-section">태스크 현황</div>', unsafe_allow_html=True)
            sc_map={"backlog":("#94A3B8","Backlog"),"todo":(D["accent"],"To Do"),"doing":(D["warning"],"진행 중"),"done":(D["success"],"완료")}
            total_t=max(len(all_tasks),1)
            for s2,(sc2,slbl) in sc_map.items():
                cnt2=len([t for t in all_tasks if t["status"]==s2]); pct2=int(cnt2/total_t*100)
                st.markdown(f'<div style="margin:5px 0"><div style="display:flex;justify-content:space-between;font-size:12px;color:{D["text2"]};margin-bottom:3px"><span>{slbl}</span><span>{cnt2}개 ({pct2}%)</span></div><div style="height:6px;background:{D["surface2"]};border-radius:99px;overflow:hidden"><div style="height:100%;width:{pct2}%;background:{sc2};border-radius:99px"></div></div></div>', unsafe_allow_html=True)
        with cl2:
            st.markdown(f'<div class="pa-section">습관 달성 현황</div>', unsafe_allow_html=True)
            if all_habits:
                for h in all_habits[:5]:
                    hl2=[l for l in wl if l["habit_id"]==h["id"] and l.get("completed")]
                    dd2=len(hl2); dt3=today.weekday()+1; ph2=int(dd2/max(dt3,1)*100)
                    hc2=D["success"] if ph2>=80 else D["warning"] if ph2>=50 else D["danger"]
                    st.markdown(f'<div style="margin:5px 0"><div style="display:flex;justify-content:space-between;font-size:12px;color:{D["text2"]};margin-bottom:3px"><span>{h.get("icon","✅")} {h["name"]}</span><span style="color:{hc2}">{dd2}/{dt3}일</span></div><div style="height:6px;background:{D["surface2"]};border-radius:99px;overflow:hidden"><div style="height:100%;width:{ph2}%;background:{hc2};border-radius:99px"></div></div></div>', unsafe_allow_html=True)
            else: st.caption("습관 없음")

# ===== AI CONTENT =====
elif page=="AI Content":
    section("AI Content 생성")
    ct=st.selectbox("콘텐츠유형",["Blog","Instagram","Twitter Thread","Full Package"],label_visibility="collapsed")
    topic=st.text_area("주제입력",placeholder="예: AI가 업무 생산성을 높이는 방법",label_visibility="collapsed",height=80)
    kw=st.text_input("키워드입력",label_visibility="collapsed",placeholder="키워드")
    img=st.file_uploader("이미지업로드",type=["png","jpg","jpeg"],key="ci",label_visibility="collapsed")
    eng=st.radio("AI엔진",["Auto","Gemini","Claude"],horizontal=True,label_visibility="collapsed")
    if st.button("생성",type="primary",use_container_width=True):
        if topic:
            with st.spinner("생성 중..."):
                em={"Auto":"auto","Gemini":"gemini","Claude":"claude"}
                prompts={"Blog":f"주제:{topic}\n키워드:{kw}\n\n블로그: 제목3개, SEO메타, 본문1500자, 해시태그10개",
                         "Instagram":f"주제:{topic}\n키워드:{kw}\n\n인스타: 훅, 본문, 해시태그30개",
                         "Twitter Thread":f"주제:{topic}\n키워드:{kw}\n\n트위터 5-8개"}
                result=""
                if ct=="Full Package":
                    for tn in ["Blog","Instagram","Twitter Thread"]:
                        st.markdown(f"### {tn}"); part=get_ai(prompts[tn],em[eng],"content"); st.markdown(part); result+=f"\n\n## {tn}\n"+part
                else: result=get_ai(prompts.get(ct,""),em[eng],"content"); st.markdown(result)
                if result:
                    s1,s2=st.columns(2)
                    if s1.button("노트 저장",key="cs"):
                        if DB: create_note(uid,f"[Content] {topic[:30]}",result); invalidate_cache(); st.success("저장됨")
                    s2.download_button("다운로드",result,f"content.txt","text/plain")

# ===== ECONOMY =====
elif page=="Economy":
    section("Economy")
    tabs=st.tabs(["대시보드","수입/지출","시장","AI 분석"])
    with tabs[0]:
        if DB:
            cm2=now_kst().strftime("%Y-%m"); exps=get_expenses(uid,cm2); inc=get_income(uid,cm2); loans=get_loans(uid)
            te=sum(e.get("amount",0) for e in exps); ti=sum(i.get("amount",0) for i in inc); tl=sum(l.get("remaining_amount",0) for l in loans)
            c1,c2,c3,c4=st.columns(4)
            c1.metric("수입",f"{ti:,}₩"); c2.metric("지출",f"{te:,}₩"); c3.metric("잔액",f"{ti-te:,}₩"); c4.metric("부채",f"{tl:,}₩")
            if exps:
                cats={}
                for e in exps: cats[e.get("category","기타")]=cats.get(e.get("category","기타"),0)+e.get("amount",0)
                for cat,amt in sorted(cats.items(),key=lambda x:-x[1]):
                    st.progress(min(amt/te,1) if te>0 else 0,text=f"{cat}: {amt:,}₩")
    with tabs[1]:
        sub=st.radio("가계부탭",["지출","수입","대출"],horizontal=True,label_visibility="collapsed")
        if sub=="지출":
            fc1,fc2,fc3=st.columns(3)
            ea=fc1.number_input("금액",min_value=0,step=1000,key="ea"); ecat=fc2.selectbox("카테고리",["식비","교통비","쇼핑","생활비","의료","교육","여가","카페","구독","기타"]); edt=fc3.date_input("지출날짜",key="edt",label_visibility="collapsed")
            if st.button("기록",type="primary",key="re"):
                if ea>0 and DB: add_expense(uid,ea,ecat,"",edt); st.success("기록됨"); st.rerun()
            if DB:
                for e in get_expenses(uid,now_kst().strftime("%Y-%m"))[:15]: st.markdown(f'{e.get("expense_date","")} · {e.get("category","")} · {e.get("amount",0):,}₩')
        elif sub=="수입":
            ic1,ic2=st.columns(2); ia=ic1.number_input("수입금액",min_value=0,step=100000,key="ia"); isrc=ic2.text_input("수입출처",key="isrc")
            if st.button("기록",type="primary",key="ri"):
                if ia>0 and DB: add_income(uid,ia,isrc); st.success("기록됨"); st.rerun()
        elif sub=="대출":
            lc1,lc2=st.columns(2); ln=lc1.text_input("대출이름",key="ln_input"); lt=lc2.number_input("총액",min_value=0,step=1000000,key="lt")
            lr=lc1.number_input("잔액",min_value=0,step=1000000,key="lr"); li=lc2.number_input("금리%",min_value=0.0,step=0.1,key="li")
            if st.button("추가",type="primary",key="al"):
                if ln and DB: add_loan(uid,ln,lt,lr,li); st.success("추가됨"); st.rerun()
            if DB:
                for l in get_loans(uid): st.progress((1-l.get("remaining_amount",0)/max(l.get("total_amount",1),1)),text=f"{l['name']}: {l.get('remaining_amount',0):,}₩")
    with tabs[2]:
        if st.button("최신 시장 정보",type="primary"):
            with st.spinner("..."): st.markdown(get_ai("US(S&P500,NASDAQ)+KR(KOSPI,KOSDAQ)+환율+뉴스5개. 간결하게.",st.session_state.ai_engine,"analysis"))
        wc1,wc2,wc3=st.columns([2,2,1])
        ws2=wc1.text_input("종목코드입력",key="ws2",label_visibility="collapsed",placeholder="종목코드"); wn2=wc2.text_input("종목명입력",key="wn2",label_visibility="collapsed",placeholder="종목명"); wm2=wc3.selectbox("시장",["KR","US"],key="wm2",label_visibility="collapsed")
        if st.button("추가",key="aw"):
            if ws2 and wn2 and DB: add_watch(uid,ws2,wn2,wm2); st.rerun()
        if DB:
            for w in get_watchlist(uid):
                c1,c2=st.columns([5,1]); c1.markdown(f"{'🇺🇸' if w.get('market')=='US' else '🇰🇷'} **{w['name']}** ({w['symbol']})")
                if c2.button("삭제",key=f"dw_{w['id']}"): del_watch(w["id"]); st.rerun()
    with tabs[3]:
        if st.button("AI 분석",type="primary"):
            if DB:
                with st.spinner("..."): st.markdown(analyze_finances(get_expenses(uid,now_kst().strftime("%Y-%m")),get_income(uid,now_kst().strftime("%Y-%m")),get_loans(uid)))

# ===== EMAIL =====
elif page=="Email":
    section("Email 발송")
    st.info("Gmail 앱 비밀번호 필요: Gmail → 보안 → 2단계 인증 → 앱 비밀번호")
    to=st.text_input("받는사람",key="to_input"); subj=st.text_input("제목",key="subj_input"); body=st.text_area("내용",height=200,key="body_input")
    with st.expander("Gmail 설정"):
        ga=st.text_input("Gmail계정",key="ga"); gp=st.text_input("앱비밀번호",type="password",key="gp")
    if st.button("발송",type="primary"):
        if all([to,subj,body,ga,gp]):
            ok,msg=send_gmail(to,subj,body,ga,gp)
            st.success(msg) if ok else st.error(msg)
        else: st.warning("모든 필드를 입력해주세요.")

# ===== SETTINGS =====
elif page=="Settings":
    section("Settings")
    tabs_s=st.tabs(["프로필","API 키","AI 엔진","목표&습관","캘린더 라벨","템플릿","AI 프롬프트","대시보드 문구","협업 공유","메뉴 순서"])

    with tabs_s[0]:
        st.markdown(f'<div class="pa-section">프로필 사진</div>',unsafe_allow_html=True)
        av_url=get_avatar_url(uid) if DB else None
        if av_url: st.image(av_url,width=80)
        uploaded_av=st.file_uploader("사진업로드",type=["png","jpg","jpeg","webp"],key="av_upload")
        if uploaded_av:
            if st.button("사진 저장",type="primary",key="av_save"):
                if DB and upload_avatar(uid,uploaded_av.read(),uploaded_av.type): st.success("저장됨!"); st.rerun()
                else: st.error("업로드 실패 — Supabase Storage avatars 버킷 Public 설정 확인")
        st.markdown("---")
        st.markdown(f'<div class="pa-section">이름</div>',unsafe_allow_html=True)
        nn=st.text_input("표시이름",value=dname,key="sn",label_visibility="collapsed")
        if st.button("업데이트",type="primary"):
            if DB: update_profile(uid,display_name=nn); st.session_state.user["display_name"]=nn; st.success("업데이트됨"); st.rerun()
        st.markdown("---")
        st.markdown(f'<div class="pa-section">비밀번호 변경</div>',unsafe_allow_html=True)
        cp3=st.text_input("현재비밀번호",type="password",key="cp"); np=st.text_input("새비밀번호",type="password",key="np"); np2=st.text_input("비밀번호확인",type="password",key="np2")
        if st.button("변경",key="chpw"):
            if np!=np2: st.error("불일치")
            elif not cp3: st.error("현재 비밀번호 입력")
            elif DB:
                import hashlib; u,err=login_user(user.get("email",""),cp3)
                if u: update_profile(uid,password_hash=hashlib.sha256(np.encode()).hexdigest()); st.success("변경됨!")
                else: st.error("현재 비밀번호 틀림")

    with tabs_s[1]:
        gk=st.text_input("Gemini API Key",value=st.session_state.gemini_api_key,type="password",key="sgk")
        ck=st.text_input("Claude API Key",value=st.session_state.claude_api_key,type="password",key="sck")
        if st.button("저장",type="primary"): st.session_state.gemini_api_key=gk; st.session_state.claude_api_key=ck; st.success("저장됨")
        st.markdown("---")
        st.markdown(f'<div class="pa-section">Google Calendar Secrets</div>',unsafe_allow_html=True)
        st.code('GOOGLE_CLIENT_ID = "..."\nGOOGLE_CLIENT_SECRET = "..."\nREDIRECT_URI = "https://sh-agent.streamlit.app"')

    with tabs_s[2]:
        st.session_state.ai_engine=st.radio("AI엔진선택",["auto","gemini","claude"],format_func=lambda x:{"auto":"Auto","gemini":"Gemini","claude":"Claude"}[x],horizontal=True)
        from ai_engine import GEMINI_MODELS,DEFAULT_MODEL
        mk=list(GEMINI_MODELS.keys()); cm3=st.session_state.get("gemini_model",DEFAULT_MODEL)
        sel=st.selectbox("Gemini모델",mk,format_func=lambda x:GEMINI_MODELS[x],index=mk.index(cm3) if cm3 in mk else 0)
        st.session_state.gemini_model=sel

    with tabs_s[3]:
        hc1,hc2,hc3=st.columns([2,1,1])
        hn=hc1.text_input("습관이름설정",key="hn_s",label_visibility="collapsed",placeholder="이름")
        hi3_cur=st.session_state.get("hi3_val","✅")
        sel_em3=emoji_picker("habit_settings",hi3_cur)
        if sel_em3!=hi3_cur: st.session_state["hi3_val"]=sel_em3; st.rerun()
        hi=sel_em3
        ht2=hc3.selectbox("습관타입설정",["check","numeric"],format_func=lambda x:{"check":"체크","numeric":"수치"}[x],key="ht2")
        htr2=1.0; hu2=""
        if ht2=="numeric":
            hc4,hc5=st.columns(2); htr2=hc4.number_input("목표값설정",min_value=0.1,value=1.0,step=0.5,key="htr2"); hu2=hc5.text_input("단위설정",key="hu2")
        if st.button("추가",key="hah2",type="primary"):
            if hn and DB: create_habit_v2(uid,hn,hi,ht2,htr2,hu2); cached_get_habits.clear(); st.rerun()
        if DB:
            for h in cached_get_habits(uid):
                c1,c2=st.columns([5,1]); c1.markdown(f"{h.get('icon','✅')} {h['name']}")
                if c2.button("삭제",key=f"dhs_{h['id']}"): delete_habit(h["id"]); cached_get_habits.clear(); st.rerun()

    with tabs_s[4]:
        if DB:
            cl2=get_color_labels(uid)
            for ck2,hv in COLOR_PRESETS.items():
                cur=cl2.get(ck2,{}).get("label",ck2.capitalize())
                ca,cb,cc=st.columns([1,3,1])
                ca.markdown(f'<div style="width:20px;height:20px;background:{hv};border-radius:50%;margin-top:8px"></div>',unsafe_allow_html=True)
                nl=cb.text_input("라벨이름",value=cur,key=f"lbl_{ck2}",label_visibility="collapsed")
                if cc.button("저장",key=f"slbl_{ck2}"): set_color_label(uid,ck2,nl,hv); st.success("저장됨"); st.rerun()

    with tabs_s[5]:
        with st.expander("기본 타입별 템플릿 수정"):
            ts=st.selectbox("템플릿타입",["meeting","idea","project","daily"],format_func=lambda x:{"meeting":"Meeting","idea":"Idea","project":"Project","daily":"Daily"}[x],key="dts")
            ed2=get_note_template(uid,ts) if DB else get_default_templates().get(ts,"")
            nd2=st.text_area("템플릿내용",value=ed2,height=200,key="dtc",label_visibility="collapsed")
            if st.button("저장",key="sdtm",type="primary"):
                if DB:
                    at2=get_templates(uid)
                    for t in at2:
                        if t.get("note_type")==f"default_{ts}": delete_template(t["id"])
                    create_template(uid,f"기본_{ts}",nd2,note_type=f"default_{ts}",icon="📝"); st.success("저장됨!")
        st.markdown("---")
        tn=st.text_input("템플릿이름",key="tn2",placeholder="이름"); ti3=st.text_input("템플릿아이콘",value="📄",key="ti3",placeholder="아이콘"); tc3=st.text_area("커스텀내용",height=150,key="tc3",label_visibility="collapsed")
        if st.button("커스텀 템플릿 저장",key="stb",type="primary"):
            if tn and tc3 and DB: create_template(uid,tn,tc3,icon=ti3); st.success("저장됨"); st.rerun()
        if DB:
            for t in get_templates(uid):
                if t.get("note_type") not in ["report_template","ai_prompt","pomo_prompt"] and not t.get("note_type","").startswith("default_"):
                    c1,c2=st.columns([5,1]); c1.markdown(f"{t.get('icon','📄')} {t['name']}")
                    if c2.button("삭제",key=f"dt_{t['id']}"): delete_template(t["id"]); st.rerun()

    with tabs_s[6]:
        pt=st.selectbox("프롬프트카테고리",["Summary용","Expand용","Pomodoro 분석용"],key="pt3"); pn2=st.text_input("프롬프트이름",key="pn2",placeholder="이름"); pc3=st.text_area("프롬프트내용",height=100,key="pc3",label_visibility="collapsed")
        cm4={"Summary용":("ai_prompt","📝"),"Expand용":("ai_prompt","✨"),"Pomodoro 분석용":("pomo_prompt","🍅")}
        if st.button("저장",key="sap",type="primary"):
            if pn2 and pc3 and DB:
                nt2,ic2=cm4[pt]; create_template(uid,pn2,pc3,note_type=nt2,icon=ic2); st.success("저장됨"); st.rerun()
        if DB:
            for t in get_templates(uid):
                if t.get("note_type") in ["ai_prompt","pomo_prompt"]:
                    c1,c2=st.columns([5,1]); c1.markdown(f"{t.get('icon','🤖')} {t['name']}")
                    if c2.button("삭제",key=f"dap_{t['id']}"): delete_template(t["id"]); st.rerun()

    with tabs_s[7]:
        st.markdown(f'<div class="pa-section">대시보드 오늘의 문구</div>',unsafe_allow_html=True)
        st.caption("매일 한 번 AI가 생성하거나 직접 입력한 문구가 대시보드에 표시됩니다")
        user_data=user if user else {}
        settings_str=user_data.get("settings") or "{}"
        try: us=json.loads(settings_str) if isinstance(settings_str,str) else (settings_str or {})
        except: us={}
        qt_opts={"motivational":"명언 (매일 업데이트)","bible":"성경 구절 - 개역개정 (매일 업데이트)","both":"명언 + 성경 구절 모두","manual":"직접 입력","none":"표시 안 함"}
        cur_qt=us.get("quote_type","motivational")
        new_qt=st.selectbox("문구유형",list(qt_opts.keys()),format_func=lambda x:qt_opts[x],index=list(qt_opts.keys()).index(cur_qt) if cur_qt in qt_opts else 0,key="qt_sel")
        manual_q=""
        if new_qt=="manual":
            manual_q=st.text_area("직접입력문구",value=us.get("manual_quote",""),height=100,key="mq",placeholder="내가 되새기고 싶은 문구를 입력하세요...")
        if st.button("저장",type="primary",key="save_qt"):
            if DB:
                us["quote_type"]=new_qt
                if new_qt=="manual": us["manual_quote"]=manual_q
                update_profile(uid,settings=json.dumps(us,ensure_ascii=False))
                st.session_state.user=get_user_by_id(uid)
                for k in list(st.session_state.keys()):
                    if k.startswith("quote_"): del st.session_state[k]
                st.success("저장됨!"); st.rerun()
        if new_qt in ["bible","motivational","both"] and new_qt!="none":
            if st.button("미리보기",key="pq"):
                for qt3 in (["bible","motivational"] if new_qt=="both" else [new_qt]):
                    q=get_daily_quote(uid,qt3)
                    if q:
                        lines=q.strip().split("\n"); text=lines[0]; ref=lines[1] if len(lines)>1 else ""
                        st.markdown(f'<div class="pa-quote"><div class="pa-quote-text">"{text}"</div>{"<div class=pa-quote-ref>"+ref+"</div>" if ref else ""}</div>',unsafe_allow_html=True)

    with tabs_s[8]:
        st.markdown(f'<div class="pa-section">내 앱 공유하기</div>', unsafe_allow_html=True)
        st.info("💡 먼저 Supabase SQL Editor에서 sharing_setup.sql을 실행해야 합니다")
        sh1,sh2=st.columns([3,1])
        share_email=sh1.text_input("공유이메일",placeholder="friend@example.com",key="share_email")
        share_perm=sh2.selectbox("공유권한",["view","edit"],format_func=lambda x:{"view":"👁️ 보기","edit":"✏️ 편집"}[x],key="share_perm")
        if st.button("공유 추가",type="primary",key="add_share"):
            if share_email and DB:
                try:
                    name,err=add_shared_access(uid,share_email,share_perm)
                    if name: st.success(f"✅ {name}님과 공유됨!")
                    else: st.error(err or "공유 실패")
                except: st.error("공유 기능을 사용하려면 Supabase에 shared_access 테이블이 필요합니다")
        if DB:
            try:
                shared=get_shared_users(uid)
                if shared:
                    st.markdown(f'<div class="pa-section">공유 중인 사용자</div>', unsafe_allow_html=True)
                    for s in shared:
                        sc1,sc2=st.columns([4,1])
                        perm_icon="👁️" if s.get("permission")=="view" else "✏️"
                        sc1.markdown(f"{perm_icon} {s.get('shared_email','')} ({s.get('permission','')})")
                        if sc2.button("취소",key=f"rm_share_{s['id']}"): remove_shared_access(uid,s["shared_with_id"]); st.rerun()
            except: st.caption("공유 기능 미설정")
        st.markdown("---")
        st.markdown(f'<div class="pa-section">공유받은 앱</div>', unsafe_allow_html=True)
        if DB:
            try:
                accesses=get_my_accesses(uid)
                if accesses:
                    for a in accesses:
                        owner=a.get("profiles",{})
                        owner_name=owner.get("display_name","") if isinstance(owner,dict) else ""
                        perm_icon2="👁️" if a.get("permission")=="view" else "✏️"
                        st.markdown(f"{perm_icon2} **{owner_name}**님의 앱")
                else: st.caption("공유받은 앱 없음")
            except: st.caption("공유 기능 미설정")

    with tabs_s[9]:
        st.markdown(f'<div class="pa-section">사이드바 메뉴 순서</div>',unsafe_allow_html=True)
        st.caption("↑↓ 버튼으로 순서를 변경하세요. 변경사항은 즉시 적용됩니다.")
        current_order = get_pages()
        for i, pg in enumerate(current_order):
            c1,c2,c3=st.columns([5,1,1])
            c1.markdown(f'<div style="padding:6px 0;font-size:13px;color:{D["text"]}">{pg}</div>',unsafe_allow_html=True)
            if i>0 and c2.button("↑",key=f"mu_{i}"):
                new_order=list(current_order)
                new_order[i],new_order[i-1]=new_order[i-1],new_order[i]
                st.session_state.sidebar_pages_order=new_order; st.rerun()
            if i<len(current_order)-1 and c3.button("↓",key=f"md_{i}"):
                new_order=list(current_order)
                new_order[i],new_order[i+1]=new_order[i+1],new_order[i]
                st.session_state.sidebar_pages_order=new_order; st.rerun()
        if st.button("기본값으로 초기화",use_container_width=True):
            st.session_state.sidebar_pages_order=None; st.rerun()

st.markdown(f'<div style="height:1px;background:{D["border"]};margin:32px 0 8px"></div><p style="font-size:11px;color:{D["text3"]};text-align:center">Personal Assistant v7.1</p>',unsafe_allow_html=True)
