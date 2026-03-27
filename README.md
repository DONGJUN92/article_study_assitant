# 📚 Article Study

> AI 기반 다국어 학술 논문 학습 도우미 — Chromium 브라우저 확장 프로그램
로컬 LLM (Ollama + Gemma3:1b)과 경량 RAG (LightRAG)를 활용하여 **프라이버시를 보장**하면서 논문을 효율적으로 학습할 수 있는 브라우저 확장 프로그램입니다.

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📖 PDF 자동 학습 | PDF 열면 자동으로 RAG 인덱싱 |
| 📝 단어 분석 | 블록 선택 시 문맥 기반 최적 의미 제시 |
| 🌐 문장 번역 + 요약 | 번역 + 논문 맥락 3줄 요약 |
| 📄 전체 번역 | 좌우 분할 뷰, 스크롤 동기화 |
| 💬 AI 질문 | RAG 기반 논문 질의응답 |
| 🔤 스마트 단어장 | 자동 수집, 에빙하우스 복습 |
| 🎯 AI 브리핑 | 원클릭 논문 요약 |

## 🛠️ 시스템 요구사항

- **OS**: Windows 10+
- **RAM**: 8GB+ (16GB 권장)
- **Python**: 3.10+
- **Ollama**: 최신 버전
- **브라우저**: Chrome 120+ / Edge 120+
- **저장 공간**: 약 5GB (모델 포함)

## 🚀 설치 및 실행 가이드 (Step by Step)

> ⚠️ **Windows PowerShell** 기준으로 설명합니다. 모든 명령어는 터미널에 **한 줄씩** 복사-붙여넣기 하세요.

---

### 📌 STEP 1 — 사전 준비 프로그램 설치

아래 2개 프로그램이 PC에 설치되어 있어야 합니다. 이미 설치되어 있다면 건너뛰세요.

#### ① Python 설치 (3.10 이상)
1. 아래 링크에서 다운로드합니다:
   👉 https://www.python.org/downloads/
2. 설치할 때 **반드시** `✅ Add Python to PATH` 체크박스를 선택하세요
3. 설치 완료 후 **PowerShell을 새로 열고** 아래 명령어로 확인합니다:
   ```powershell
   python --version
   ```
   ✅ `Python 3.10.x` 같은 버전이 출력되면 성공  
   ❌ 오류가 나면 Python을 다시 설치하고 `Add to PATH`를 체크했는지 확인

#### ② Ollama 설치 (AI 모델 실행기)
1. 아래 링크에서 다운로드합니다:
   👉 https://ollama.com/download
2. 설치 파일을 실행하여 설치합니다 (별도 설정 없이 `Next` → `Install`)
3. 설치 완료 후 아래 명령어로 확인합니다:
   ```powershell
   ollama --version
   ```
   ✅ 버전 번호가 출력되면 성공

---

### 📌 STEP 2 — AI 모델 다운로드

> 최초 1회만 필요합니다. 약 **3GB**를 다운로드하므로 인터넷이 필요합니다.

PowerShell에서 아래 명령어를 **한 줄씩** 실행합니다:

```powershell
ollama pull gemma3:1b
```
⏳ 다운로드가 끝날 때까지 기다립니다 (약 5~10분)

```powershell
ollama pull nomic-embed-text
```
⏳ 마찬가지로 완료까지 대기합니다

✅ 두 모델 모두 `success`가 출력되면 완료

---

### 📌 STEP 3 — Python 서버 설정

> 프로젝트 폴더(`article_study`)가 있는 경로에서 진행합니다.

#### 방법 A: 자동 설치 스크립트 사용 (권장)
PowerShell에서 아래 명령어를 실행합니다:
```powershell
cd "c:\Users\DONGJUN SHIN\Desktop\개발\article_study\installer"
```
```powershell
.\install.ps1
```
> 💡 **만약 "스크립트 실행이 비활성화되어 있습니다" 오류가 나오면**, 아래 명령어를 먼저 실행하세요:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> 그 다음 다시 `.\install.ps1` 을 실행합니다.

#### 방법 B: 수동 설치
STEP 3-A가 안 될 경우, 아래 명령어를 **한 줄씩** 실행합니다:

```powershell
cd "c:\Users\DONGJUN SHIN\Desktop\개발\article_study\server"
```
```powershell
python -m venv venv
```
```powershell
.\venv\Scripts\Activate.ps1
```
> 💡 **만약 오류가 발생하면**: PowerShell 보안 정책 때문일 수 있습니다. 아래 명령어를 먼저 실행하세요:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> 그 다음 다시 `.\venv\Scripts\Activate.ps1` 을 실행합니다.

```powershell
pip install -r requirements.txt
```
⏳ 패키지 설치가 완료될 때까지 기다립니다 (약 3~5분)

✅ 오류 없이 끝나면 서버 설정 완료!

---

### 📌 STEP 4 — 서버 실행

> ⚠️ **Article Study를 사용하려면 항상 서버가 켜져 있어야 합니다.**

#### 방법 A: 스크립트로 실행
```powershell
cd "c:\Users\DONGJUN SHIN\Desktop\개발\article_study\installer"
```
```powershell
.\start_server.ps1
```

#### 방법 B: 수동 실행
```powershell
cd "c:\Users\DONGJUN SHIN\Desktop\개발\article_study\server"
```
```powershell
.\venv\Scripts\Activate.ps1
```
```powershell
python main.py
```

✅ 아래와 같은 메시지가 나오면 서버가 정상 실행된 것입니다:
```
🚀 Article Study server starting on http://127.0.0.1:8765
📖 API docs: http://127.0.0.1:8765/docs
```

> 💡 **서버를 끄려면**: 서버가 실행 중인 터미널에서 `Ctrl+C`를 누르세요.  
> 💡 **서버는 닫지 마세요**: 확장 프로그램을 사용하는 동안 이 터미널 창을 열어두어야 합니다.

---

### 📌 STEP 5 — 브라우저 확장 프로그램 설치

#### Chrome 사용자
1. 주소창에 `chrome://extensions` 를 입력하고 Enter
2. 오른쪽 상단의 **"개발자 모드"** 토글 스위치를 **켜기(ON)** 합니다
3. 화면 왼쪽 상단에 나타나는 **"압축해제된 확장 프로그램을 로드합니다"** 버튼을 클릭
4. 파일 선택 창에서 아래 폴더를 선택합니다:
   ```
   c:\Users\DONGJUN SHIN\Desktop\개발\article_study\extension
   ```
5. ✅ "Article Study" 확장 프로그램이 목록에 나타나면 설치 완료!

#### Edge 사용자
1. 주소창에 `edge://extensions` 를 입력하고 Enter
2. 왼쪽 하단의 **"개발자 모드"** 토글 스위치를 **켜기(ON)** 합니다
3. **"압축 풀기"** 버튼을 클릭
4. 위와 같은 `extension` 폴더를 선택합니다

---

### 📌 STEP 6 — 사용하기

1. **서버가 켜져있는지 확인** (STEP 4)
2. 브라우저에서 **PDF 논문 파일을 열면** 자동으로 학습이 시작됩니다
3. 우측 하단에 "📖 논문 학습중..." 메시지가 나타나고, 완료되면 "✅ 학습 완료"로 바뀝니다
4. 이후 단어 선택, AI 질문, 번역 등의 기능을 사용할 수 있습니다

---

### ❓ 문제 해결 (FAQ)

| 문제 | 해결 방법 |
|------|-----------|
| `.\install.bat` 실행 시 오류 | PowerShell 대신 **명령 프롬프트(cmd)** 를 열어 실행해보세요 |
| `python` 명령을 찾을 수 없음 | Python 설치 시 `Add to PATH` 체크 후 재설치 |
| `pip install` 중 오류 | `python -m pip install --upgrade pip` 실행 후 재시도 |
| 서버 실행 시 포트 오류 | 이미 다른 프로그램이 8765 포트를 사용 중. 해당 프로그램 종료 후 재시도 |
| 확장 프로그램에서 "서버 연결 실패" | 서버 터미널이 켜져 있는지 확인 |
| Ollama 관련 오류 | Ollama 앱이 시스템 트레이에서 실행 중인지 확인 |

## 📁 프로젝트 구조

```
article_study/
├── extension/           # 브라우저 확장 프로그램 (MV3)
│   ├── manifest.json
│   ├── background/      # Service Worker
│   ├── content/         # Content Scripts + CSS
│   ├── sidepanel/       # AI 채팅, 단어장, 브리핑
│   ├── popup/           # 상태 표시 팝업
│   ├── options/         # 설정 페이지
│   └── icons/
├── server/              # Python 백엔드 (FastAPI)
│   ├── main.py          # 엔트리포인트
│   ├── routers/         # API 라우터
│   ├── services/        # 비즈니스 로직
│   └── models/          # Pydantic 스키마
├── installer/           # 설치 스크립트
└── README.md
```

## ⌨️ 단축키

| 단축키 | 기능 |
|--------|------|
| `Ctrl+Shift+T` | 전체 문서 번역 |
| `Ctrl+Shift+A` | AI 질문 패널 |
| `Ctrl+Shift+G` | 단어장 열기 |

## 🔗 API 엔드포인트

서버 실행 후 `http://localhost:8765/docs`에서 전체 API 문서 확인 가능.

| Endpoint | 설명 |
|----------|------|
| POST `/api/ingest` | PDF 업로드 & 학습 |
| POST `/api/word` | 단어 분석 |
| POST `/api/sentence` | 문장 번역+요약 |
| POST `/api/chat` | AI 챗 (SSE) |
| POST `/api/translate` | 전체 번역 (SSE) |
| GET `/api/vocabulary` | 단어장 조회 |
| GET `/api/health` | 서버 상태 확인 |

## 🔒 보안

- 모든 AI 처리는 로컬에서 수행
- 외부 API 호출 없음
- 데이터는 로컬 디스크에만 저장

## 📜 라이선스

MIT License
