"""DB Utils V4.1 - All Supabase operations"""
import hashlib, streamlit as st
from supabase import create_client
from datetime import datetime, date, timedelta

def get_sb():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key: return None
    return create_client(url, key)

def _q(table):
    sb = get_sb()
    return sb.table(table) if sb else None

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

# === AUTH ===
def register_user(email, pw, name):
    q = _q("profiles")
    if not q: return None, "DB error"
    try:
        if q.select("id").eq("email", email).execute().data: return None, "Email exists"
        r = q.insert({"email": email, "password_hash": hash_pw(pw), "display_name": name}).execute()
        return (r.data[0] if r.data else None), None
    except Exception as e: return None, str(e)

def login_user(email, pw):
    q = _q("profiles")
    if not q: return None, "DB error"
    try:
        r = q.select("*").eq("email", email).eq("password_hash", hash_pw(pw)).execute()
        return (r.data[0], None) if r.data else (None, "Invalid credentials")
    except Exception as e: return None, str(e)

def update_profile(uid, **kw):
    q = _q("profiles")
    if q:
        try: q.update(kw).eq("id", uid).execute(); return True
        except: pass
    return False

# === FOLDERS ===
def get_folders(uid, parent_id=None):
    q = _q("folders")
    if not q: return []
    try:
        query = q.select("*").eq("user_id", uid)
        if parent_id: query = query.eq("parent_id", parent_id)
        else: query = query.is_("parent_id", "null")
        return query.order("sort_order").execute().data or []
    except: return []

def create_folder(uid, name, parent_id=None, icon="📁"):
    q = _q("folders")
    if not q: return None
    try:
        d = {"user_id": uid, "name": name, "icon": icon}
        if parent_id: d["parent_id"] = parent_id
        return q.insert(d).execute().data[0]
    except: return None

def delete_folder(fid):
    q = _q("folders")
    if q:
        try: q.delete().eq("id", fid).execute(); return True
        except: pass
    return False

# === NOTES ===
def get_notes(uid, note_type=None, search=None, fav_only=False, folder_id=None, inc_deleted=False):
    q = _q("notes")
    if not q: return []
    try:
        query = q.select("*").eq("user_id", uid)
        if not inc_deleted: query = query.eq("is_deleted", False)
        if note_type: query = query.eq("note_type", note_type)
        if fav_only: query = query.eq("is_favorite", True)
        if folder_id: query = query.eq("folder_id", folder_id)
        if search: query = query.or_(f"title.ilike.%{search}%,content.ilike.%{search}%")
        return query.order("updated_at", desc=True).execute().data or []
    except: return []

def create_note(uid, title, content="", note_type="note", folder_id=None, is_daily=False, daily_date=None):
    q = _q("notes")
    if not q: return None
    try:
        d = {"user_id": uid, "title": title, "content": content, "note_type": note_type, "is_daily": is_daily}
        if folder_id: d["folder_id"] = folder_id
        if daily_date: d["daily_date"] = str(daily_date)
        return q.insert(d).execute().data[0]
    except: return None

def update_note(nid, **kw):
    q = _q("notes")
    if not q: return False
    try: kw["updated_at"] = datetime.now().isoformat(); q.update(kw).eq("id", nid).execute(); return True
    except: return False

def delete_note(nid, perm=False):
    q = _q("notes")
    if not q: return False
    try:
        if perm: q.delete().eq("id", nid).execute()
        else: update_note(nid, is_deleted=True)
        return True
    except: return False

def get_daily_note(uid, d=None):
    q = _q("notes")
    if not q: return None
    d = d or date.today()
    try:
        r = q.select("*").eq("user_id", uid).eq("is_daily", True).eq("daily_date", str(d)).execute()
        if r.data: return r.data[0]
        return create_note(uid, f"📅 {d.strftime('%Y-%m-%d')}", f"# {d.strftime('%Y-%m-%d %A')}\n\n## Notes\n\n\n## To Do\n\n- [ ] \n\n## Ideas\n\n", "daily", is_daily=True, daily_date=d)
    except: return None

# === TAGS ===
def get_tags(uid):
    q = _q("tags")
    return q.select("*").eq("user_id", uid).execute().data or [] if q else []

def add_tag(uid, name, color="#6366f1"):
    q = _q("tags")
    if not q: return None
    try: return q.upsert({"user_id": uid, "name": name, "color": color}).execute().data[0]
    except: return None

def tag_note(nid, tid):
    q = _q("note_tags")
    if q:
        try: q.upsert({"note_id": nid, "tag_id": tid}).execute(); return True
        except: pass
    return False

# === NOTE LINKS ===
def link_notes(s, t):
    q = _q("note_links")
    if q:
        try: q.upsert({"source_id": s, "target_id": t}).execute(); q.upsert({"source_id": t, "target_id": s}).execute(); return True
        except: pass
    return False

def get_linked_notes(nid):
    q = _q("note_links")
    if not q: return []
    try: return q.select("target_id").eq("source_id", nid).execute().data or []
    except: return []

def get_all_links(uid):
    notes = get_notes(uid)
    nids = [n["id"] for n in notes]
    q = _q("note_links")
    if not q or not nids: return []
    try: return q.select("source_id, target_id").in_("source_id", nids).execute().data or []
    except: return []

# === TEMPLATES ===
def get_templates(uid):
    q = _q("templates")
    return q.select("*").eq("user_id", uid).order("created_at").execute().data or [] if q else []

def create_template(uid, name, content, note_type="note", icon="📄"):
    q = _q("templates")
    if not q: return None
    try: return q.insert({"user_id": uid, "name": name, "content": content, "note_type": note_type, "icon": icon}).execute().data[0]
    except: return None

def delete_template(tid):
    q = _q("templates")
    if q:
        try: q.delete().eq("id", tid).execute(); return True
        except: pass
    return False

# === TASKS ===
def get_tasks(uid, status=None, project=None):
    q = _q("tasks")
    if not q: return []
    try:
        query = q.select("*").eq("user_id", uid)
        if status: query = query.eq("status", status)
        if project: query = query.eq("project", project)
        return query.order("created_at", desc=True).execute().data or []
    except: return []

def create_task(uid, title, desc="", status="todo", prio="medium", due=None, proj=None, nid=None):
    q = _q("tasks")
    if not q: return None
    try:
        d = {"user_id": uid, "title": title, "description": desc, "status": status, "priority": prio, "project": proj, "note_id": nid}
        if due: d["due_date"] = str(due)
        return q.insert(d).execute().data[0]
    except: return None

def update_task(tid, **kw):
    q = _q("tasks")
    if not q: return False
    try: kw["updated_at"] = datetime.now().isoformat(); q.update(kw).eq("id", tid).execute(); return True
    except: return False

def delete_task(tid):
    q = _q("tasks")
    if q:
        try: q.delete().eq("id", tid).execute(); return True
        except: pass
    return False

# === CALENDAR ===
def get_events(uid, start=None, end=None):
    q = _q("calendar_events")
    if not q: return []
    try:
        query = q.select("*").eq("user_id", uid)
        if start: query = query.gte("start_time", start.isoformat())
        if end: query = query.lte("start_time", end.isoformat())
        return query.order("start_time").execute().data or []
    except: return []

def create_event(uid, title, start, end=None, desc="", color_label="blue"):
    q = _q("calendar_events")
    if not q: return None
    try:
        d = {"user_id": uid, "title": title, "start_time": start.isoformat(), "description": desc, "color_label": color_label}
        if end: d["end_time"] = end.isoformat()
        return q.insert(d).execute().data[0]
    except: return None

def delete_event(eid):
    q = _q("calendar_events")
    if q:
        try: q.delete().eq("id", eid).execute(); return True
        except: pass
    return False

def get_color_labels(uid):
    q = _q("color_labels")
    if not q: return {}
    try:
        r = q.select("*").eq("user_id", uid).execute()
        return {d["color_key"]: {"label": d["label"], "hex": d["hex_code"]} for d in (r.data or [])}
    except: return {}

def set_color_label(uid, key, label, hex_code):
    q = _q("color_labels")
    if q:
        try: q.upsert({"user_id": uid, "color_key": key, "label": label, "hex_code": hex_code}).execute(); return True
        except: pass
    return False

# === EXPENSES ===
def get_expenses(uid, month=None):
    q = _q("expenses")
    if not q: return []
    try:
        query = q.select("*").eq("user_id", uid)
        if month:
            y, m = int(month[:4]), int(month[5:7])
            start = f"{month}-01"
            end = f"{y+1}-01-01" if m == 12 else f"{y}-{m+1:02d}-01"
            query = query.gte("expense_date", start).lt("expense_date", end)
        return query.order("expense_date", desc=True).execute().data or []
    except: return []

def add_expense(uid, amt, cat, desc="", d=None):
    q = _q("expenses")
    if not q: return None
    try: return q.insert({"user_id": uid, "amount": amt, "category": cat, "description": desc, "expense_date": str(d or date.today())}).execute().data[0]
    except: return None

def bulk_add_expenses(uid, items):
    q = _q("expenses")
    if not q: return False
    try:
        for e in items:
            q.insert({"user_id": uid, "amount": e["amount"], "category": e["category"],
                      "description": e.get("description",""), "expense_date": e.get("date", str(date.today()))}).execute()
        return True
    except: return False

# === INCOME ===
def get_income(uid, month=None):
    q = _q("income")
    if not q: return []
    try:
        query = q.select("*").eq("user_id", uid)
        if month:
            y, m = int(month[:4]), int(month[5:7])
            query = query.gte("income_date", f"{month}-01").lt("income_date", f"{y+1}-01-01" if m==12 else f"{y}-{m+1:02d}-01")
        return query.order("income_date", desc=True).execute().data or []
    except: return []

def add_income(uid, amt, src, d=None, recurring=False):
    q = _q("income")
    if not q: return None
    try: return q.insert({"user_id": uid, "amount": amt, "source": src, "income_date": str(d or date.today()), "is_recurring": recurring}).execute().data[0]
    except: return None

# === LOANS ===
def get_loans(uid):
    q = _q("loans")
    return q.select("*").eq("user_id", uid).execute().data or [] if q else []

def add_loan(uid, name, total, remaining, rate=0, monthly=0):
    q = _q("loans")
    if not q: return None
    try: return q.insert({"user_id": uid, "name": name, "total_amount": total, "remaining_amount": remaining, "interest_rate": float(rate), "monthly_payment": monthly}).execute().data[0]
    except: return None

def delete_loan(lid):
    q = _q("loans")
    if q:
        try: q.delete().eq("id", lid).execute(); return True
        except: pass
    return False

# === HABITS (V4.1 - numeric support) ===
def get_habits(uid):
    q = _q("habits")
    return q.select("*").eq("user_id", uid).order("created_at").execute().data or [] if q else []

def create_habit(uid, name, icon="✅"):
    q = _q("habits")
    if not q: return None
    try: return q.insert({"user_id": uid, "name": name, "icon": icon}).execute().data[0]
    except: return None

def create_habit_v2(uid, name, icon="✅", habit_type="check", target_value=1, unit=""):
    q = _q("habits")
    if not q: return None
    try:
        return q.insert({"user_id": uid, "name": name, "icon": icon,
                         "habit_type": habit_type, "target_value": float(target_value), "unit": unit}).execute().data[0]
    except:
        try: return q.insert({"user_id": uid, "name": name, "icon": icon}).execute().data[0]
        except: return None

def delete_habit(hid):
    q = _q("habits")
    if q:
        try: q.delete().eq("id", hid).execute(); return True
        except: pass
    return False

def toggle_habit(hid, uid, d=None):
    q = _q("habit_logs")
    if not q: return False
    ds = str(d or date.today())
    try:
        r = q.select("*").eq("habit_id", hid).eq("log_date", ds).execute()
        if r.data:
            q.update({"completed": not r.data[0]["completed"]}).eq("id", r.data[0]["id"]).execute()
        else:
            q.insert({"habit_id": hid, "user_id": uid, "log_date": ds, "completed": True}).execute()
        return True
    except: return False

def toggle_habit_value(hid, uid, value=0, d=None):
    q = _q("habit_logs")
    if not q: return False
    ds = str(d or date.today())
    try:
        r = q.select("*").eq("habit_id", hid).eq("log_date", ds).execute()
        completed = float(value) > 0
        if r.data:
            try: q.update({"completed": completed, "value": float(value)}).eq("id", r.data[0]["id"]).execute()
            except: q.update({"completed": completed}).eq("id", r.data[0]["id"]).execute()
        else:
            try: q.insert({"habit_id": hid, "user_id": uid, "log_date": ds, "completed": completed, "value": float(value)}).execute()
            except: q.insert({"habit_id": hid, "user_id": uid, "log_date": ds, "completed": completed}).execute()
        return True
    except: return False

def get_habit_logs(uid, start, end):
    q = _q("habit_logs")
    if not q: return []
    try: return q.select("*").eq("user_id", uid).gte("log_date", str(start)).lte("log_date", str(end)).execute().data or []
    except: return []

# === WATCHLIST ===
def get_watchlist(uid):
    q = _q("watchlist")
    return q.select("*").eq("user_id", uid).execute().data or [] if q else []

def add_watch(uid, sym, name, mkt="KR"):
    q = _q("watchlist")
    if not q: return None
    try: return q.upsert({"user_id": uid, "symbol": sym, "name": name, "market": mkt}).execute().data[0]
    except: return None

def del_watch(wid):
    q = _q("watchlist")
    if q:
        try: q.delete().eq("id", wid).execute(); return True
        except: pass
    return False

# === POMODORO (V4.1 - status + interruptions) ===
def log_pomo(uid, dur=25, task="", status="complete", interruptions=0):
    q = _q("pomodoro_logs")
    if not q: return None
    try:
        return q.insert({"user_id": uid, "duration_minutes": dur, "task_name": task,
                         "status": status, "interruptions": interruptions}).execute().data[0]
    except:
        try: return q.insert({"user_id": uid, "duration_minutes": dur, "task_name": task}).execute().data[0]
        except: return None

def get_pomo_logs(uid, days=7):
    q = _q("pomodoro_logs")
    if not q: return []
    try: return q.select("*").eq("user_id", uid).gte("completed_at", str(date.today()-timedelta(days=days))).order("completed_at", desc=True).execute().data or []
    except: return []

# === CUSTOM TERMS ===
def get_terms(uid):
    q = _q("custom_terms")
    if not q: return {}
    try: return {r["wrong_term"]: r["correct_term"] for r in (q.select("*").eq("user_id", uid).execute().data or [])}
    except: return {}

def add_term(uid, wrong, correct):
    q = _q("custom_terms")
    if q:
        try: q.upsert({"user_id": uid, "wrong_term": wrong, "correct_term": correct}).execute(); return True
        except: pass
    return False

def apply_terms(uid, text):
    for w, c in get_terms(uid).items(): text = text.replace(w, c)
    return text

# === PINNED ===
def get_pinned(uid):
    q = _q("pinned_items")
    return q.select("*").eq("user_id", uid).order("sort_order").execute().data or [] if q else []

def add_pin(uid, itype, title, iid=None, url=None):
    q = _q("pinned_items")
    if not q: return None
    try: return q.insert({"user_id": uid, "item_type": itype, "title": title, "item_id": iid, "url": url}).execute().data[0]
    except: return None

def del_pin(pid):
    q = _q("pinned_items")
    if q:
        try: q.delete().eq("id", pid).execute(); return True
        except: pass
    return False

# === SEARCH ALL ===
def search_all(uid, keyword):
    results = []
    for n in get_notes(uid, search=keyword):
        results.append({"type": "note", "title": n["title"], "id": n["id"], "date": n.get("updated_at","")[:10]})
    for t in get_tasks(uid):
        if keyword.lower() in t.get("title","").lower():
            results.append({"type": "task", "title": t["title"], "id": t["id"], "date": t.get("created_at","")[:10]})
    for e in get_events(uid):
        if keyword.lower() in e.get("title","").lower():
            results.append({"type": "event", "title": e["title"], "id": e["id"], "date": e.get("start_time","")[:10]})
    return results

# === EXPORT ===
def export_all_notes_md(uid):
    notes = get_notes(uid)
    content = ""
    for n in notes:
        content += f"# {n['title']}\n\nType: {n.get('note_type','note')} | Updated: {n.get('updated_at','')[:10]}\n\n{n.get('content','')}\n\n---\n\n"
    return content
