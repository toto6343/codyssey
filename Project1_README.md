# 노코드 자동화 도구 비교 및 구현 프로젝트

> 코딩 없이 마우스 클릭만으로 반복 업무를 자동화하는 노코드 자동화 도구(Make, Zapier)를 비교 분석하고, 자유 주제로 나만의 자동화 파이프라인을 설계·구현한 프로젝트입니다.

---

## 목차

- [프로젝트 1: 자동화 도구 비교 구현](#프로젝트-1-자동화-도구-비교-구현)
- [프로젝트 2: 자유 주제 자동화 설계 및 구현](#프로젝트-2-자유-주제-자동화-설계-및-구현)

---

## 프로젝트 1: 자동화 도구 비교 구현

### 워크플로우 개요

**주제:** AI 도구 학습 과정 만족도 조사 자동 분류 및 이메일 알림

동일한 워크플로우를 **Make**와 **Zapier** 2개 도구로 구현하고 비교 분석하였습니다.

```
Google Form 응답 제출
        ↓
Google Sheets 새 행 감지 (Trigger)
        ↓
조건 분기 (만족도 점수 기준)
   ↙              ↘
4점 이상          3점 이하
(긍정 응답)      (개선 필요)
   ↓                ↓
Gmail 발송       Gmail 발송
```

---

### Make 구현

#### 워크플로우 구성

| 단계 | 모듈 | 설정 |
|------|------|------|
| Trigger | Google Sheets — Watch New Rows | 설문 응답 시트 연결 |
| 조건 분기 | Router | 만족도 점수 기준 2개 Route |
| Action 1 | Gmail — Send an Email | 긍정 응답 알림 (score ≥ 4) |
| Action 2 | Gmail — Send an Email | 개선 필요 알림 (score ≤ 3) |

#### 워크플로우 구성 화면

![Make 워크플로우](screenshots/make_workflow.png)

#### 실행 결과 화면

![Make 긍정 응답 이메일](screenshots/make_result_positive.png)
![Make 개선 필요 이메일](screenshots/make_result_negative.png)

---

### Zapier 구현

#### 워크플로우 구성

Zapier는 Router 기능이 없어 **Zap 2개**로 구현하였습니다.

**Zap 1 — 긍정 응답**

| 단계 | 모듈 | 설정 |
|------|------|------|
| Trigger | Google Sheets — New Spreadsheet Row | 설문 응답 시트 연결 |
| Filter | Filter by Zapier | score Greater than 3 |
| Action | Gmail — Send Email | [긍정 응답] 만족도 조사 결과 |

**Zap 2 — 개선 필요**

| 단계 | 모듈 | 설정 |
|------|------|------|
| Trigger | Google Sheets — New Spreadsheet Row | 설문 응답 시트 연결 |
| Filter | Filter by Zapier | score Less than 4 |
| Action | Gmail — Send Email | [개선 필요] 만족도 조사 결과 |

#### 워크플로우 구성 화면

![Zapier Zap1 워크플로우](screenshots/zapier_zap1.png)
![Zapier Zap2 워크플로우](screenshots/zapier_zap2.png)

#### 실행 결과 화면

![Zapier 긍정 응답 이메일](screenshots/zapier_result_positive.png)
![Zapier 개선 필요 이메일](screenshots/zapier_result_negative.png)

---

### 비교 분석

| 비교 항목 | Make | Zapier |
|-----------|------|--------|
| **UI/UX** | 시각적 노드(버블) 기반. 전체 흐름이 한눈에 파악됨 | 리스트 기반. 단계별로 직관적이고 깔끔함 |
| **설정 난이도** | 초기 학습 곡선 있음. 모듈 연결 방식 익숙해지는 데 시간 필요 | 초보자 친화적. 단계별 가이드로 빠르게 설정 가능 |
| **조건 분기** | Router 내장 — 하나의 시나리오에서 다중 분기 가능 (무료) | Filter만 제공 — 분기마다 별도 Zap 필요. **Filter는 유료** |
| **무료 플랜** | 1,000 Ops/월. Router 등 대부분 기능 무료 | 100 Tasks/월. Filter 등 고급 기능은 유료 플랜 필요 |
| **실행 로그** | 모듈별 입출력 데이터 상세 확인 가능 | Task History에서 확인. 상세도는 Make보다 낮음 |
| **연동 서비스** | 1,000개 이상. HTTP 모듈로 커스텀 API 연동 가능 | 6,000개 이상. 연동 서비스 수는 Zapier가 더 많음 |

#### Make 장단점

**장점**
- 복잡한 조건 분기를 무료 플랜에서 구현 가능
- 시각적 노드 기반으로 전체 흐름 파악 용이
- 실행 로그가 상세하여 디버깅 편리

**단점**
- 초기 학습 곡선 존재
- 모듈 연결 방식이 낯설어 초반 설정 오류 발생 가능

#### Zapier 장단점

**장점**
- 초보자도 빠르게 설정 가능한 직관적 UI
- 연동 가능한 앱 수가 6,000개 이상으로 광범위

**단점**
- Filter(조건 분기) 기능이 유료 플랜에서만 제공
- 무료 플랜 Task 수 제한 (100개/월)
- 조건 분기 시 Zap을 여러 개 관리해야 함

#### 도구 선택 가이드

| 상황 | 추천 도구 |
|------|-----------|
| 복잡한 조건 분기가 필요할 때 | **Make** |
| 무료로 고급 기능을 사용하고 싶을 때 | **Make** |
| 빠르게 간단한 자동화를 구축할 때 | **Zapier** |
| 연동 앱 종류가 매우 많이 필요할 때 | **Zapier** |
| 처음 노코드 자동화를 시작할 때 | **Zapier** |

---

## 프로젝트 2: 자유 주제 자동화 설계 및 구현

### 반복 업무 정의

> _(작성 예정)_

### 선정 도구 및 이유

> _(작성 예정)_

### 워크플로우 설계

```
(다이어그램 또는 흐름 설명 작성 예정)
```

### 워크플로우 구성 화면

> _(스크린샷 추가 예정)_

### 실행 결과 화면

> _(스크린샷 추가 예정)_

---

## 학습 정리

### Trigger와 Action이란?

- **Trigger**: 자동화를 시작하는 이벤트 (예: 새 Form 응답 제출)
- **Action**: Trigger 발생 후 실행되는 동작 (예: 이메일 발송, 시트 기록)

### 조건 분기(Filter/Router)란?

- 데이터 조건에 따라 다른 Action을 실행하도록 흐름을 나누는 기능
- Make: **Router** (하나의 시나리오에서 다중 경로)
- Zapier: **Filter** (조건 불충족 시 Zap 중단)

---

## 사용 도구

- [Make](https://make.com) — 시각적 노드 기반 자동화 플랫폼
- [Zapier](https://zapier.com) — 리스트 기반 자동화 플랫폼
- Google Forms — 설문 데이터 수집
- Google Sheets — 응답 데이터 저장
- Gmail — 자동 이메일 발송
