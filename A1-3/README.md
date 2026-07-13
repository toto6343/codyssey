# FitRoutine (핏루틴)

목표와 가능한 시간만 선택하면, AI가 순서가 있는 홈트레이닝 루틴(운동명 + 세트/시간)을 즉시 생성해주는 웹 서비스입니다.

- **배포 URL**: (Vercel 배포 후 이 자리에 실제 URL을 기재하세요. [`핏루틴`](https://fitroutine-indol.vercel.app/))
- **서비스 기획서**: [`service-plan.md`](./service-plan.md) 참고

## 페이지 구성

1. **홈** — 서비스 소개 + 루틴 생성기로 이동하는 CTA
2. **루틴 생성기** — 운동 목표/시간 선택 → AI 루틴 생성 결과 표시
3. **운동 팁 / FAQ** — 운동 전후 주의사항 안내

상단 네비게이션(모바일에서는 햄버거 메뉴)으로 세 섹션을 이동할 수 있습니다.

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | 순수 HTML / CSS / JavaScript (프레임워크 미사용) |
| Backend | Vercel Serverless Functions (Python, 표준 라이브러리만 사용) |
| AI | OpenAI API (Chat Completions, `gpt-4o-mini`) |
| 배포 | Vercel (GitHub 연동) |

## 폴더 구조

```
fitroutine/
├── index.html
├── css/
│   └── style.css
├── js/
│   └── main.js
├── api/
│   └── generate.py       # POST { goal, duration } → { routine }
├── requirements.txt
├── service-plan.md
└── README.md
```

## 로컬에서 확인하기

프론트엔드만 먼저 보고 싶다면 `index.html`을 브라우저로 바로 열어도 되지만,
`api/generate.py` 호출까지 확인하려면 Vercel CLI로 로컬 서버를 띄워야 합니다.

```bash
npm install -g vercel
vercel dev
```

`vercel dev` 실행 전, 프로젝트 루트에 `.env` 파일을 만들고 아래처럼 키를 설정하세요.

```
OPENAI_API_KEY=발급받은_실제_키_값
```

> ⚠️ `.env` 파일은 Git에 커밋하지 마세요. 실제 키 값은 README, 코드, 스크린샷, 커밋 이력 어디에도 남기지 않습니다.

## 배포 방법 (Vercel)

1. 이 프로젝트를 GitHub 저장소에 push 합니다.
2. [Vercel](https://vercel.com)에서 "Add New Project" → 해당 GitHub 저장소를 선택합니다.
3. **Environment Variables**에 아래 값을 등록합니다.

   | Key | Value |
   |---|---|
   | `OPENAI_API_KEY` | 발급받은 OpenAI API 키 |

4. Deploy를 클릭하면 배포가 진행되고, 완료 후 `https://프로젝트명.vercel.app` 형태의 URL이 발급됩니다.
5. 배포 URL에 접속해 세 섹션 이동, 반응형(데스크톱/모바일), AI 루틴 생성 기능이 정상 동작하는지 확인합니다.
6. 문제가 있으면 코드를 수정한 뒤 다시 GitHub에 push하면 Vercel이 자동으로 재배포합니다.

## AI 기능 동작 방식

1. 사용자가 운동 목표(근력/유산소/스트레칭)와 시간(15/30/60분)을 선택합니다.
2. `js/main.js`가 `fetch('/api/generate', { method: 'POST', body: JSON.stringify({ goal, duration }) })`로 요청을 보냅니다.
3. `api/generate.py`(Vercel Serverless Function)가 요청을 받아 OpenAI API를 호출하고, 생성된 루틴 텍스트를 JSON으로 반환합니다.
4. 프론트가 응답을 받아 루틴을 번호가 매겨진 카드 목록으로 화면에 표시합니다.

### 실패 처리

| 상황 | 동작 |
|---|---|
| 목표 또는 시간 미선택 | API 호출 없이 "운동 목표와 시간을 모두 선택해주세요" 안내 |
| API 오류(4xx/5xx) | "루틴 생성 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요" 안내 |
| 응답 지연(15초 초과) | 요청을 중단하고 "응답이 지연되고 있습니다" 안내 |

## 보너스 과제

### 1. 운영 자동화 (데이터 저장/알림 흐름)

루틴이 생성될 때마다 `api/generate.py`가 결과를 노코드 자동화 웹훅(예: Make.com 시나리오)으로 전송해, "사용자 입력 → 처리 → 저장/알림" 흐름을 완성합니다.

**설정 방법**

1. Make.com에서 새 시나리오를 만들고 트리거를 **Webhooks → Custom webhook**으로 설정해 웹훅 URL을 발급받습니다.
2. 이후 모듈로 Google Sheets(행 추가)나 Notion(데이터베이스 항목 생성) 등을 연결해 저장소로 씁니다.
3. 발급받은 웹훅 URL을 환경 변수에 등록합니다.

   | Key | Value |
   |---|---|
   | `WEBHOOK_URL` | Make.com에서 발급받은 웹훅 URL |

4. `WEBHOOK_URL`이 설정되지 않은 경우 이 로깅 단계는 조용히 건너뛰므로, 설정하지 않아도 서비스는 정상 동작합니다(선택 기능).
5. 웹훅 전송이 실패해도 사용자에게 보여지는 루틴 생성 응답에는 영향이 없습니다(best-effort 방식).

전송되는 데이터 형식:
```json
{
  "goal": "근력",
  "duration_min": "30",
  "routine": "1. 워밍업 ...\n2. ...",
  "generated_at": "2026-07-10T12:00:00+00:00"
}
```

### 2. UX 및 측정 고도화

- **마이크로 인터랙션**: 칩(목표/시간) 선택 시 팝 애니메이션, 루틴 결과 카드가 순서대로 하나씩 나타나는 stagger 애니메이션, 운동 팁 카드가 스크롤 시 서서히 나타나는 리빌 효과(`IntersectionObserver` 사용)
- **방문자 분석**: Vercel Analytics 스크립트(`/_vercel/insights/script.js`)를 삽입해두었습니다. Vercel 프로젝트 대시보드의 **Analytics** 탭에서 활성화하면 별도 코드 수정 없이 방문자 수를 확인할 수 있습니다.
- **접근성 고려**: `prefers-reduced-motion`을 존중해 모션에 민감한 사용자에게는 애니메이션을 최소화하며, JavaScript가 비활성화된 환경에서도 콘텐츠가 가려지지 않도록 `noscript` 폴백을 넣었습니다.

## 보안 주의사항

- API 키는 코드에 직접 작성하지 않고 Vercel 프로젝트의 환경 변수로만 관리합니다.
- `.env` 파일은 `.gitignore`에 추가해 커밋되지 않도록 합니다.
- 키 유출이 의심되면 즉시 OpenAI Platform에서 키를 재발급하세요.
- `WEBHOOK_URL`(보너스 기능)도 민감할 수 있는 내부 자동화 주소이므로, `OPENAI_API_KEY`와 동일하게 환경 변수로만 관리하고 코드/README/커밋에 직접 노출하지 않습니다.