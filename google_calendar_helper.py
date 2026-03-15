"""Google Calendar Integration Helper"""
import streamlit as st
from datetime import datetime, timedelta, timezone
import json

def get_google_creds():
    """Get Google OAuth credentials from secrets"""
    client_id = st.secrets.get("GOOGLE_CLIENT_ID","")
    client_secret = st.secrets.get("GOOGLE_CLIENT_SECRET","")
    return client_id, client_secret

def get_redirect_uri():
    """Get the redirect URI for OAuth"""
    # Streamlit Cloud URL from secrets or default
    return st.secrets.get("REDIRECT_URI","https://localhost:8501")

def build_auth_url():
    """Build Google OAuth authorization URL"""
    client_id, _ = get_google_creds()
    if not client_id: return None
    redirect_uri = get_redirect_uri()
    scope = "https://www.googleapis.com/auth/calendar"
    import urllib.parse
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)

def exchange_code_for_token(code):
    """Exchange authorization code for access/refresh tokens"""
    import requests
    client_id, client_secret = get_google_creds()
    redirect_uri = get_redirect_uri()
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    if r.status_code == 200:
        return r.json()
    return None

def refresh_access_token(refresh_token):
    """Refresh the access token"""
    import requests
    client_id, client_secret = get_google_creds()
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    })
    if r.status_code == 200:
        return r.json()
    return None

def get_valid_token(uid):
    """Get a valid access token, refreshing if needed"""
    from db_utils import get_google_tokens, save_google_tokens
    tokens = get_google_tokens(uid)
    if not tokens or not tokens.get("refresh_token"):
        return None
    
    # Check if token is expired or will expire in 5 minutes
    expiry_str = tokens.get("token_expiry","")
    now = datetime.now(timezone.utc)
    needs_refresh = True
    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str.replace("Z","+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            needs_refresh = (expiry - now).total_seconds() < 300
        except: pass
    
    if needs_refresh:
        new_tok = refresh_access_token(tokens["refresh_token"])
        if new_tok:
            expiry = now + timedelta(seconds=new_tok.get("expires_in",3600))
            save_google_tokens(uid, new_tok["access_token"], tokens["refresh_token"], expiry.isoformat())
            return new_tok["access_token"]
        return None
    return tokens.get("access_token")

def gcal_get_events(uid, time_min, time_max):
    """Fetch events from Google Calendar"""
    import requests
    token = get_valid_token(uid)
    if not token: return []
    try:
        r = requests.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "timeMin": time_min.isoformat() + "Z" if time_min.tzinfo is None else time_min.isoformat(),
                "timeMax": time_max.isoformat() + "Z" if time_max.tzinfo is None else time_max.isoformat(),
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": 100,
            }
        )
        if r.status_code == 200:
            return r.json().get("items", [])
    except: pass
    return []

def gcal_create_event(uid, title, start_dt, end_dt, desc=""):
    """Create event in Google Calendar"""
    import requests
    token = get_valid_token(uid)
    if not token: return None
    try:
        body = {
            "summary": title,
            "description": desc,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Seoul"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Seoul"},
        }
        r = requests.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body
        )
        if r.status_code in [200, 201]:
            return r.json().get("id")
    except: pass
    return None

def gcal_delete_event(uid, gcal_event_id):
    """Delete event from Google Calendar"""
    import requests
    token = get_valid_token(uid)
    if not token: return False
    try:
        r = requests.delete(
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{gcal_event_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        return r.status_code in [200, 204]
    except: return False

def parse_gcal_event(event):
    """Parse Google Calendar event to our format"""
    start = event.get("start", {})
    end = event.get("end", {})
    start_str = start.get("dateTime", start.get("date",""))
    end_str = end.get("dateTime", end.get("date",""))
    return {
        "gcal_id": event.get("id",""),
        "title": event.get("summary","(제목 없음)"),
        "start_time": start_str,
        "end_time": end_str,
        "description": event.get("description",""),
        "color_label": "indigo",  # Google events use indigo
        "source": "google",
    }
