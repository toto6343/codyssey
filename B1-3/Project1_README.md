# 노코드 자동화 도구 비교 및 구현 프로젝트

> 코딩 없이 마우스 클릭만으로 반복 업무를 자동화하는 노코드 자동화 도구(Make, Zapier)를 비교 분석하고, 자유 주제로 나만의 자동화 파이프라인을 설계·구현한 프로젝트입니다.

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

![Make 워크플로우]<img width="1110" height="736" alt="Image" src="https://github.com/user-attachments/assets/d5d9b693-7cad-4e96-8c83-86c1842718c2" />

#### 실행 결과 화면

![Make 긍정 응답 이메일]
<img width="855" height="154" alt="Image" src="https://github.com/user-attachments/assets/1b94a2d4-087f-49ff-9822-427c518164aa" />

![Make 개선 필요 이메일]


<img width="747" height="162" alt="Image" src="https://github.com/user-attachments/assets/1b5e2ab7-90e1-4f59-81eb-e47815786b53" />

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

![Zapier Zap1 워크플로우]
<img width="471" height="819" alt="Image" src="https://github.com/user-attachments/assets/8de4c6b6-90be-412f-bf1a-08ea61765159" />
![Zapier Zap2 워크플로우]
<img width="480" height="802" alt="Image" src="https://github.com/user-attachments/assets/f6665ccf-71db-4251-9b99-952f24f71a46" />

#### 실행 결과

Filter 기능은 유료 플랜이 필요하여 실행 결과를 첨부하지 못했다.

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
