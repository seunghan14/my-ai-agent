# 🚀 나만의 AI 에이전트 - 설치 가이드

## 전체 순서 (약 20-30분)

1. ✅ Supabase 설정 (5분)
2. ✅ GitHub에 코드 업로드 (5분)  
3. ✅ Streamlit Cloud 배포 (5분)
4. ✅ API 키 설정 (3분)
5. ⭐ (선택) 텔레그램 봇 연결 (10분)

---

## 1단계: Supabase 설정

### 1-1. 가입
1. https://supabase.com 접속
2. "Start your project" 클릭
3. GitHub 계정으로 로그인 (없으면 만들기)

### 1-2. 프로젝트 생성
1. "New Project" 클릭
2. 프로젝트 이름: `my-ai-agent`
3. Database Password: 강력한 비밀번호 입력 (메모해두세요!)
4. Region: `Northeast Asia (Tokyo)` 선택 (한국에서 가장 빠름)
5. "Create new project" 클릭
6. 2-3분 기다리기

### 1-3. 테이블 생성
1. 왼쪽 메뉴에서 "SQL Editor" 클릭
2. "New query" 클릭
3. `setup.sql` 파일의 내용을 **전체 복사**해서 붙여넣기
4. "Run" 버튼 클릭
5. "Success" 메시지 확인

### 1-4. API 키 확인
1. 왼쪽 메뉴 "Settings" → "API" 클릭
2. 다음 두 값을 메모:
   - **Project URL**: `https://xxxx.supabase.co`
   - **anon public key**: `eyJhbG...` (긴 문자열)

---

## 2단계: GitHub에 코드 업로드

### 2-1. GitHub 저장소 생성
1. https://github.com 접속 (계정 없으면 가입)
2. 우측 상단 "+" → "New repository"
3. Repository name: `my-ai-agent`
4. **Public** 선택
5. "Create repository" 클릭

### 2-2. 파일 업로드
1. 생성된 저장소 페이지에서 "uploading an existing file" 링크 클릭
2. 다운로드받은 파일들을 드래그앤드롭:
   - `app.py`
   - `db_utils.py`
   - `ai_engine.py`
   - `requirements.txt`
   - `.streamlit/config.toml` (폴더째로)
3. "Commit changes" 클릭

⚠️ 주의: `secrets_template.toml`과 `telegram_bot.py`는 **업로드하지 마세요!**

---

## 3단계: Streamlit Cloud 배포

### 3-1. 배포
1. https://share.streamlit.io 접속 (이미 가입하셨죠!)
2. "New app" 클릭
3. Repository: `your-github-username/my-ai-agent` 선택
4. Branch: `main`
5. Main file path: `app.py`
6. "Deploy!" 클릭

### 3-2. Secrets 설정 (중요!)
1. 배포된 앱 페이지에서 우측 하단 "Manage app" 클릭
2. "Settings" → "Secrets" 탭
3. 다음 내용 입력:

```toml
SUPABASE_URL = "https://여기에-1단계에서-메모한-URL.supabase.co"
SUPABASE_KEY = "여기에-1단계에서-메모한-anon-key"
```

4. "Save" 클릭
5. 앱이 자동으로 재시작됩니다

### 3-3. 확인
- 앱 URL (`https://내앱이름.streamlit.app`)로 접속
- 회원가입 → 로그인 테스트
- 노트 작성 테스트

---

## 4단계: API 키 설정

### Gemini API 키 (무료)
1. https://aistudio.google.com/apikey 접속
2. "API 키 만들기" 클릭
3. 키 복사
4. 앱의 ⚙️ 설정 → Gemini API 키에 붙여넣기

### Claude API 키 (선택, 유료)
1. https://console.anthropic.com 접속
2. API Keys → Create Key
3. 크레딧 충전 필요 (최소 $5부터)
4. 앱의 ⚙️ 설정 → Claude API 키에 붙여넣기
5. **없어도 Gemini만으로 모든 기능 사용 가능!**

---

## 5단계: 텔레그램 봇 (선택)

### 5-1. 봇 생성
1. 텔레그램에서 @BotFather 검색
2. `/newbot` 입력
3. 봇 이름 입력 (예: "나의 AI 비서")
4. 봇 username 입력 (예: `my_ai_agent_bot`)
5. **봇 토큰** 메모 (예: `123456:ABC-DEF...`)

### 5-2. 봇 배포 (무료 호스팅)
텔레그램 봇은 별도 서버에서 24시간 실행해야 합니다.

**방법 A: Render (추천, 무료)**
1. https://render.com 가입
2. "New" → "Web Service"
3. GitHub 저장소 연결 (telegram_bot.py만 별도 저장소 필요)
4. Environment Variables에 다음 추가:
   - `TELEGRAM_TOKEN`: 봇 토큰
   - `SUPABASE_URL`: Supabase URL
   - `SUPABASE_KEY`: Supabase Key
   - `GEMINI_API_KEY`: Gemini 키
5. Deploy

**방법 B: 로컬 실행 (테스트용)**
```bash
pip install requests
python telegram_bot.py
```
(PC를 켜둬야 동작)

---

## 🎉 완료!

### 접속 방법
- **회사 PC**: 브라우저 → `https://내앱.streamlit.app`
- **아이폰**: 사파리 → 같은 주소 → 공유 → "홈 화면에 추가"
- **갤럭시탭**: 크롬 → 같은 주소 → 메뉴 → "홈 화면에 추가"
- **텔레그램**: 봇에게 메시지 보내기

### 비용
- Streamlit Cloud: **무료**
- Supabase: **무료** (500MB)
- Gemini API: **무료**
- Claude API: 선택사항 (사용량 기반)
- 텔레그램: **무료**
- Render (봇 호스팅): **무료**

### **총 월 비용: 0원** 🎉

---

## 문제 해결

### "DB 연결 실패"
→ Streamlit Cloud의 Secrets에 SUPABASE_URL과 SUPABASE_KEY가 정확히 입력되었는지 확인

### "API 키 오류"  
→ 앱 내 ⚙️ 설정에서 Gemini API 키가 입력되었는지 확인

### 회사에서 접속 안 됨
→ `*.streamlit.app` 도메인이 차단된 경우, Render나 Railway로 대체 배포 가능

### 텔레그램 봇 응답 없음
→ 봇이 실행 중인지 확인. Render 대시보드에서 로그 확인
