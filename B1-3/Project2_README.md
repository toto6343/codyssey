# [프로젝트 2] 자유 주제 자동화 설계 및 구현

> AI 키워드 뉴스 자동 수집 및 알림 시스템

---

## 1. 자동화할 반복 업무 정의

**업무명:** AI 관련 뉴스 수동 검색 및 저장

**문제 상황:**
매일 ChatGPT, Claude, Gemini 등 AI 관련 최신 뉴스를 직접 검색하고, 관심 있는 기사를 찾아 따로 저장하는 작업이 반복됩니다. 하루에도 수십 개의 기사가 올라오기 때문에 놓치는 기사가 생기거나 수동으로 정리하는 데 시간이 소요됩니다.

**자동화 목표:**
- RSS 피드에서 AI 키워드(ChatGPT, Claude, Gemini)가 포함된 기사를 자동 감지
- Google Sheets에 날짜, 제목, 링크를 자동 저장
- Gmail로 새 기사 알림을 자동 발송

---

## 2. 자동화 도구 선정 및 이유

**선정 도구: Make (make.com)**

| 선정 이유 | 설명 |
|-----------|------|
| RSS 모듈 내장 | 별도 설정 없이 RSS 피드 바로 연동 가능 |
| 무료 Router 기능 | 키워드 필터링을 무료 플랜에서 OR 조건으로 구현 가능 |
| 시각적 흐름 파악 | 노드 기반 UI로 전체 워크플로우를 한눈에 확인 가능 |
| 상세한 실행 로그 | 모듈별 입출력 데이터 확인으로 디버깅 용이 |
| 무료 플랜 범위 | 1,000 Ops/월로 일상적인 뉴스 수집에 충분 |

---

## 3. 워크플로우 설계 문서

### 흐름도

```
RSS 피드 새 글 등록
        ↓
Watch RSS Feed Items
(VentureBeat AI 피드)
        ↓
Router — AI 키워드 필터
┌───────────────────────────┐
│ 제목에 "ChatGPT" 포함     │
│ OR 제목에 "Claude" 포함   │
│ OR 제목에 "Gemini" 포함   │
└───────────────────────────┘
        ↓ (조건 충족 시)
Google Sheets — Add a Row
(날짜 / 제목 / 링크 저장)
        ↓
Gmail — Send an Email
([AI 뉴스] 제목 — 알림 발송)
```

### 단계별 설명

| 단계 | 모듈 | 상세 설정 |
|------|------|-----------|
| **Trigger** | RSS — Watch RSS Feed Items | URL: `https://venturebeat.com/category/ai/feed/` |
| **조건 분기** | Router | 제목에 ChatGPT / Claude / Gemini 포함 여부 (OR 조건 3개) |
| **Action 1** | Google Sheets — Add a Row | 날짜(Date Created), 제목(Title), 링크(URL) 저장 |
| **Action 2** | Gmail — Send an Email | 제목: `[AI 뉴스] {{Title}}` / 본문: 제목 + 날짜 + 링크 |

### Trigger 설정

- **트리거 이벤트:** Watch RSS Feed Items
- **피드 URL:** `https://venturebeat.com/category/ai/feed/`
- **시작 지점:** From now on (새 글만 감지)
- **최대 처리 수:** 5건/실행

### 조건 분기 설정 (Router Filter)

```
Label: AI 키워드 필터
Condition 1: Title Contains "ChatGPT"
OR
Condition 2: Title Contains "Claude"
OR
Condition 3: Title Contains "Gemini"
```

### Google Sheets 컬럼 매핑

| 컬럼 | 매핑 값 |
|------|---------|
| 날짜 | Date Created |
| 제목 | Title |
| 링크 | URL |

---

## 4. 구현 화면 캡처

### Make 워크플로우 구성 화면

![Make 워크플로우]
<img width="1738" height="430" alt="Image" src="https://github.com/user-attachments/assets/ec50923a-a38e-4a7e-aa1d-95c61cfb9822" />

**실행 결과 요약:**
- RSS 모듈: 1건 감지
- Router: 2건 라우팅
- Google Sheets: 3건 저장 ✅
- Gmail: 3건 발송 ✅

---

## 5. 실행 결과 화면

### Gmail 수신 결과

![Gmail 알림 결과]
<img width="1016" height="141" alt="Image" src="https://github.com/user-attachments/assets/cafb02d0-4de6-4c1e-82ef-6b31ebeb05e5" />

**수신된 이메일 목록:**
- `[AI 뉴스] Claude Code costs up to $200 a month. Goose does the same thing for free.`
- `[AI 뉴스] Anthropic launches Cowork, a Claude Desktop agent that works in your files — no coding required`
- `[AI 뉴스] Nous Research's NousCoder-14B is an open-source coding model landing right in the Claude Code moment`

---

## 6. 학습 정리

### 이 워크플로우에서 배운 것

- **Trigger:** RSS 피드의 새 글 등록이 자동화의 시작점
- **조건 분기:** OR 조건으로 여러 키워드를 동시에 필터링 가능
- **Action:** Sheets 저장과 Gmail 발송을 순차적으로 연결
- **실용성:** 매일 수동으로 하던 뉴스 검색을 완전 자동화

### 확장 가능성

- 키워드 추가 (예: "GPT-5", "Llama", "Mistral")
- Slack 알림 추가
- 피드 URL 여러 개 추가 (TechCrunch, The Verge 등)
- 주간 요약 자동 생성 (AI 연동)
