"""
DB 유틸리티 - Supabase 연동
"""
import hashlib
import streamlit as st
from supabase import create_client
from datetime import datetime, date
import json

def get_supabase():
    """Supabase 클라이언트 반환"""
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ===== 사용자 인증 =====
def register_user(email, password, display_name):
    sb = get_supabase()
    if not sb:
        return None, "DB 연결 실패"
    try:
        existing = sb.table("profiles").select("id").eq("email", email).execute()
        if existing.data:
            return None, "이미 등록된 이메일입니다"
        result = sb.table("profiles").insert({
            "email": email,
            "password_hash": hash_password(password),
            "display_name": display_name
        }).execute()
        return result.data[0] if result.data else None, None
    except Exception as e:
        return None, str(e)

def login_user(email, password):
    sb = get_supabase()
    if not sb:
        return None, "DB 연결 실패"
    try:
        result = sb.table("profiles").select("*").eq("email", email).eq("password_hash", hash_password(password)).execute()
        if result.data:
            return result.data[0], None
        return None, "이메일 또는 비밀번호가 잘못되었습니다"
    except Exception as e:
        return None, str(e)

# ===== 노트 CRUD =====
def get_notes(user_id, note_type=None, search=None, favorites_only=False, include_deleted=False):
    sb = get_supabase()
    if not sb:
        return []
    try:
        query = sb.table("notes").select("*").eq("user_id", user_id)
        if not include_deleted:
            query = query.eq("is_deleted", False)
        if note_type:
            query = query.eq("note_type", note_type)
        if favorites_only:
            query = query.eq("is_favorite", True)
        if search:
            query = query.or_(f"title.ilike.%{search}%,content.ilike.%{search}%")
        result = query.order("updated_at", desc=True).execute()
        return result.data or []
    except:
        return []

def create_note(user_id, title, content="", note_type="note", template=None, is_daily=False, daily_date=None):
    sb = get_supabase()
    if not sb:
        return None
    try:
        data = {
            "user_id": user_id,
            "title": title,
            "content": content,
            "note_type": note_type,
            "template": template,
            "is_daily": is_daily,
            "daily_date": str(daily_date) if daily_date else None
        }
        result = sb.table("notes").insert(data).execute()
        return result.data[0] if result.data else None
    except:
        return None

def update_note(note_id, **kwargs):
    sb = get_supabase()
    if not sb:
        return False
    try:
        kwargs["updated_at"] = datetime.now().isoformat()
        sb.table("notes").update(kwargs).eq("id", note_id).execute()
        return True
    except:
        return False

def delete_note(note_id, permanent=False):
    sb = get_supabase()
    if not sb:
        return False
    try:
        if permanent:
            sb.table("notes").delete().eq("id", note_id).execute()
        else:
            update_note(note_id, is_deleted=True)
        return True
    except:
        return False

def get_daily_note(user_id, target_date=None):
    sb = get_supabase()
    if not sb:
        return None
    target = target_date or date.today()
    try:
        result = sb.table("notes").select("*").eq("user_id", user_id).eq("is_daily", True).eq("daily_date", str(target)).execute()
        if result.data:
            return result.data[0]
        return create_note(user_id, f"📅 {target.strftime('%Y년 %m월 %d일')}", "## 오늘의 메모\n\n\n## 할 일\n\n- [ ] \n\n## 아이디어\n\n", "daily", is_daily=True, daily_date=target)
    except:
        return None

# ===== 태그 =====
def get_tags(user_id):
    sb = get_supabase()
    if not sb:
        return []
    try:
        result = sb.table("tags").select("*").eq("user_id", user_id).execute()
        return result.data or []
    except:
        return []

def add_tag(user_id, name, color="#6366f1"):
    sb = get_supabase()
    if not sb:
        return None
    try:
        result = sb.table("tags").upsert({"user_id": user_id, "name": name, "color": color}).execute()
        return result.data[0] if result.data else None
    except:
        return None

def tag_note(note_id, tag_id):
    sb = get_supabase()
    if not sb:
        return False
    try:
        sb.table("note_tags").upsert({"note_id": note_id, "tag_id": tag_id}).execute()
        return True
    except:
        return False

def get_note_tags(note_id):
    sb = get_supabase()
    if not sb:
        return []
    try:
        result = sb.table("note_tags").select("tag_id, tags(name, color)").eq("note_id", note_id).execute()
        return result.data or []
    except:
        return []

# ===== 노트 링크 (양방향) =====
def link_notes(source_id, target_id):
    sb = get_supabase()
    if not sb:
        return False
    try:
        sb.table("note_links").upsert({"source_id": source_id, "target_id": target_id}).execute()
        sb.table("note_links").upsert({"source_id": target_id, "target_id": source_id}).execute()
        return True
    except:
        return False

def get_linked_notes(note_id):
    sb = get_supabase()
    if not sb:
        return []
    try:
        result = sb.table("note_links").select("target_id, notes!note_links_target_id_fkey(id, title)").eq("source_id", note_id).execute()
        return result.data or []
    except:
        return []

# ===== 태스크 =====
def get_tasks(user_id, status=None, project=None):
    sb = get_supabase()
    if not sb:
        return []
    try:
        query = sb.table("tasks").select("*").eq("user_id", user_id)
        if status:
            query = query.eq("status", status)
        if project:
            query = query.eq("project", project)
        result = query.order("created_at", desc=True).execute()
        return result.data or []
    except:
        return []

def create_task(user_id, title, description="", status="todo", priority="medium", due_date=None, project=None, note_id=None):
    sb = get_supabase()
    if not sb:
        return None
    try:
        data = {
            "user_id": user_id, "title": title, "description": description,
            "status": status, "priority": priority, "project": project, "note_id": note_id
        }
        if due_date:
            data["due_date"] = str(due_date)
        result = sb.table("tasks").insert(data).execute()
        return result.data[0] if result.data else None
    except:
        return None

def update_task(task_id, **kwargs):
    sb = get_supabase()
    if not sb:
        return False
    try:
        kwargs["updated_at"] = datetime.now().isoformat()
        sb.table("tasks").update(kwargs).eq("id", task_id).execute()
        return True
    except:
        return False

def delete_task(task_id):
    sb = get_supabase()
    if not sb:
        return False
    try:
        sb.table("tasks").delete().eq("id", task_id).execute()
        return True
    except:
        return False

# ===== 캘린더 =====
def get_events(user_id, start_date=None, end_date=None):
    sb = get_supabase()
    if not sb:
        return []
    try:
        query = sb.table("calendar_events").select("*").eq("user_id", user_id)
        if start_date:
            query = query.gte("start_time", start_date.isoformat())
        if end_date:
            query = query.lte("start_time", end_date.isoformat())
        result = query.order("start_time").execute()
        return result.data or []
    except:
        return []

def create_event(user_id, title, start_time, end_time=None, description="", color="#3b82f6"):
    sb = get_supabase()
    if not sb:
        return None
    try:
        data = {
            "user_id": user_id, "title": title, "start_time": start_time.isoformat(),
            "description": description, "color": color
        }
        if end_time:
            data["end_time"] = end_time.isoformat()
        result = sb.table("calendar_events").insert(data).execute()
        return result.data[0] if result.data else None
    except:
        return None

def delete_event(event_id):
    sb = get_supabase()
    if not sb:
        return False
    try:
        sb.table("calendar_events").delete().eq("id", event_id).execute()
        return True
    except:
        return False

# ===== 지출 =====
def get_expenses(user_id, month=None):
    sb = get_supabase()
    if not sb:
        return []
    try:
        query = sb.table("expenses").select("*").eq("user_id", user_id)
        if month:
            start = f"{month}-01"
            if month[5:7] == "12":
                end = f"{int(month[:4])+1}-01-01"
            else:
                end = f"{month[:5]}{int(month[5:7])+1:02d}-01"
            query = query.gte("expense_date", start).lt("expense_date", end)
        result = query.order("expense_date", desc=True).execute()
        return result.data or []
    except:
        return []

def add_expense(user_id, amount, category, description="", expense_date=None):
    sb = get_supabase()
    if not sb:
        return None
    try:
        data = {
            "user_id": user_id, "amount": amount, "category": category,
            "description": description, "expense_date": str(expense_date or date.today())
        }
        result = sb.table("expenses").insert(data).execute()
        return result.data[0] if result.data else None
    except:
        return None

# ===== 전사 용어 사전 =====
def get_custom_terms(user_id):
    sb = get_supabase()
    if not sb:
        return {}
    try:
        result = sb.table("custom_terms").select("*").eq("user_id", user_id).execute()
        return {r["wrong_term"]: r["correct_term"] for r in (result.data or [])}
    except:
        return {}

def add_custom_term(user_id, wrong_term, correct_term):
    sb = get_supabase()
    if not sb:
        return False
    try:
        sb.table("custom_terms").upsert({
            "user_id": user_id, "wrong_term": wrong_term, "correct_term": correct_term
        }).execute()
        return True
    except:
        return False

def apply_custom_terms(user_id, text):
    terms = get_custom_terms(user_id)
    for wrong, correct in terms.items():
        text = text.replace(wrong, correct)
    return text
