"""
OpenRouter API 연동 — AI 보조 해석
===================================
분석 과정에서 아래 3가지 작업에 대해서만 AI(OpenRouter 경유 LLM)를 사용하고,
모든 호출을 `data/ai_usage_log.jsonl`에 남깁니다.

    1. 전처리 방침 초안 검토 (결측치/이상치 처리 기준 제안)
    2. 통계 요약(관찰)을 바탕으로 인사이트 문장 초안 생성
    3. 리포트 문장 다듬기(맞춤법/가독성)

각 호출은 (task, reason, prompt, response, verified_by) 를 기록해
"AI 사용 로그" 섹션(REPORT.md §7)의 근거 데이터로 사용합니다.

[수정 사항]
- 스크립트 폴더의 .env 파일에서 OPENROUTER_API_KEY를 자동으로
  읽어오도록 python-dotenv 연동을 추가했습니다.
- [추가] MODEL = "openrouter/free"는 OpenRouter가 제공하는 무료 모델
  라우터로, 요청 특성에 맞는 무료 모델을 자동 선택합니다(유효한 값입니다).
- [추가] requests 호출 실패(타임아웃/레이트리밋/네트워크 오류) 시
  스크립트가 아무 로그도 안 남기고 죽는 문제가 있어, 실패도 로그에
  남기도록 try/except를 추가했습니다.
- [추가] __main__ 블록의 실행 예시를 하드코딩된 통계값 대신, 실제
  analyze.py 파이프라인(load_long_df -> to_wide -> clean)에서 나온
  진짜 데이터 기반으로 바꿨습니다. 이렇게 실행해야 ai_usage_log.jsonl에
  근거 있는 로그가 남고, 리포트 §7에 그대로 인용할 수 있습니다.
"""

import datetime as dt
import json
import os

import requests

try:
    from dotenv import load_dotenv
    # 이 파일(src/)과 같은 폴더의 .env를 읽는다. 이미 export된 환경변수가 있으면 그걸 우선함.
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=False)
except ImportError:
    print(
        "  [info] python-dotenv가 설치되어 있지 않아 .env 파일을 읽지 못했습니다. "
        "pip install python-dotenv --break-system-packages 를 실행하거나, "
        "환경변수를 직접 export 해주세요."
    )

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ai_usage_log.jsonl")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"  # OpenRouter의 무료 모델 라우터. 특정 모델을 고정하고 싶다면
                            # 모델 카탈로그(https://openrouter.ai/models)에서 slug를 확인해 교체


def _log(task: str, reason: str, prompt: str, response: str, verified_by: str) -> None:
    entry = {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "task": task,
        "reason": reason,
        "prompt": prompt,
        "response_preview": response[:500],
        "verified_by": verified_by,
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _log_failure(task: str, reason: str, prompt: str, error: str) -> None:
    """API 호출 자체가 실패했을 때도 흔적을 남긴다(원인 파악 및 재현성 목적)."""
    entry = {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "task": task,
        "reason": reason,
        "prompt": prompt,
        "response_preview": None,
        "error": error,
        "verified_by": None,
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def call_openrouter(prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENROUTER_API_KEY 를 찾을 수 없습니다.\n"
            f"  1) {os.path.join(os.path.dirname(__file__), '.env')} 파일에 "
            "OPENROUTER_API_KEY=발급받은키 형태로 넣거나\n"
            "  2) export OPENROUTER_API_KEY=발급받은키 로 환경변수를 직접 설정하세요.\n"
            "발급: https://openrouter.ai/keys"
        )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        # 네트워크 오류/타임아웃/4xx·5xx 등 - 호출 실패 자체를 예외로 다시 던지되,
        # 호출부(suggest_outlier_policy 등)에서 실패 로그를 남길 수 있도록 그대로 전파한다.
        print(f"  [warn] OpenRouter 호출 실패: {e}")
        raise
    except (KeyError, IndexError) as e:
        # 응답은 왔지만 예상한 구조(choices[0].message.content)가 아닌 경우
        print(f"  [warn] OpenRouter 응답 파싱 실패: {e}")
        raise


def suggest_outlier_policy(summary_stats: str) -> str:
    """작업1: 결측치/이상치 처리 기준 초안 제안 (사람이 최종 검토/적용)."""
    task = "전처리 방침 초안 검토(결측치/이상치 기준 제안)"
    reason = "사람이 직접 기준을 정하기 전, 통계적으로 흔히 쓰이는 대안을 빠르게 훑어보기 위함(시간 절감)"
    prompt = (
        "다음은 환율 시계열 데이터의 기술통계 요약입니다. 결측치와 이상치를 "
        "어떤 기준(예: IQR, 표준편차 배수)으로 처리하면 좋을지 2~3문장으로 "
        f"제안해줘. 근거도 함께 제시해줘.\n\n{summary_stats}"
    )
    try:
        response = call_openrouter(prompt)
    except (requests.RequestException, KeyError, IndexError) as e:
        _log_failure(task, reason, prompt, error=str(e))
        raise
    _log(
        task=task,
        reason=reason,
        prompt=prompt,
        response=response,
        verified_by="제안된 기준(예: IQR 1.5배)을 실제 데이터에 적용한 뒤 그래프로 결과를 육안 검증, "
        "업계 관행(구간별 롤링 median/IQR)과 대조",
    )
    return response


def draft_insight(observation: str) -> str:
    """작업2: 관찰(수치 근거) -> 인사이트 문장 초안 생성 (최종 해석/결론은 사람이 작성)."""
    task = "인사이트 문장 초안 생성(관찰 -> 해석 가설)"
    reason = "여러 해석 가설을 빠르게 브레인스토밍하기 위함(대안 탐색)"
    prompt = (
        "다음은 환율 데이터에서 관찰된 사실(수치)입니다. 이 관찰을 바탕으로 "
        "가능한 해석 가설을 1~2개, 그리고 반례 가능성도 함께 3문장 이내로 "
        f"제시해줘.\n\n관찰: {observation}"
    )
    try:
        response = call_openrouter(prompt)
    except (requests.RequestException, KeyError, IndexError) as e:
        _log_failure(task, reason, prompt, error=str(e))
        raise
    _log(
        task=task,
        reason=reason,
        prompt=prompt,
        response=response,
        verified_by="제시된 가설을 실제 동기간 뉴스/거시지표(금리, 반도체 업황 등)와 대조하여 "
        "타당성 있는 가설만 REPORT.md에 채택, 근거 없는 가설은 한계점으로 이동",
    )
    return response


def polish_text(draft: str) -> str:
    """작업3: 리포트 문장 다듬기 (맞춤법/가독성). 사실관계는 변경하지 않도록 사람이 diff 확인."""
    task = "리포트 문장 다듬기(맞춤법/가독성)"
    reason = "초안 대비 가독성 향상, 사실관계 왜곡 여부는 사람이 직접 대조(검증 목적)"
    prompt = f"다음 한국어 문장을 사실관계는 바꾸지 말고 자연스럽게 다듬어줘:\n\n{draft}"
    try:
        response = call_openrouter(prompt)
    except (requests.RequestException, KeyError, IndexError) as e:
        _log_failure(task, reason, prompt, error=str(e))
        raise
    _log(
        task=task,
        reason=reason,
        prompt=prompt,
        response=response,
        verified_by="원문과 다듬어진 문장을 줄 단위로 diff 비교하여 수치/사실 왜곡 여부 확인",
    )
    return response


if __name__ == "__main__":
    # 실행 예시: 하드코딩된 통계값 대신, 실제 analyze.py 파이프라인에서 나온
    # 데이터를 사용한다. 이렇게 해야 ai_usage_log.jsonl에 실제 근거가 남고
    # REPORT.md §7 "AI 사용 로그"에 그대로 인용할 수 있다.
    from analyze import load_long_df, to_wide, clean

    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "exchange_rates.db")
    long_df = load_long_df(db_path)
    wide = to_wide(long_df)
    cleaned, report = clean(wide)

    # 정제 전 원본 기준 기술통계 + clean() 처리 결과를 함께 프롬프트에 포함
    stats_text = wide.describe().to_string()
    clean_report_text = json.dumps(report, ensure_ascii=False)
    example_stats = (
        f"[원본 데이터 기술통계]\n{stats_text}\n\n"
        f"[적용한 정제 결과(수익률 기준 z-score, |z|>3)]\n{clean_report_text}"
    )
    print(suggest_outlier_policy(example_stats))