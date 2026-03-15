"""AI Engine V4.0 - Gemini + Claude + weekly_report custom format"""
import streamlit as st
import google.generativeai as genai
import requests, json

GEMINI_MODELS = {
    "gemini-2.5-flash": "⚡ Gemini 2.5 Flash (Fast, Free, Recommended)",
    "gemini-2.5-pro": "🧠 Gemini 2.5 Pro (Smart, ~50/day free)",
    "gemini-2.0-flash": "⚡ Gemini 2.0 Flash",
    "gemini-1.5-flash": "⚡ Gemini 1.5 Flash",
}
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.5-flash"

def _get_key(name):
    return st.session_state.get(name, "") or st.secrets.get(name.upper(), "")

def _get_model():
    return st.session_state.get("gemini_model", DEFAULT_MODEL)

def get_ai(prompt, engine="auto", task="general"):
    if engine == "auto":
        engine = "claude" if (_get_key("claude_api_key") and task in ["content","summary","creative"]) else "gemini"
    return _claude(prompt) if engine == "claude" else _gemini(prompt)

def _gemini(prompt):
    key = _get_key("gemini_api_key")
    if not key: return "⚠️ Gemini API key가 없습니다. Settings에서 입력하거나 Streamlit Secrets에 GEMINI_API_KEY를 추가하세요."
    model_name = _get_model()
    try:
        genai.configure(api_key=key)
        return genai.GenerativeModel(model_name).generate_content(prompt).text
    except Exception as e:
        error_str = str(e)
        if "429" in error_str and model_name != FALLBACK_MODEL:
            try:
                return genai.GenerativeModel(FALLBACK_MODEL).generate_content(prompt).text
            except Exception as e2:
                return f"❌ Gemini: {e2}"
        return f"❌ Gemini ({model_name}): {e}"

def _claude(prompt):
    key = _get_key("claude_api_key")
    if not key: return _gemini(prompt)
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "content-type": "application/json", "anthropic-version": "2023-06-01"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 4096, "messages": [{"role":"user","content": prompt}]}, timeout=60)
        return r.json()["content"][0]["text"] if r.status_code == 200 else _gemini(prompt)
    except: return _gemini(prompt)

def transcribe(audio):
    key = _get_key("gemini_api_key")
    if not key: return "⚠️ Gemini API key required."
    try:
        genai.configure(api_key=key)
        return genai.GenerativeModel(_get_model()).generate_content(
            ["다음 음성을 한국어로 정확하게 전사해주세요. 화자 구분이 가능하면 구분해주세요.", {"mime_type": audio.type, "data": audio.read()}]).text
    except Exception as e:
        if "429" in str(e):
            try: return genai.GenerativeModel(FALLBACK_MODEL).generate_content(
                ["다음 음성을 한국어로 정확하게 전사해주세요.", {"mime_type": audio.type, "data": audio.read()}]).text
            except: pass
        return f"❌ {e}"

def ocr_image(image_data, mime_type):
    key = _get_key("gemini_api_key")
    if not key: return "⚠️ Gemini API key required."
    try:
        genai.configure(api_key=key)
        return genai.GenerativeModel(_get_model()).generate_content(
            ["이 이미지의 모든 텍스트를 정확하게 읽어서 전사해주세요. 손글씨도 최대한 정확하게 읽어주세요. 마크다운 형식으로 정리해주세요.", {"mime_type": mime_type, "data": image_data}]).text
    except Exception as e:
        if "429" in str(e):
            try: return genai.GenerativeModel(FALLBACK_MODEL).generate_content(
                ["이 이미지의 모든 텍스트를 정확하게 읽어서 전사해주세요.", {"mime_type": mime_type, "data": image_data}]).text
            except: pass
        return f"❌ {e}"

def analyze_image_for_content(image_data, mime_type, content_type="instagram"):
    key = _get_key("gemini_api_key")
    if not key: return "⚠️ Gemini API key required."
    prompt = f"이 이미지를 분석하고, {content_type}용 매력적인 캡션/글을 한국어로 작성해주세요. 해시태그도 포함해주세요."
    try:
        genai.configure(api_key=key)
        return genai.GenerativeModel(_get_model()).generate_content([prompt, {"mime_type": mime_type, "data": image_data}]).text
    except Exception as e:
        if "429" in str(e):
            try: return genai.GenerativeModel(FALLBACK_MODEL).generate_content([prompt, {"mime_type": mime_type, "data": image_data}]).text
            except: pass
        return f"❌ {e}"

def smart_classify(text):
    r = get_ai(f'텍스트를 분류. JSON만 응답. type("task"/"note"/"expense"/"event"), title, content, amount(숫자/null), category(지출카테고리/null). 텍스트: "{text}"', task="analysis")
    try:
        c = r.strip()
        if c.startswith("```"): c = c.split("\n",1)[1].rsplit("```",1)[0]
        return json.loads(c)
    except: return {"type":"note","title":text[:50],"content":text}

def classify_expenses(text):
    r = get_ai(f'지출 내역을 JSON 배열로. 각: {{"date":"YYYY-MM-DD","category":"카테고리","amount":숫자,"description":"설명"}}. 카테고리: 식비,교통비,쇼핑,생활비,의료,교육,여가,카페,구독,기타.\n\n{text}', task="analysis")
    try:
        c = r.strip()
        if c.startswith("```"): c = c.split("\n",1)[1].rsplit("```",1)[0]
        return json.loads(c)
    except: return []

def summarize_meeting(text):
    return get_ai(f"회의 전사 분석:\n{text}\n\n형식:\n## 📋 요약\n## ✅ 결정사항\n## 🎯 액션아이템\n- [ ] 담당: 할일 (마감)\n## 💡 아이디어\n## 📌 다음단계", task="summary")

def suggest_related(content, notes):
    if not notes: return []
    nl = "\n".join([f"ID:{n['id']}|{n['title']}" for n in notes[:30]])
    r = get_ai(f"현재:\n{content[:500]}\n\n기존노트:\n{nl}\n\n관련노트 최대5개 ID JSON배열. 없으면[]", task="analysis")
    try:
        c = r.strip()
        if c.startswith("```"): c = c.split("\n",1)[1].rsplit("```",1)[0]
        return json.loads(c)
    except: return []

def analyze_finances(exp, inc, loans):
    te = sum(e.get("amount",0) for e in exp); ti = sum(i.get("amount",0) for i in inc); tl = sum(l.get("remaining_amount",0) for l in loans)
    cats = {}
    for e in exp: cats[e.get("category","기타")] = cats.get(e.get("category","기타"),0)+e.get("amount",0)
    return get_ai(f"재정분석:\n수입:{ti:,}원\n지출:{te:,}원\n대출잔액:{tl:,}원\n카테고리:{json.dumps(cats,ensure_ascii=False)}\n\n1.재정건강도/100 2.지출최적화3가지 3.대출전략 4.저축/투자추천 5.3개월계획", task="analysis")

def web_summary(url):
    return get_ai(f"URL 핵심 3-5줄 요약 + 키워드 3-5개:\n{url}", task="summary")

def weekly_report(notes, tasks, expenses, custom_format=None):
    done = [t for t in tasks if t.get("status")=="done"]
    todo = [t for t in tasks if t.get("status")=="todo"]
    meeting_notes = [n for n in notes if n.get("note_type")=="meeting"]
    notes_summary = "\n".join([f"- {n['title']}: {n.get('content','')[:100]}" for n in notes[:20]])
    tasks_summary = f"완료: {len(done)}개, 미완료: {len(todo)}개"
    meetings = "\n".join([f"- {n['title']}: {n.get('content','')[:200]}" for n in meeting_notes[:10]])
    fmt = custom_format or """형식:\n## 📊 주간 업무 보고\n### 1. 핵심 성과\n### 2. 진행 중 업무\n### 3. 회의 요약\n### 4. 이슈/리스크\n### 5. 다음 주 계획\n### 6. 건의사항"""
    return get_ai(f"""이번 주 업무 데이터 기반 주간 보고서:

## 노트 ({len(notes)}개):
{notes_summary}

## 태스크: {tasks_summary}
완료: {', '.join([t['title'] for t in done[:15]])}
미완료: {', '.join([t['title'] for t in todo[:15]])}

## 회의록 ({len(meeting_notes)}개):
{meetings}

## 지출: {sum(e.get('amount',0) for e in expenses):,}원

{fmt}""", task="summary")

def folder_summary(notes, period_label):
    content = "\n".join([f"### {n['title']}\n{n.get('content','')[:300]}\n" for n in notes[:30]])
    return get_ai(f"{period_label} 노트 {len(notes)}개 분석:\n\n{content}\n\n1.핵심주제 2.요약 3.인사이트 4.액션아이템", task="analysis")

def send_gmail(to, subj, body, sender, pw):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    try:
        msg = MIMEMultipart(); msg['From']=sender; msg['To']=to; msg['Subject']=subj
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(sender, pw); s.send_message(msg); s.quit()
        return True, "Sent!"
    except Exception as e: return False, str(e)

def file_to_markdown(file_obj):
    name = file_obj.name.lower()
    if name.endswith(('.txt','.md')):
        return file_obj.read().decode('utf-8')
    elif name.endswith('.csv'):
        import pandas as pd; return pd.read_csv(file_obj).to_markdown()
    elif name.endswith('.xlsx'):
        import pandas as pd; return pd.read_excel(file_obj).to_markdown()
    elif name.endswith('.docx'):
        try:
            import docx; doc = docx.Document(file_obj)
            return "\n\n".join([p.text for p in doc.paragraphs])
        except: return get_ai(f"파일 내용을 마크다운으로 변환: {file_obj.name}")
    else:
        content = file_obj.read()
        try: return content.decode('utf-8')
        except: return f"(Binary file: {file_obj.name})"
