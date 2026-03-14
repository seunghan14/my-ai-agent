"""
텔레그램 봇 - 빠른 메모, 조회, 알림
별도 서버에서 실행해야 합니다 (예: Railway, Render 무료 티어)

사용법:
1. @BotFather에서 봇 생성 → 토큰 받기
2. 아래 설정 입력
3. python telegram_bot.py 실행
"""
import os
import json
import requests
from datetime import datetime, date

# ===== 설정 =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "여기에-텔레그램-봇-토큰")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "여기에-supabase-url")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "여기에-supabase-key")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "여기에-gemini-key")

# Supabase 헬퍼
def sb_request(method, table, data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if method == "GET":
        return requests.get(url, headers=headers, params=params).json()
    elif method == "POST":
        return requests.post(url, headers=headers, json=data).json()

# 텔레그램 헬퍼
def send_message(chat_id, text, parse_mode="Markdown"):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode})

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    try:
        return requests.get(url, params=params, timeout=35).json().get("result", [])
    except:
        return []

# 명령어 처리
def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    
    if not text:
        return
    
    # /시작 - 안내
    if text == "/start" or text == "/help":
        help_text = """🚀 *나만의 AI 에이전트 봇*

📝 *메모*: 아무 텍스트 → 노트 자동 저장
✅ */할일 내용* → 태스크 추가
💰 */지출 카테고리 금액* → 지출 기록
🔍 */검색 키워드* → 노트 검색
📋 */오늘* → 오늘 할일 + 일정
📊 */리뷰* → 주간 리뷰
☀️ */브리핑* → 오늘의 브리핑

아무 텍스트를 보내면 자동으로 노트에 저장됩니다!"""
        send_message(chat_id, help_text)
        return
    
    # /할일 - 태스크 추가
    if text.startswith("/할일 ") or text.startswith("/todo "):
        task_text = text.split(" ", 1)[1]
        sb_request("POST", "tasks", {
            "user_id": get_user_id(chat_id),
            "title": task_text,
            "status": "todo",
            "priority": "medium"
        })
        send_message(chat_id, f"✅ 태스크 추가됨: *{task_text}*")
        return
    
    # /지출 - 지출 기록
    if text.startswith("/지출 "):
        parts = text.split(" ")
        if len(parts) >= 3:
            category = parts[1]
            try:
                amount = int(parts[2].replace(",", ""))
                desc = " ".join(parts[3:]) if len(parts) > 3 else ""
                sb_request("POST", "expenses", {
                    "user_id": get_user_id(chat_id),
                    "amount": amount,
                    "category": category,
                    "description": desc,
                    "expense_date": str(date.today())
                })
                send_message(chat_id, f"💰 기록됨: {category} {amount:,}원")
            except:
                send_message(chat_id, "❌ 형식: /지출 카테고리 금액\n예: /지출 식비 12000")
        return
    
    # /검색 - 노트 검색
    if text.startswith("/검색 ") or text.startswith("/search "):
        keyword = text.split(" ", 1)[1]
        user_id = get_user_id(chat_id)
        results = sb_request("GET", "notes", params={
            "user_id": f"eq.{user_id}",
            "is_deleted": "eq.false",
            "or": f"(title.ilike.%{keyword}%,content.ilike.%{keyword}%)",
            "order": "updated_at.desc",
            "limit": "5"
        })
        if results:
            msg = f"🔍 *'{keyword}' 검색 결과:*\n\n"
            for r in results:
                msg += f"📝 *{r['title']}*\n{(r.get('content','')[:80])}...\n\n"
            send_message(chat_id, msg)
        else:
            send_message(chat_id, f"검색 결과가 없습니다: {keyword}")
        return
    
    # /오늘 - 오늘 할일 + 일정
    if text == "/오늘" or text == "/today":
        user_id = get_user_id(chat_id)
        tasks = sb_request("GET", "tasks", params={
            "user_id": f"eq.{user_id}",
            "status": "in.(todo,doing)",
            "order": "priority.desc"
        })
        msg = f"📋 *오늘 현황 ({date.today()})*\n\n"
        if tasks:
            for t in tasks[:10]:
                prio = {"high":"🔴","medium":"🟡","low":"🟢"}.get(t.get("priority",""), "⚪")
                status = {"todo":"할일","doing":"진행중"}.get(t.get("status",""), "")
                msg += f"{prio} [{status}] {t['title']}\n"
        else:
            msg += "할 일이 없어요! 🎉\n"
        send_message(chat_id, msg)
        return
    
    # URL 감지 - 웹 클리퍼
    if text.startswith("http://") or text.startswith("https://"):
        send_message(chat_id, f"🔗 링크 저장됨! AI 요약 기능은 추후 업데이트 예정")
        sb_request("POST", "notes", {
            "user_id": get_user_id(chat_id),
            "title": f"🔗 웹 클립 {datetime.now().strftime('%m/%d %H:%M')}",
            "content": f"URL: {text}",
            "note_type": "note"
        })
        return
    
    # 기본 - 메모로 저장
    sb_request("POST", "notes", {
        "user_id": get_user_id(chat_id),
        "title": f"📱 메모 {datetime.now().strftime('%m/%d %H:%M')}",
        "content": text,
        "note_type": "note"
    })
    send_message(chat_id, "📝 메모 저장됨!")

def get_user_id(chat_id):
    """텔레그램 chat_id로 user_id 조회 (간단 버전: 첫 번째 사용자)"""
    # 실제로는 chat_id와 user_id 매핑 테이블이 필요합니다
    users = sb_request("GET", "profiles", params={"limit": "1"})
    return users[0]["id"] if users else None

# 메인 루프
def main():
    print("🤖 텔레그램 봇 시작!")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "message" in update:
                try:
                    handle_message(update["message"])
                except Exception as e:
                    print(f"Error: {e}")

if __name__ == "__main__":
    main()
