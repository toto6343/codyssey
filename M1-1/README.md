# 환율 트렌드 분석: 원/달러, 원/엔, 원/위안

시계열 데이터 기반 트렌드 분석 미션 — 환율(USD, JPY, CNY) 대상

## 폴더 구조

```
krw-fx-trend/
├── data/
│   ├── exchange_rates.db         # SQLite 캐시 (실데이터 또는 샘플데이터 저장)
│   ├── sample_exchange_rates.csv # 데모/재현용 샘플 데이터
│   ├── ai_usage_log.jsonl        # AI 호출 로그
│   └── ai_usage_log.md           # AI 사용 로그 요약
├── src/
│   ├── fetch_data.py             # 한국수출입은행 Open API 수집 + SQLite 캐싱
│   ├── generate_sample_data.py   # 샘플 데이터 생성 (네트워크 제한 시 대체용)
│   ├── ai_analysis.py            # OpenRouter API 연동 + 사용 로그
│   ├── analyze.py                # 이동평균/변동성/월별수익률/분해/예측 함수
│   ├── visualize.py              # 차트 생성 스크립트
│   └── debug/                   # 진단용 스크립트
├── outputs/                      # 시각화 결과 (PNG)
├── dashboard/
│   └── index.html               # 인터랙티브 대시보드 (Plotly.js)
├── analysis.ipynb                # 전체 분석 노트북
├── REPORT.md                     # 최종 분석 리포트
├── requirements.txt
├── vercel.json
├── .gitignore
└── README.md
```

## 1. 데이터 수집 (실제 API 사용 시)

이 저장소는 **한국수출입은행 Open API (환율)** 를 사용합니다.

1. https://www.koreaexim.go.kr/ir/HPHKIR019M01 에서 Open API 인증키를 발급받습니다.
2. 환경변수 등록:
   ```bash
   export KOREAEXIM_API_KEY="발급받은_키"
   ```
3. 수집 실행:
   ```bash
   python src/fetch_data.py --start 2023-01-01 --end 2026-08-31
   ```
   (기간은 원하는 대로 조정 가능합니다. 예: 오늘 날짜까지 최신 데이터를 계속
   추가하려면 `--end`를 실행 시점 날짜로 바꿔 재실행하면 됩니다 — 이미 캐싱된
   날짜는 다시 호출하지 않습니다.)
   - 이 API는 **하루 1건 조회 형식**이라 기간 데이터를 얻으려면 영업일마다 반복 호출해야 합니다.
   - 호출 실패/재요청을 줄이기 위해 결과를 `data/exchange_rates.db` (SQLite)에 저장하고,
     이미 캐싱된 날짜는 다시 호출하지 않습니다. 호출 사이에는 요청 제한을 피하기 위해
     `--sleep` 옵션(기본 0.3초)만큼 대기합니다.

> **주의:** 이 실행 환경(샌드박스)은 외부 네트워크가 화이트리스트로 제한되어 있어
> `koreaexim.go.kr`, `openrouter.ai` 에 직접 접속할 수 없습니다. 그래서 본 제출물의
> 분석/시각화/리포트는 실제 API 스펙과 동일한 스키마로 생성한 **샘플 데이터**
> (`src/generate_sample_data.py`)로 재현했습니다. `fetch_data.py`는 실제 키를 넣고
> 로컬(또는 네트워크가 열린 환경)에서 바로 실행 가능한 완성 코드입니다.

## 2. AI 활용 (OpenRouter)

`src/ai_analysis.py`는 OpenRouter API(`https://openrouter.ai/api/v1/chat/completions`)를
호출하여 통계 요약을 바탕으로 인사이트 초안을 생성하고, 모든 호출을
`data/ai_usage_log.jsonl`에 기록합니다 (작업 종류/이유/검증 방법 포함, REPORT.md §7 참고).

```bash
export OPENROUTER_API_KEY="발급받은_키"
python src/ai_analysis.py
```

## 3. 분석 재현

아래 순서로 실행하면 로컬에서 가장 안정적으로 재현할 수 있습니다.

```bash
pip install -r requirements.txt
python src/generate_sample_data.py        # 네트워크 제한 환경용 샘플 데이터 생성
python src/visualize.py                   # outputs/ 하위에 차트 생성
jupyter nbconvert --to notebook --execute analysis.ipynb   # 노트북 실행 → outputs/*.png 생성
```

실제 API를 직접 쓰려면 다음처럼 실행합니다.

```bash
export KOREAEXIM_API_KEY="발급받은_키"
python src/fetch_data.py --start 2023-01-01 --end 2026-08-31
python src/visualize.py
```

## 4. 대시보드 (보너스)

`dashboard/index.html`은 별도 서버 없이 브라우저로 바로 열 수 있습니다. 이 파일은
임베드된 데이터 스냅샷을 기반으로 기간 슬라이더와 통화 체크박스를 통해
추세를 탐색할 수 있도록 구성되어 있습니다.

### 4-1. 로컬 확인
더블클릭으로 `dashboard/index.html`을 열거나, 프로젝트 루트에서 아래 명령으로
로컬 서버를 띄워 확인합니다.

```bash
python -m http.server 8000
```

그다음 브라우저에서 `http://localhost:8000/dashboard/` 또는 파일 경로로 열면 됩니다.

### 4-2. Vercel 배포 (보너스 제출 옵션 1: 배포 URL)

이 대시보드는 순수 정적 HTML(서버 불필요)이라 Vercel에 그대로 올릴 수 있습니다.
(참고: Streamlit은 웹소켓 기반 상시 서버가 필요해 Vercel의 서버리스 구조와
맞지 않으므로, 배포용으로는 이 정적 버전을 사용합니다.)

프로젝트 루트에서 이미 `vercel.json`이 설정되어 있어, 별도 빌드 설정 없이
`dashboard/index.html`이 자동으로 배포 대상이 됩니다.

**방법 A — Vercel 웹 대시보드에서 GitHub 저장소 연결 (권장)**
1. 이 프로젝트를 GitHub 저장소로 push합니다.
2. https://vercel.com 에서 "Add New Project" → 방금 만든 저장소 선택.
3. Framework Preset: **Other** 선택.
4. Root Directory는 그대로(저장소 루트) 두면 됩니다 — 루트의 `vercel.json`이
   `outputDirectory: "dashboard"`를 지정해두어서 자동으로 `dashboard/index.html`이
   배포됩니다.
5. "Deploy" 클릭 → 몇 초 후 `https://프로젝트명.vercel.app` 형태의 URL이 발급됩니다.
6. 이후 GitHub에 push할 때마다 자동으로 재배포됩니다.

**방법 B — Vercel CLI로 즉시 배포**
```bash
npm install -g vercel
cd exchange-rate-analysis
vercel --prod
```
CLI가 몇 가지 질문(프로젝트 이름 등)을 물어보는데 기본값을 그대로 사용해도 됩니다.
`vercel.json`이 있어 별도 빌드 설정 없이 `dashboard/index.html`이 배포됩니다.

**배포 URL**: https://krwfxtrend.vercel.app/

배포 후 발급된 URL을 REPORT.md 또는 제출 폼에 기재하면 됩니다.
