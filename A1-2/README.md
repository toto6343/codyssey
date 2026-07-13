# 국내 여행 추천 프로그램 (OpenAI API + Naver Local Search API)

여행 날짜를 입력하면

1. **OpenAI API(LLM)** 가 그 시기에 여행하기 좋은 국내 지역을 1~3곳 추천하고 (날씨/행사/추천 이유 포함)
2. **Naver Local Search API(지도/장소 검색)** 가 추천된 각 지역의 맛집을 검색한 뒤
3. 다시 **OpenAI API** 가 위 데이터를 종합해 최종 여행 리포트를 Markdown으로 생성합니다.

## 주요 기능

- CLI 실행 (`argparse`), 날짜 형식(`YYYY-MM-DD`) 검증
- LLM 1차 추천 → 지도 API 맛집 검색 → LLM 최종 리포트, 3단계 파이프라인
- **복수 지역 추천 (보너스)**: 한 번에 1~3개 지역을 추천받아 지역별로 리포트 작성
- **결과 캐싱 (보너스)**: 같은 `--date` 로 재실행 시 이미 저장된 원본 JSON이 있으면
  추천/맛집 검색 API 호출을 건너뛰고 저장된 데이터로 리포트만 다시 생성 (`--no-cache` 옵션으로 강제 재호출 가능)
- API 실패(인증 오류/네트워크 오류/빈 결과)에도 프로그램이 중단되지 않고, 해당 구간을 "데이터 없음"으로 표기하며 계속 진행
- LLM 응답이 JSON으로 파싱되지 않을 경우 최대 1회 재시도
- API 키는 코드에 직접 작성하지 않고 `.env` / 환경변수로만 관리

## 폴더 구조

```
travel_planner/
├── travel_planner.py     # 메인 프로그램
├── requirements.txt       # 필요 패키지 목록
├── .env.example           # 환경변수 설정 예시 (실제 키 값 없음)
└── README.md
```

실행 시 자동으로 `results/` 폴더가 생성되고, 아래 파일들이 저장됩니다.

```
results/
├── {YYYY-MM-DD}_raw_data.json     # 1차 추천 JSON + 맛집 검색 결과 + 오류 목록
└── {YYYY-MM-DD}_travel_plan.md    # 최종 여행 리포트
```

## 1. 설치

Python 3.10 이상이 필요합니다.

```bash
cd A1-2
pip install -r requirements.txt
```

## 2. API 키 발급 및 설정 방법

### 2-1. OpenAI API 키 발급

1. [OpenAI Platform](https://platform.openai.com/api-keys) 에 접속해 로그인합니다.
2. "Create new secret key" 를 눌러 키를 발급받습니다.

### 2-2. Naver Local Search API 키 발급

1. [Naver 개발자 센터](https://developers.naver.com/apps) 에 접속해 로그인 후 "애플리케이션 등록"을 클릭합니다.
2. 사용 API 목록에서 **검색(Search)** 을 추가합니다.
3. 등록 완료 후 발급되는 **Client ID / Client Secret** 을 확인합니다.
4. `401`/`403` 오류가 발생하면 애플리케이션에 "검색" API가 정상 등록되어 있는지, Client ID/Secret 값과 헤더명(`X-Naver-Client-Id`, `X-Naver-Client-Secret`)에 오타가 없는지 확인하세요.

### 2-3. 키 설정 (택 1)

**방법 A — `.env` 파일 사용 (권장)**

`.env.example` 파일을 복사해 `.env` 파일을 만들고, 값을 채워 넣습니다.

```bash
cp .env.example .env
```

```
OPENAI_API_KEY=발급받은_실제_키_값
OPENAI_MODEL=gpt-4o-mini
NAVER_CLIENT_ID=발급받은_실제_ID
NAVER_CLIENT_SECRET=발급받은_실제_시크릿
```

**방법 B — 환경변수 직접 설정 (현재 터미널 세션에만 적용)**

macOS / Linux:
```bash
export OPENAI_API_KEY="your_key"
export NAVER_CLIENT_ID="your_id"
export NAVER_CLIENT_SECRET="your_secret"
```

Windows PowerShell:
```powershell
$env:OPENAI_API_KEY="your_key"
$env:NAVER_CLIENT_ID="your_id"
$env:NAVER_CLIENT_SECRET="your_secret"
```

> ⚠️ 위 예시는 설정 "방식"을 보여주기 위한 것이며, 실제 키 값은 절대 README, 코드, 커밋, 제출물 어디에도 직접 작성하지 마세요.

## 3. 실행 방법

```bash
python travel_planner.py --date "2026-03-15"
```

출력 예시:

```
[1/3] 1차 추천 생성 중(LLM)...
    - recommended_city: "제주"
    - recommended_city: "강릉"
[2/3] 맛집 검색 중(지도/장소 API)...
    - 제주: 맛집 5곳 검색 완료
    - 강릉: 맛집 5곳 검색 완료
[3/3] 최종 리포트 생성 중(LLM)...
    - 리포트 생성 완료

완료! results/2026-03-15_travel_plan.md 를 확인하세요.
```

캐시를 무시하고 강제로 다시 호출하려면:

```bash
python travel_planner.py --date "2026-03-15" --no-cache
```

## 4. 결과물 확인 방법

- `results/{날짜}_raw_data.json` : 1차 추천 결과, 맛집 검색 결과(도시별), 오류 목록(`errors`)이 담긴 원본 데이터
- `results/{날짜}_travel_plan.md` : 지역별 추천 이유 / 날씨 / 행사 / 맛집 / 1일 일정 / 오류 요약이 포함된 최종 리포트 (Markdown)

## 5. 오류 처리 정책

| 상황 | 동작 |
|---|---|
| API 키 미설정 | 즉시 종료 + 설정 방법 안내 출력 |
| 지도/장소 API 실패(네트워크/인증/쿼터) | 해당 지역 맛집 섹션을 "데이터 없음"으로 처리하고 계속 진행 |
| 맛집 검색 결과 0건 | 중단하지 않고 "데이터 없음"으로 다음 단계 진행 |
| LLM JSON 파싱 실패 | "필수 키만 다시 출력"하도록 프롬프트를 바꿔 1회 재시도, 그래도 실패하면 빈 추천으로 진행 |
| 최종 리포트 생성(LLM) 실패 | 코드에서 직접 구성한 대체(fallback) 리포트를 생성 |

모든 오류는 `raw_data.json`의 `errors` 배열과 리포트의 "오류 요약" 섹션에 기록됩니다.

## 6. 보안 주의사항

- API 키를 코드에 직접 작성하지 마세요. 반드시 `.env` 또는 환경변수를 사용하세요.
- `.env` 파일은 절대 Git에 커밋하거나 과제 제출물에 포함하지 마세요. (`.gitignore`에 `.env`를 추가하는 것을 권장합니다.)
- `results/` 폴더에 저장되는 JSON/Markdown 파일에는 API 키가 포함되지 않습니다. 다만 제출 전 혹시 모를 개인정보나 민감 정보가 포함되지 않았는지 한 번 더 확인하세요.
- 키가 노출되었다고 의심되면 즉시 OpenAI Platform / Naver 개발자 센터에서 키를 재발급하세요.