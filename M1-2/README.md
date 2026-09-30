# 🎬 주말 박스오피스 AI 비서

> KOBIS 주말 박스오피스 데이터를 분석·요약해서 GPT에 컨텍스트로 주입하고, **"내 데이터를 아는" AI와 대화**하는 웹 서비스

## 1. 서비스 소개

일반적인 챗봇은 "최근 주말 극장가 어때?"라고 물어도 실제 데이터를 모르기 때문에 일반론만 답합니다.
이 서비스는 KOBIS(영화진흥위원회) 주말 박스오피스 약 120주치를 Firestore에 저장하고, 기간·평균·최고/최저·최근 추세·전년 동기 대비를 계산한 **요약**을 시스템 프롬프트에 넣어 데이터에 근거한 답변을 만듭니다.

- 💬 **데이터 기반 AI 채팅** (로딩 표시, 대화 자동 저장)
- 🗂 **데이터 관리** (추가 / 조회 / 수정 / 삭제)
- 🕘 **대화 기록** (목록 조회, 불러오기, 삭제)
- 🔄 **최신 데이터 동기화** (버튼 한 번으로 KOBIS의 새 주말 데이터 추가)
- 📊 **데이터 요약** (기간, 개수, 평균, 최고, 최근 4주 트렌드, 전년 동기 대비)

> 데이터 기준: 각 주말(금~일) 박스오피스 **상위 10편의 관객수 합계**입니다. (KOBIS API가 조회당 최대 10편을 반환)

## 2. 기술 스택

| 영역 | 사용 기술 |
|---|---|
| Backend | Python 3.10+, FastAPI, Pydantic, Uvicorn |
| Database | Firebase Firestore (`data`, `conversations`) |
| AI | OpenAI Chat Completions API |
| Frontend | HTML / CSS / JavaScript (프레임워크 없음) |
| 배포 | Render (Backend), Vercel (Frontend) |
| 데이터 | KOBIS 오픈API `searchWeeklyBoxOfficeList` (`weekGb=1`, 주말) |

## 3. 배포 URL

| 구분 | URL |
|---|---|
| Frontend (Vercel) | `https://<your-app>.vercel.app` ← 배포 후 입력 |
| Backend API (Render) | `https://<your-api>.onrender.com` ← 배포 후 입력 |
| Swagger UI | `https://<your-api>.onrender.com/docs` ← 배포 후 입력 |

> ⏳ 백엔드는 Render 무료 티어라 **첫 요청 시 최대 1분 정도 지연**(콜드스타트)될 수 있습니다. 프론트엔드가 접속 즉시 `/health`를 호출해 서버를 깨우고 안내 문구를 보여줍니다.

## 4. 동작 원리 (컨텍스트 주입)

```
사용자 질문
   │
   ▼
POST /api/chat
   ├─ 1) Firestore data 조회 → 요약 계산 (기간/평균/최고/트렌드/전년 대비/TOP5)
   ├─ 2) 요약을 시스템 프롬프트 템플릿에 삽입   ← 컨텍스트 주입
   ├─ 3) (이어 말하기면) 이전 대화 최근 10개 + 질문과 함께 GPT 호출
   └─ 4) 질문/답변을 conversations에 자동 저장
```

GPT는 학습된 지식이 아니라 **요청마다 주입되는 요약**을 근거로 답합니다. 프롬프트에 "요약에 없는 내용은 추측하지 말고 모른다고 답하라"는 규칙을 넣어 환각을 줄였습니다.

## 5. 프로젝트 구조

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # 앱 초기화, CORS, 예외 핸들러
│   │   ├── config.py            # 환경변수
│   │   ├── firebase.py          # Firestore 연결
│   │   ├── schemas.py           # Pydantic 요청/응답 검증
│   │   ├── routers/             # HTTP 계층 (data, conversations, chat)
│   │   └── services/            # 비즈니스 로직 (summary, data, conversation, chat)
│   └── requirements.txt
├── frontend/
│   ├── public/                  # index.html, style.css, app.js, config.js
│   ├── build.js                 # Vercel 빌드 시 API_BASE_URL → config.js 주입
│   └── vercel.json
├── scripts/collect_weekend_boxoffice.py   # KOBIS → Firestore 1회성 수집
└── render.yaml                  # Render Blueprint
```

**분리 기준**: 라우터는 요청 검증·응답 변환(HTTP)만, 서비스는 데이터 처리·외부 API 호출(로직)만 담당합니다. 요약 계산(`summary_service`)은 외부 의존성이 없는 순수 함수라 단독 테스트가 쉽습니다.

## 6. API 목록

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/data` | 데이터 추가 (문서 ID = 날짜, 중복 시 409) |
| POST | `/api/data/sync` | KOBIS에서 최근 N주(기본 8, 최대 12)를 가져와 **없는 날짜만** 추가 |
| GET | `/api/data` | 데이터 목록 |
| PUT | `/api/data/{id}` | 데이터 수정 (value, memo) |
| DELETE | `/api/data/{id}` | 데이터 삭제 |
| GET | `/api/data/summary` | 데이터 요약 (프롬프트 주입용) |
| POST | `/api/conversations` | 대화 저장 |
| GET | `/api/conversations` | 대화 목록 (**messages 미포함**, `message_count` 제공) |
| GET | `/api/conversations/{id}` | 특정 대화 전체 messages 조회 |
| DELETE | `/api/conversations/{id}` | 대화 삭제 |
| POST | `/api/chat` | AI 대화 (요약 주입 + 자동 저장) |
| GET | `/health` | 헬스체크 |

요약 응답 예시:

```json
{
  "period": "2024-06-14 ~ 2026-09-25",
  "count": 120,
  "metrics": { "total": 2162000000, "average": 18018706, "max": 29740000, "max_date": "2026-05-08", "...": "..." },
  "latest": { "date": "2026-09-25", "value": 8510000, "memo": "1위: ..." },
  "trend": "최근 4주 평균이 직전 4주 대비 -4.7% (유지)",
  "yoy": "작년 같은 시기(최근 4주 기준) 대비 -9.0% (하락)"
}
```

## 7. 로컬 실행 방법

### 사전 준비
- Python 3.10+, Node.js(선택, 빌드 스크립트 확인용)
- Firebase 프로젝트 + Firestore Database + 서비스 계정 키(JSON)
- OpenAI API 키, KOBIS 오픈API 키

### 1) 백엔드
```bash
cd backend
python -m venv venv
source venv\Scripts\Activate.ps1        
pip install -r requirements.txt
cp .env.example .env              # 값 채우기
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

### 2) 데이터 수집 (최초 1회)
`backend/.env`에 `KOBIS_API_KEY`와 Firebase 키를 채워 둔 상태에서, backend 가상환경을 켠 채 프로젝트 루트에서 실행합니다.
```bash
python scripts/collect_weekend_boxoffice.py --weeks 120 --dry-run   # data.json만 생성해 확인
python scripts/collect_weekend_boxoffice.py --weeks 120             # Firestore 적재
```
이후 새 주말 데이터는 웹 화면 **데이터 관리 → 🔄 최신 데이터 가져오기** 버튼으로 추가합니다. (이미 있는 날짜는 건너뛰어 수정한 메모가 보존됩니다.)

### 3) 프론트엔드
```bash
cd frontend/public
python -m http.server 5500        # http://localhost:5500
```
`config.js`의 기본 API 주소는 `http://localhost:8000`이고, 백엔드 기본 CORS 허용 목록에 `http://localhost:5500`이 포함돼 있습니다.

## 8. 환경 변수 목록

### Backend (Render)
| 이름 | 필수 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI API 키 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | ✅ | 서비스 계정 키 JSON **한 줄 문자열** (또는 로컬 파일 경로) |
| `KOBIS_API_KEY` | ✅ | KOBIS 오픈API 키 (동기화 버튼, 수집 스크립트) |
| `ALLOWED_ORIGINS` | ✅ | CORS 허용 도메인, 쉼표 구분·슬래시 없이 (예: `https://your-app.vercel.app`) |
| `OPENAI_MODEL` | | 기본 `gpt-4o-mini` |
| `CHAT_MAX_TOKENS` | | 응답 최대 토큰, 기본 500 |
| `CHAT_MAX_HISTORY` | | 프롬프트에 넣을 이전 메시지 수, 기본 10 |

### Frontend (Vercel)
| 이름 | 필수 | 설명 |
|---|---|---|
| `API_BASE_URL` | ✅ | 백엔드 주소 (예: `https://your-api.onrender.com`). 빌드 시 `config.js`로 주입 |

### 데이터 수집 스크립트
`scripts/collect_weekend_boxoffice.py`는 `backend/.env`의 값(`KOBIS_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_JSON`)을 자동으로 읽습니다. 별도 `export`가 필요 없습니다.

> 🔐 API 키와 서비스 계정 키는 코드/저장소에 넣지 않고 환경변수로만 관리합니다. 서비스 계정 키는 CORS로 보호되지 않는 서버 측 비밀이므로 프론트엔드에는 절대 두지 않습니다.

## 9. 배포 방법

1. **백엔드 (Render)**: GitHub에 푸시 → Render에서 Blueprint(`render.yaml`) 또는 Web Service로 생성 → 환경변수 4개(`OPENAI_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_JSON`, `ALLOWED_ORIGINS`, `KOBIS_API_KEY`) 입력 → `/docs` 접속 확인
2. **프론트엔드 (Vercel)**: 프로젝트 Import → **Root Directory를 `frontend`로 지정** → 환경변수 `API_BASE_URL`에 Render 주소 입력 → 배포
3. **CORS 마무리**: Vercel 배포 URL을 Render의 `ALLOWED_ORIGINS`에 넣고 재배포

## 10. 제출 스크린샷

| 화면 | 이미지 |
|---|---|
| 데이터 요약이 보이는 채팅 화면 (질문+답변 포함) | `docs/screenshot-chat.png` |
| 데이터 관리 화면 (CRUD 중 1개 동작) | `docs/screenshot-data.png` |
| 대화 기록 화면 (불러오기 동작) | `docs/screenshot-history.png` |

## 11. 한계 및 참고

- 상위 10편 합계 기준이라 실제 전체 관객수와 차이가 있을 수 있습니다.
- 요약에 없는 정보(월별 평균, 특정 영화의 상세 성적 등)는 AI가 "알 수 없다"고 답합니다.
- 동기화 API는 인증이 없어 URL을 아는 사람이 호출할 수 있습니다. 주 수 상한(12)과 20초 쿨다운으로 남용을 줄였고, 실서비스라면 인증을 추가해야 합니다.
- OpenAI 호출은 과금이 발생하므로 `max_tokens`와 입력 길이(1,000자) 제한을 두었습니다.
