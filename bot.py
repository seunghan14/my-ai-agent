"""
Personal Assistant Telegram Bot
- 텔레그램에서 AI 질문, 노트/태스크 추가 가능
- Render 배포용 (webhook 방식)
- 환경변수: BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, ALLOWED_CHAT_IDS
"""
import os, json, logging, hashlib
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, request

# ===== 환경변수 =====
BOT_TOKEN       = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL    = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY    = os.environ.get("SUPABASE_KEY", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
# 허용할 Telegram chat_id (쉼표구분). 비워두면 전체 허용 (비추)
ALLOWED_IDS_RAW = os.environ.get("ALLOWED_CHAT_IDS", "")
ALLOWED_IDS     = set(ALLOWED_IDS_RAW.split(",")) if ALLOWED_IDS_RAW.strip() else set()

KST = timezone(timedelta(hours=9))
def now_kst(): return datetime.now(KST)

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# ===== Supabase 헬퍼 =====
def sb_req(method, path, payload=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        r = requests.request(method, url, headers=headers,
                             json=payload, timeout=10)
        if r.status_code in [200, 201]:
            return r.json()
    except Exception as e:
        logging.error(f"Supabase error: {e}")
    return None

def get_user_by_telegram_id(tg_id):
    """telegram_id로 프로필 조회"""
    data = sb_req("GET", f"profiles?telegram_id=eq.{tg_id}&select=id,display_name,email")
    if data and len(data) > 0:
        return data[0]
    return None

def link_telegram_id(email, pw, tg_id):
    """이메일+비밀번호로 로그인 후 telegram_id 연결"""
    pw_hash = hashlib.sha256(pw.encode()).hexdigest()
    data = sb_req("GET", f"profiles?email=eq.{email}&password_hash=eq.{pw_hash}&select=id,display_name")
    if not data or len(data) == 0:
        return None, "이메일 또는 비밀번호가 틀렸습니다"
    uid = data[0]["id"]
    sb_req("PATCH", f"profiles?id=eq.{uid}", {"telegram_id": str(tg_id)})
    return data[0], None

def create_note_db(uid, title, content):
    return sb_req("POST", "notes", {
        "user_id": uid, "title": title, "content": content,
        "note_type": "note", "created_at": now_kst().isoformat(),
        "updated_at": now_kst().isoformat()
    })

def create_task_db(uid, title):
    return sb_req("POST", "tasks", {
        "user_id": uid, "title": title, "status": "todo",
        "priority": "medium", "created_at": now_kst().isoformat()
    })

def get_recent_notes(uid, limit=5):
    return sb_req("GET", f"notes?user_id=eq.{uid}&order=updated_at.desc&limit={limit}&select=title,updated_at") or []

def get_pending_tasks(uid, limit=5):
    return sb_req("GET", f"tasks?user_id=eq.{uid}&status=in.(todo,doing)&order=created_at.desc&limit={limit}&select=title,status,due_date") or []

# ===== Gemini AI =====
def ask_gemini(prompt):
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY가 설정되지 않았습니다."
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30
        )
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return f"❌ Gemini 오류 ({r.status_code})"
    except Exception as e:
        return f"❌ {e}"

# ===== Telegram 전송 =====
def tg_send(chat_id, text, parse_mode="Markdown"):
    if not BOT_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4096], "parse_mode": parse_mode},
            timeout=10
        )
    except Exception as e:
        logging.error(f"Telegram send error: {e}")

# ===== 사용자 상태 관리 (메모리, 재시작 시 초기화) =====
user_states = {}   # {chat_id: {"state": ..., "data": ...}}

def get_state(chat_id):
    return user_states.get(str(chat_id), {})

def set_state(chat_id, state, data=None):
    user_states[str(chat_id)] = {"state": state, "data": data or {}}

def clear_state(chat_id):
    user_states.pop(str(chat_id), None)

# ===== 메시지 처리 =====
def handle_message(chat_id, text, username):
    chat_id_str = str(chat_id)

    # 접근 제한
    if ALLOWED_IDS and chat_id_str not in ALLOWED_IDS:
        tg_send(chat_id, "⛔ 접근이 허용되지 않았습니다.")
        return

    text = text.strip()
    state = get_state(chat_id)

    # ── 로그인 흐름 ──
    if state.get("state") == "wait_login_pw":
        email = state["data"].get("email", "")
        user, err = link_telegram_id(email, text, chat_id)
        if user:
            clear_state(chat_id)
            tg_send(chat_id, f"✅ 연결 완료! 안녕하세요 *{user.get('display_name','사용자')}*님\n\n/help 로 사용법 확인")
        else:
            clear_state(chat_id)
            tg_send(chat_id, f"❌ 로그인 실패: {err}\n다시 시도하려면 /login")
        return

    if state.get("state") == "wait_login_email":
        set_state(chat_id, "wait_login_pw", {"email": text})
        tg_send(chat_id, "🔒 비밀번호를 입력하세요:")
        return

    # ── 노트/태스크 입력 흐름 ──
    if state.get("state") == "wait_note_content":
        user = get_user_by_telegram_id(chat_id)
        if user:
            title = state["data"].get("title", text[:40])
            create_note_db(user["id"], title, text)
            clear_state(chat_id)
            tg_send(chat_id, f"📝 노트 저장됨!\n*{title}*")
        else:
            clear_state(chat_id)
            tg_send(chat_id, "❌ 로그인이 필요합니다. /login")
        return

    if state.get("state") == "wait_task_title":
        user = get_user_by_telegram_id(chat_id)
        if user:
            create_task_db(user["id"], text)
            clear_state(chat_id)
            tg_send(chat_id, f"✅ 태스크 추가됨!\n*{text}*")
        else:
            clear_state(chat_id)
            tg_send(chat_id, "❌ 로그인이 필요합니다. /login")
        return

    # ── 명령어 ──
    if text.startswith("/start"):
        user = get_user_by_telegram_id(chat_id)
        if user:
            tg_send(chat_id, f"👋 안녕하세요 *{user.get('display_name','사용자')}*님!\n/help 로 사용법 확인")
        else:
            tg_send(chat_id, "👋 Personal Assistant Bot입니다!\n\n먼저 /login 으로 계정을 연결하세요.")
        return

    if text.startswith("/help"):
        tg_send(chat_id, """*📖 사용법*

*계정*
/login — 앱 계정 연결

*빠른 추가*
/note — 노트 빠른 추가
/task — 태스크 빠른 추가
또는 그냥 텍스트 입력 → AI 답변

*조회*
/notes — 최근 노트 5개
/tasks — 진행 중 태스크

*AI*
/ai [질문] — AI에게 질문
또는 질문을 그냥 입력하면 AI 답변
""")
        return

    if text.startswith("/login"):
        set_state(chat_id, "wait_login_email")
        tg_send(chat_id, "📧 앱 계정 이메일을 입력하세요:")
        return

    if text.startswith("/note"):
        user = get_user_by_telegram_id(chat_id)
        if not user:
            tg_send(chat_id, "❌ 먼저 /login 으로 계정을 연결하세요."); return
        args = text[5:].strip()
        if args:
            create_note_db(user["id"], args[:50], args)
            tg_send(chat_id, f"📝 노트 저장됨!\n*{args[:50]}*")
        else:
            set_state(chat_id, "wait_note_content", {"title": f"Telegram {now_kst().strftime('%m/%d %H:%M')}"})
            tg_send(chat_id, "📝 노트 내용을 입력하세요:")
        return

    if text.startswith("/task"):
        user = get_user_by_telegram_id(chat_id)
        if not user:
            tg_send(chat_id, "❌ 먼저 /login 으로 계정을 연결하세요."); return
        args = text[5:].strip()
        if args:
            create_task_db(user["id"], args)
            tg_send(chat_id, f"✅ 태스크 추가됨!\n*{args}*")
        else:
            set_state(chat_id, "wait_task_title")
            tg_send(chat_id, "✅ 태스크 제목을 입력하세요:")
        return

    if text.startswith("/notes"):
        user = get_user_by_telegram_id(chat_id)
        if not user:
            tg_send(chat_id, "❌ 먼저 /login 으로 계정을 연결하세요."); return
        notes = get_recent_notes(user["id"])
        if notes:
            lines = [f"📝 *최근 노트*"]
            for n in notes:
                dt = n.get("updated_at","")[:10]
                lines.append(f"• {n['title'] or '(제목 없음)'} `{dt}`")
            tg_send(chat_id, "\n".join(lines))
        else:
            tg_send(chat_id, "노트가 없습니다.")
        return

    if text.startswith("/tasks"):
        user = get_user_by_telegram_id(chat_id)
        if not user:
            tg_send(chat_id, "❌ 먼저 /login 으로 계정을 연결하세요."); return
        tasks = get_pending_tasks(user["id"])
        if tasks:
            lines = ["✅ *진행 중 태스크*"]
            for t in tasks:
                status_icon = "🔄" if t["status"] == "doing" else "○"
                due = f" `~{t['due_date']}`" if t.get("due_date") else ""
                lines.append(f"{status_icon} {t['title']}{due}")
            tg_send(chat_id, "\n".join(lines))
        else:
            tg_send(chat_id, "진행 중인 태스크가 없습니다. 🎉")
        return

    if text.startswith("/ai "):
        q = text[4:].strip()
        tg_send(chat_id, "🤔 생각 중...")
        answer = ask_gemini(q)
        tg_send(chat_id, answer)
        return

    # ── 일반 텍스트 → AI 답변 ──
    if not text.startswith("/"):
        tg_send(chat_id, "🤔 생각 중...")
        answer = ask_gemini(text)
        tg_send(chat_id, answer)
        return

    tg_send(chat_id, "알 수 없는 명령어입니다. /help 로 사용법 확인")

# ===== Flask Webhook =====
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        msg = data.get("message") or data.get("edited_message")
        if msg:
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            username = msg.get("from", {}).get("username", "")
            if text:
                handle_message(chat_id, text, username)
    except Exception as e:
        logging.error(f"Webhook error: {e}")
    return "ok", 200

@app.route("/health")
def health():
    return {"status": "ok", "time": now_kst().isoformat()}, 200

@app.route("/")
def index():
    return "PA Bot is running 🚀", 200

# ===== Webhook 등록 헬퍼 (최초 1회 실행) =====
def register_webhook(render_url):
    """
    배포 후 한 번만 실행:
    python3 -c "from bot import register_webhook; register_webhook('https://your-app.onrender.com')"
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    webhook_url = f"{render_url}/webhook/{BOT_TOKEN}"
    r = requests.post(url, json={"url": webhook_url})
    print(r.json())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
