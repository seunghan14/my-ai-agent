import os, json, requests
from flask import Flask, request, jsonify
from supabase import create_client

app = Flask(__name__)

# ===== 환경변수 =====
BOT_TOKEN       = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL    = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY    = os.environ.get("SUPABASE_KEY", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
ALLOWED_IDS_STR = os.environ.get("ALLOWED_CHAT_IDS", "")

# ALLOWED_CHAT_IDS: 콤마 구분 숫자열 (예: "123456789,987654321")
ALLOWED_CHAT_IDS = set()
for cid in ALLOWED_IDS_STR.split(","):
    cid = cid.strip()
    if cid.isdigit():
        ALLOWED_CHAT_IDS.add(int(cid))

TG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ===== 메모리 상태 (세션 내 유지) =====
user_states = {}   # chat_id → {"uid": ..., "step": ...}

# ===== Supabase =====
def get_sb():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None

# ===== Telegram 헬퍼 =====
def tg_send(chat_id, text, parse_mode="Markdown"):
    """텔레그램 메시지 전송 (3000자 자동 분할)"""
    if not BOT_TOKEN:
        return
    # 긴 메시지 분할
    chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]
    for chunk in chunks:
        try:
            requests.post(f"{TG_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode
            }, timeout=10)
        except Exception as e:
            print(f"tg_send error: {e}")

# ===== Gemini AI =====
def ask_gemini(prompt, context=""):
    if not GEMINI_API_KEY:
        return "Gemini API 키가 설정되지 않았습니다."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    full_prompt = f"{context}\n\n{prompt}" if context else prompt
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    try:
        r = requests.post(url, json=payload, timeout=30)
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"AI 오류: {e}"

# ===== DB 헬퍼 =====
def db_get_user(email, password_hash):
    sb = get_sb()
    if not sb:
        return None
    try:
        import hashlib
        ph = hashlib.sha256(password_hash.encode()).hexdigest() if len(password_hash) != 64 else password_hash
        r = sb.table("profiles").select("*").eq("email", email).eq("password_hash", ph).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None

def db_create_note(uid, title, content):
    sb = get_sb()
    if not sb:
        return False
    try:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=9))).isoformat()
        sb.table("notes").insert({
            "user_id": uid, "title": title, "content": content,
            "note_type": "note", "created_at": now, "updated_at": now
        }).execute()
        return True
    except Exception as e:
        print(f"db_create_note error: {e}")
        return False

def db_create_task(uid, title):
    sb = get_sb()
    if not sb:
        return False
    try:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=9))).isoformat()
        sb.table("tasks").insert({
            "user_id": uid, "title": title, "status": "todo",
            "priority": "medium", "created_at": now, "updated_at": now
        }).execute()
        return True
    except Exception as e:
        print(f"db_create_task error: {e}")
        return False

def db_get_notes(uid, limit=5):
    sb = get_sb()
    if not sb:
        return []
    try:
        r = sb.table("notes").select("title,updated_at").eq("user_id", uid)\
            .order("updated_at", desc=True).limit(limit).execute()
        return r.data or []
    except Exception:
        return []

def db_get_tasks(uid, limit=5):
    sb = get_sb()
    if not sb:
        return []
    try:
        r = sb.table("tasks").select("title,status,priority").eq("user_id", uid)\
            .neq("status", "done").order("created_at", desc=True).limit(limit).execute()
        return r.data or []
    except Exception:
        return []

# ===== 커맨드 핸들러 =====
def handle_start(chat_id):
    tg_send(chat_id, 
        "👋 *Personal Assistant Bot*\n\n"
        "연결된 노트, 태스크, AI 기능을 텔레그램에서 사용할 수 있습니다.\n\n"
        "📌 *명령어*\n"
        "`/help` — 도움말\n"
        "`/login` — 계정 연결\n"
        "`/notes` — 최근 노트 보기\n"
        "`/tasks` — 진행 중 태스크\n"
        "`/note 제목|내용` — 노트 저장\n"
        "`/task 할일` — 태스크 추가\n"
        "`/ai 질문` — AI에게 질문\n\n"
        "💡 *명령어 없이 바로 텍스트를 입력하면 AI가 답변합니다.*"
    )

def handle_help(chat_id):
    handle_start(chat_id)

def handle_login(chat_id):
    state = user_states.get(chat_id, {})
    if state.get("uid"):
        tg_send(chat_id, f"✅ 이미 로그인되어 있습니다.\n계정 연결 해제하려면 `/logout`")
        return
    user_states[chat_id] = {"step": "email"}
    tg_send(chat_id, "📧 이메일을 입력해주세요:")

def handle_logout(chat_id):
    if chat_id in user_states:
        del user_states[chat_id]
    tg_send(chat_id, "👋 로그아웃되었습니다.")

def handle_notes(chat_id):
    state = user_states.get(chat_id, {})
    uid = state.get("uid")
    if not uid:
        tg_send(chat_id, "⚠️ 먼저 `/login`으로 계정을 연결해주세요.")
        return
    notes = db_get_notes(uid)
    if not notes:
        tg_send(chat_id, "📝 저장된 노트가 없습니다.")
        return
    msg = "📝 *최근 노트*\n\n"
    for n in notes:
        title = n.get("title", "(제목 없음)") or "(제목 없음)"
        date = (n.get("updated_at") or "")[:10]
        msg += f"• {title} `{date}`\n"
    tg_send(chat_id, msg)

def handle_tasks(chat_id):
    state = user_states.get(chat_id, {})
    uid = state.get("uid")
    if not uid:
        tg_send(chat_id, "⚠️ 먼저 `/login`으로 계정을 연결해주세요.")
        return
    tasks = db_get_tasks(uid)
    if not tasks:
        tg_send(chat_id, "✅ 진행 중인 태스크가 없습니다!")
        return
    status_icon = {"todo": "○", "doing": "◑", "backlog": "·"}
    prio_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    msg = "✅ *진행 중 태스크*\n\n"
    for t in tasks:
        si = status_icon.get(t.get("status","todo"), "○")
        pi = prio_icon.get(t.get("priority","medium"), "🟡")
        msg += f"{si} {pi} {t.get('title','')}\n"
    tg_send(chat_id, msg)

def handle_note_cmd(chat_id, args, uid):
    if not uid:
        tg_send(chat_id, "⚠️ 먼저 `/login`으로 계정을 연결해주세요.")
        return
    if not args:
        tg_send(chat_id, "사용법: `/note 제목|내용`\n예: `/note 아이디어|오늘 번뜩이는 생각`")
        return
    parts = args.split("|", 1)
    title = parts[0].strip()
    content = parts[1].strip() if len(parts) > 1 else ""
    if db_create_note(uid, title, content):
        tg_send(chat_id, f"📝 노트 저장됨: *{title}*")
    else:
        tg_send(chat_id, "❌ 노트 저장 실패. DB 연결을 확인해주세요.")

def handle_task_cmd(chat_id, args, uid):
    if not uid:
        tg_send(chat_id, "⚠️ 먼저 `/login`으로 계정을 연결해주세요.")
        return
    if not args:
        tg_send(chat_id, "사용법: `/task 할일 내용`\n예: `/task 보고서 작성`")
        return
    if db_create_task(uid, args.strip()):
        tg_send(chat_id, f"✅ 태스크 추가됨: *{args.strip()}*")
    else:
        tg_send(chat_id, "❌ 태스크 추가 실패. DB 연결을 확인해주세요.")

def handle_ai_cmd(chat_id, args):
    if not args:
        tg_send(chat_id, "사용법: `/ai 질문`\n예: `/ai 오늘 날씨 어때?`")
        return
    tg_send(chat_id, "🤔 생각 중...")
    answer = ask_gemini(args)
    tg_send(chat_id, answer)

# ===== 로그인 플로우 =====
def handle_login_flow(chat_id, text):
    state = user_states.get(chat_id, {})
    step = state.get("step")

    if step == "email":
        user_states[chat_id]["email"] = text.strip()
        user_states[chat_id]["step"] = "password"
        tg_send(chat_id, "🔑 비밀번호를 입력해주세요:")
        return True

    if step == "password":
        email = user_states[chat_id].get("email", "")
        user = db_get_user(email, text.strip())
        if user:
            user_states[chat_id] = {"uid": user["id"], "name": user.get("display_name", email)}
            tg_send(chat_id, f"✅ 로그인 성공! 안녕하세요, *{user.get('display_name', email)}*님!")
        else:
            del user_states[chat_id]
            tg_send(chat_id, "❌ 이메일 또는 비밀번호가 올바르지 않습니다.\n다시 시도하려면 `/login`")
        return True

    return False

# ===== 메인 메시지 핸들러 =====
def handle_message(chat_id, text):
    text = (text or "").strip()
    if not text:
        return

    # 로그인 플로우 처리
    state = user_states.get(chat_id, {})
    if state.get("step") in ("email", "password"):
        if handle_login_flow(chat_id, text):
            return

    uid = state.get("uid")

    # 커맨드 처리
    if text.startswith("/"):
        parts = text.split(None, 1)
        cmd = parts[0].lower().split("@")[0]
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/start":        handle_start(chat_id)
        elif cmd == "/help":       handle_help(chat_id)
        elif cmd == "/login":      handle_login(chat_id)
        elif cmd == "/logout":     handle_logout(chat_id)
        elif cmd == "/notes":      handle_notes(chat_id)
        elif cmd == "/tasks":      handle_tasks(chat_id)
        elif cmd == "/note":       handle_note_cmd(chat_id, args, uid)
        elif cmd == "/task":       handle_task_cmd(chat_id, args, uid)
        elif cmd == "/ai":         handle_ai_cmd(chat_id, args)
        else:
            tg_send(chat_id, f"알 수 없는 명령어입니다. `/help`로 도움말을 확인하세요.")
    else:
        # 일반 텍스트 → AI 자동 답변
        tg_send(chat_id, "🤔 생각 중...")
        answer = ask_gemini(text)
        tg_send(chat_id, answer)

# ===== Flask 라우트 =====
@app.route("/", methods=["GET"])
def index():
    """Render 헬스체크 + 슬립 방지"""
    return jsonify({"status": "ok", "service": "PA Telegram Bot"}), 200

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    message = data.get("message") or data.get("edited_message")
    if not message:
        return jsonify({"ok": True})

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return jsonify({"ok": True})

    # 허용된 chat_id 체크 (ALLOWED_CHAT_IDS 비어있으면 모두 허용)
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        print(f"Unauthorized chat_id: {chat_id}")
        return jsonify({"ok": True})

    try:
        handle_message(chat_id, text)
    except Exception as e:
        print(f"handle_message error: {e}")
        try:
            tg_send(chat_id, "⚠️ 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
        except Exception:
            pass

    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
