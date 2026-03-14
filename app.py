"""
AI 엔진 - Gemini + Claude 듀얼 엔진
"""
import streamlit as st
import google.generativeai as genai
import requests
import json

def get_ai_response(prompt, engine="auto", task_type="general"):
    """
    AI 응답 생성
    engine: "auto", "gemini", "claude"
    task_type: "general", "content", "analysis", "summary", "transcription"
    """
    if engine == "auto":
        engine = _auto_select_engine(task_type)
    
    if engine == "claude":
        return _call_claude(prompt)
    else:
        return _call_gemini(prompt)

def _auto_select_engine(task_type):
    """작업 유형에 따라 최적 엔진 자동 선택"""
    claude_key = st.session_state.get("claude_api_key", "")
    
    if not claude_key:
        return "gemini"
    
    claude_tasks = ["content", "summary", "creative"]
    if task_type in claude_tasks:
        return "claude"
    return "gemini"

def _call_gemini(prompt):
    """Gemini API 호출"""
    api_key = st.session_state.get("gemini_api_key", "")
    if not api_key:
        return "⚠️ Gemini API 키를 설정에서 입력하세요."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Gemini 오류: {str(e)}"

def _call_claude(prompt):
    """Claude API 호출"""
    api_key = st.session_state.get("claude_api_key", "")
    if not api_key:
        return _call_gemini(prompt)
    try:
        headers = {
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result["content"][0]["text"]
        else:
            return _call_gemini(prompt)
    except:
        return _call_gemini(prompt)

def transcribe_audio(audio_file, user_id=None):
    """음성 파일 전사 (Gemini 활용)"""
    api_key = st.session_state.get("gemini_api_key", "")
    if not api_key:
        return "⚠️ Gemini API 키가 필요합니다."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        audio_data = audio_file.read()
        
        response = model.generate_content([
            "다음 음성을 한국어로 정확하게 전사해주세요. 화자 구분이 가능하면 구분해주세요.",
            {"mime_type": audio_file.type, "data": audio_data}
        ])
        return response.text
    except Exception as e:
        return f"❌ 전사 오류: {str(e)}"

def summarize_meeting(transcript):
    """회의록 요약"""
    prompt = f"""다음 회의 전사 내용을 분석해주세요:

{transcript}

다음 형식으로 정리해주세요:

## 📋 회의 요약
- 핵심 논의 사항 3-5개

## ✅ 결정 사항
- 결정된 내용 목록

## 🎯 액션 아이템
- [ ] 담당자: 할 일 (마감일)

## 💡 주요 아이디어
- 논의된 아이디어 목록

## 📌 다음 단계
- 후속 조치 사항
"""
    return get_ai_response(prompt, task_type="summary")

def smart_classify(text):
    """텍스트를 자동 분류 (퀵 캡처용)"""
    prompt = f"""다음 텍스트를 분류해주세요. JSON으로만 응답하세요.

텍스트: "{text}"

분류 기준:
- type: "task" (할일), "note" (메모), "expense" (지출), "event" (일정), "idea" (아이디어)
- title: 적절한 제목
- content: 정리된 내용
- due_date: 날짜가 있으면 YYYY-MM-DD (없으면 null)
- category: 지출이면 카테고리 (없으면 null)
- amount: 지출이면 금액 (없으면 null)
- tags: 관련 태그 배열

JSON만 응답하세요. 다른 텍스트 없이."""
    
    response = get_ai_response(prompt, task_type="analysis")
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(cleaned)
    except:
        return {"type": "note", "title": text[:50], "content": text, "tags": []}

def suggest_related_notes(content, existing_notes):
    """관련 노트 추천"""
    if not existing_notes:
        return []
    
    notes_list = "\n".join([f"- ID:{n['id']} | {n['title']}" for n in existing_notes[:30]])
    
    prompt = f"""현재 작성 중인 내용:
{content[:500]}

기존 노트 목록:
{notes_list}

위 내용과 관련 있는 기존 노트를 최대 5개 추천해주세요.
각 노트의 ID만 JSON 배열로 응답하세요. 예: ["id1", "id2"]
관련 노트가 없으면 빈 배열 []을 응답하세요."""

    response = get_ai_response(prompt, task_type="analysis")
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(cleaned)
    except:
        return []

def generate_weekly_review(notes, tasks, expenses):
    """주간 자동 리뷰 생성"""
    prompt = f"""이번 주 활동을 분석해서 리뷰를 작성해주세요.

작성한 노트 수: {len(notes)}개
노트 제목들: {', '.join([n.get('title','') for n in notes[:20]])}

태스크 현황:
- 완료: {len([t for t in tasks if t.get('status')=='done'])}개
- 진행중: {len([t for t in tasks if t.get('status')=='doing'])}개
- 미완료: {len([t for t in tasks if t.get('status')=='todo'])}개

지출 총액: {sum(e.get('amount',0) for e in expenses):,}원
카테고리별: {json.dumps({cat: sum(e['amount'] for e in expenses if e.get('category')==cat) for cat in set(e.get('category','기타') for e in expenses)}, ensure_ascii=False)}

다음 내용으로 리뷰를 작성해주세요:
1. 이번 주 요약
2. 잘한 점
3. 개선할 점
4. 다음 주 추천 우선순위
5. 동기부여 한마디

친절하고 실용적으로 작성해주세요."""
    
    return get_ai_response(prompt, task_type="summary")
