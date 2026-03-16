"""Google Calendar Integration Helper - Fixed V2"""
import streamlit as st
from datetime import datetime, timedelta, timezone
import json

def get_google_creds():
    client_id = st.secrets.get("GOOGLE_CLIENT_ID","")
    client_secret = st.secrets.get("GOOGLE_CLIENT_SECRET","")
    return client_id, client_secret

def get_redirect_uri():
    uri = st.secrets.get("REDIRECT_URI","")
    if not uri:
        uri = "https://sh-agent.streamlit.app"
    return uri.rstrip("/")

def build_auth_url():
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
    from db_utils import get_google_tokens, save_google_tokens
    tokens = get_google_tokens(uid)
    if not tokens or not tokens.get("refresh_token"):
        return None

    expiry_str = tokens.get("token_expiry","")
    now = datetime.now(timezone.utc)
    needs_refresh = True

    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str.replace("Z","+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            # FIX: .total_seconds() 사용 (기존 .seconds는 시간 컴포넌트만 반환)
            needs_refresh = (expiry - now).total_seconds() < 300
        except:
            needs_refresh = True

    if needs_refresh:
        new_tok = refresh_access_token(tokens["refresh_token"])
        if new_tok:
            expiry = now + timedelta(seconds=new_tok.get("expires_in",3600))
            save_google_tokens(uid, new_tok["access_token"], tokens["refresh_token"], expiry.isoformat())
            return new_tok["access_token"]
        return None
    return tokens.get("access_token")

def gcal_get_events(uid, time_min, time_max):
    import requests
    token = get_valid_token(uid)
    if not token:
        return [], "토큰 없음 또는 만료 (재연결 필요)"

    try:
        # FIX: Z suffix 처리 개선
        def to_rfc3339(dt):
            if dt.tzinfo is None:
                return dt.isoformat() + "Z"
            return dt.isoformat()

        r = requests.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "timeMin": to_rfc3339(time_min),
                "timeMax": to_rfc3339(time_max),
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": 100,
            },
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("items", []), None
        elif r.status_code == 401:
            return [], f"인증 만료 (401) - Google Calendar 재연결 필요"
        else:
            return [], f"API 오류 ({r.status_code}): {r.text[:100]}"
    except Exception as e:
        return [], f"연결 오류: {str(e)}"

def gcal_create_event(uid, title, start_dt, end_dt, desc=""):
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
            json=body,
            timeout=10
        )
        if r.status_code in [200, 201]:
            return r.json().get("id")
    except:
        pass
    return None

def gcal_delete_event(uid, gcal_event_id):
    import requests
    token = get_valid_token(uid)
    if not token: return False
    try:
        r = requests.delete(
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{gcal_event_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        return r.status_code in [200, 204]
    except:
        return False

def parse_gcal_event(event):
    start = event.get("start", {})
    end = event.get("end", {})
    start_str = start.get("dateTime", start.get("date",""))
    end_str = end.get("dateTime", end.get("date",""))

    # FIX: gcal_id가 빈 문자열이면 None으로 처리
    gcal_id = event.get("id","").strip() or None

    return {
        "gcal_id": gcal_id,
        "title": event.get("summary","(제목 없음)"),
        "start_time": start_str,
        "end_time": end_str,
        "description": event.get("description",""),
        "color_label": "indigo",
        "source": "google",
    }
