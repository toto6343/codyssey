#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
travel_planner.py

OpenAI(ChatGPT) API(LLM) + Naver Local Search API(지도/장소 검색)를 조합하여
국내 여행 추천 리포트를 생성하는 CLI 프로그램.

실행 예:
    python travel_planner.py --date "2026-03-15"

보너스 기능:
    - 복수 지역 추천 (recommended_cities: 2~3개)
    - 결과 캐싱 (같은 --date 로 재실행 시 이미 저장된 원본 JSON이 있으면
      API 호출을 건너뛰고 저장된 데이터로 리포트만 재생성)
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv가 없어도 이미 설정된 환경변수만으로 동작 가능하도록 함
    pass


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

RESULTS_DIR = Path("results")
RESTAURANT_COUNT = 5          # 도시별 검색할 맛집 개수
MAX_CITIES = 3                # 1차 추천 최대 지역 수 (보너스: 복수 지역)
LLM_JSON_RETRY = 1             # LLM JSON 파싱 실패 시 재시도 횟수 (최대 1회)


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------

def check_api_keys():
    """API 키가 설정되어 있는지 확인하고, 없으면 안내 후 즉시 종료한다."""
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not NAVER_CLIENT_ID:
        missing.append("NAVER_CLIENT_ID")
    if not NAVER_CLIENT_SECRET:
        missing.append("NAVER_CLIENT_SECRET")

    if missing:
        print("[오류] 다음 환경변수가 설정되지 않았습니다:", ", ".join(missing))
        print()
        print("설정 방법:")
        print("  1) 프로젝트 루트에 .env 파일을 만들고 아래처럼 작성하세요.")
        print("       OPENAI_API_KEY=your_openai_api_key")
        print("       NAVER_CLIENT_ID=your_naver_client_id")
        print("       NAVER_CLIENT_SECRET=your_naver_client_secret")
        print("  2) 또는 터미널에서 환경변수로 직접 설정하세요. (README.md 참고)")
        sys.exit(1)


def validate_date(date_str: str) -> str:
    """YYYY-MM-DD 형식인지 검증한다. 아니면 사용법을 출력하고 종료한다."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        print(f"[오류] 날짜 형식이 올바르지 않습니다: '{date_str}'")
        print("사용법: python travel_planner.py --date \"YYYY-MM-DD\"")
        print("예시  : python travel_planner.py --date \"2026-03-15\"")
        sys.exit(1)


def extract_json(text: str) -> dict:
    """LLM 응답 텍스트에서 JSON 객체만 뽑아 파싱한다.
    코드펜스(```json ... ```)나 앞뒤 설명 문구가 섞여 있어도 최대한 복구한다."""
    cleaned = text.strip()
    # 코드펜스 제거
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 본문 중간에 JSON이 섞여 있는 경우, 첫 '{' 와 마지막 '}' 사이만 추출
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start:end + 1]
        return json.loads(candidate)

    raise ValueError("응답에서 JSON 객체를 찾을 수 없습니다.")


# ---------------------------------------------------------------------------
# OpenAI (ChatGPT) API 호출
# ---------------------------------------------------------------------------

OPENAI_MAX_RETRIES_429 = 3          # 429(rate limit) 발생 시 자동 재시도 횟수
OPENAI_DEFAULT_BACKOFF_SEC = 20      # Retry-After 헤더가 없을 때 기본 대기 시간(초)


def _mask_key(text: str) -> str:
    """에러 메시지/URL에 API 키가 그대로 노출되지 않도록 마스킹한다."""
    if not OPENAI_API_KEY:
        return text
    return text.replace(OPENAI_API_KEY, "***MASKED***")


def call_openai(prompt: str, temperature: float = 0.7, timeout: int = 30) -> str:
    """OpenAI Chat Completions API를 호출하고 텍스트 응답을 반환한다.

    - 실패 시 HTTP 상태 코드/응답 본문 등 구체적인 원인을 담은 예외를 던진다.
      (API 키는 마스킹하여 로그/에러 메시지에 절대 그대로 남지 않도록 한다.)
    - 429(Too Many Requests, rate limit 또는 quota 초과)는 서버가 응답한
      Retry-After 시간만큼 대기 후 최대 OPENAI_MAX_RETRIES_429회까지 자동 재시도한다.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 비어 있습니다. .env 설정을 확인하세요.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    last_error = None
    for attempt in range(OPENAI_MAX_RETRIES_429 + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"OpenAI API 네트워크 오류: {type(e).__name__}: {e}") from e

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            try:
                wait_sec = float(retry_after) if retry_after else OPENAI_DEFAULT_BACKOFF_SEC * (attempt + 1)
            except ValueError:
                wait_sec = OPENAI_DEFAULT_BACKOFF_SEC * (attempt + 1)

            last_error = _mask_key(resp.text[:500])
            if attempt < OPENAI_MAX_RETRIES_429:
                print(f"    [경고] 429 Too Many Requests - {wait_sec:.0f}초 대기 후 재시도 "
                      f"({attempt + 1}/{OPENAI_MAX_RETRIES_429})...")
                # rate_limit_exceeded / insufficient_quota 등 정확한 원인을 바로 확인할 수 있도록 출력한다.
                print(f"    [상세] {last_error}")
                time.sleep(wait_sec)
                continue
            raise RuntimeError(
                f"OpenAI API 요청 한도 초과(HTTP 429, model='{OPENAI_MODEL}')가 계속되어 포기합니다. "
                f"플랜의 rate limit / quota를 확인하세요. 응답: {last_error}"
            )

        if resp.status_code != 200:
            # 응답 본문에 실제 원인(잘못된 모델명, API 키 오류 등)이 들어있으므로 그대로 노출하되 키는 마스킹한다.
            detail = _mask_key(resp.text[:500])
            raise RuntimeError(
                f"OpenAI API 오류 (HTTP {resp.status_code}, model='{OPENAI_MODEL}'): {detail}"
            )

        data = resp.json()

        choices = data.get("choices") or []
        if not choices:
            raise ValueError(f"OpenAI 응답에 choices가 없습니다. 응답: {json.dumps(data, ensure_ascii=False)[:300]}")

        message = choices[0].get("message", {})
        text = message.get("content", "")
        if not text:
            finish_reason = choices[0].get("finish_reason")
            raise ValueError(f"OpenAI 응답에서 텍스트를 추출할 수 없습니다. finish_reason={finish_reason}")
        return text

    # 이론상 도달하지 않지만 안전망으로 남겨둔다.
    raise RuntimeError(f"OpenAI API 호출 실패: {last_error}")


# ---------------------------------------------------------------------------
# 1단계: LLM 1차 추천 (날씨/행사 정보) - 복수 지역 (보너스)
# ---------------------------------------------------------------------------

RECOMMEND_PROMPT_TEMPLATE = """당신은 국내 여행 추천 전문가입니다.
아래 여행 날짜를 기준으로, 그 시기에 여행하기 좋은 국내 지역을 1~{max_cities}곳 추천해주세요.

여행 날짜: {date}

반드시 아래 JSON 스키마와 정확히 일치하는 JSON "만" 출력하세요.
설명 문구, 코드펜스(```), 그 어떤 추가 텍스트도 포함하지 마세요.

{{
  "recommended_cities": [
    {{
      "city": "지역명 (예: 제주, 강릉)",
      "weather": "해당 시기 일반적인 날씨 요약 (문자열)",
      "events": ["행사/축제 후보 1", "행사/축제 후보 2"],
      "reason": "추천 근거 2~4문장 (문자열)"
    }}
  ]
}}

주의사항:
- recommended_cities 배열의 길이는 1~{max_cities} 사이여야 합니다.
- 실제 날씨/행사 데이터의 정확한 사실 여부보다, 스키마를 정확히 지키는 것이 중요합니다.
- city 값은 지도 검색에 사용되므로 실제 존재하는 국내 지명이어야 합니다.
"""

RECOMMEND_RETRY_TEMPLATE = """다음 요청에 대한 이전 응답이 올바른 JSON으로 파싱되지 않았습니다.
이번에는 아래 필수 키만 포함한 JSON 객체를 다른 텍스트 없이 정확히 출력하세요.

필수 스키마:
{{
  "recommended_cities": [
    {{"city": "string", "weather": "string", "events": ["string"], "reason": "string"}}
  ]
}}

여행 날짜: {date}
"""


def get_recommendation(date_str: str, errors: list) -> dict:
    """LLM을 호출하여 1차 추천 JSON을 받아온다. 실패 시 1회 재시도한다."""
    prompt = RECOMMEND_PROMPT_TEMPLATE.format(date=date_str, max_cities=MAX_CITIES)

    try:
        text = call_openai(prompt)
        parsed = extract_json(text)
        _validate_recommendation_schema(parsed)
        return parsed
    except Exception as e:
        first_error = str(e)
        # 콘솔에 즉시 원인을 출력 (기존에는 raw_data.json에만 조용히 기록되어 원인 파악이 어려웠음)
        print(f"    [경고] 1차 추천 1차 시도 실패: {first_error}")

    # 재시도 (최대 1회)
    for attempt in range(LLM_JSON_RETRY):
        try:
            retry_prompt = RECOMMEND_RETRY_TEMPLATE.format(date=date_str)
            text = call_openai(retry_prompt, temperature=0.3)
            parsed = extract_json(text)
            _validate_recommendation_schema(parsed)
            return parsed
        except Exception as e2:
            print(f"    [경고] 1차 추천 재시도 실패: {e2}")
            errors.append({
                "step": "llm_recommend",
                "type": "LLM_PARSE_ERROR",
                "message": f"1차 시도 실패: {first_error} / 재시도 실패: {e2}",
            })

    # 최종 실패 - 빈 추천으로 진행 (프로그램은 중단하지 않음)
    return {"recommended_cities": []}


def _validate_recommendation_schema(parsed: dict):
    if not isinstance(parsed, dict) or "recommended_cities" not in parsed:
        raise ValueError("recommended_cities 키가 없습니다.")
    if not isinstance(parsed["recommended_cities"], list):
        raise ValueError("recommended_cities는 배열이어야 합니다.")
    for item in parsed["recommended_cities"]:
        if "city" not in item:
            raise ValueError("각 항목에 city 키가 필요합니다.")


# ---------------------------------------------------------------------------
# 2단계: Naver Local Search API - 맛집 검색
# ---------------------------------------------------------------------------

def search_restaurants(city: str, errors: list, count: int = RESTAURANT_COUNT) -> list:
    """Naver 지역 검색 API로 해당 city의 맛집을 검색한다.
    실패/0건이어도 프로그램은 중단하지 않고 빈 리스트를 반환한다."""
    if not city:
        return []

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": f"{city} 맛집",
        "display": count,
        "sort": "random",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)

        if resp.status_code in (401, 403):
            message = f"HTTP {resp.status_code} (city={city}) - 키/헤더명을 확인하세요. 응답: {resp.text[:300]}"
            print(f"    [경고] {message}")
            errors.append({
                "step": "place_search",
                "type": "AUTH_ERROR",
                "message": message,
            })
            return []

        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])

        results = []
        for it in items:
            name = re.sub(r"<.*?>", "", it.get("title", ""))
            address = it.get("roadAddress") or it.get("address", "")
            # Naver 지역 검색의 mapx/mapy는 좌표값(문자열)을 10^7 배 한 값으로 내려온다.
            # 실제 좌표계(경도/위도 혹은 TM128/KATEC)는 API 버전에 따라 다를 수 있으므로
            # 정확한 지도 표시가 필요하다면 Naver 개발자 문서를 참고해 변환해야 한다.
            mapx = it.get("mapx")
            mapy = it.get("mapy")
            try:
                x = int(mapx) / 1e7 if mapx else None
                y = int(mapy) / 1e7 if mapy else None
            except (TypeError, ValueError):
                x, y = mapx, mapy

            results.append({
                "name": name,
                "address": address,
                "category": it.get("category", ""),
                "url": it.get("link", ""),
                "x": x,
                "y": y,
            })

        if not results:
            errors.append({
                "step": "place_search",
                "type": "EMPTY_RESULT",
                "message": f"0 results for query='{city} 맛집'",
            })

        return results

    except requests.exceptions.RequestException as e:
        message = f"{type(e).__name__}: {e} (city={city})"
        print(f"    [경고] {message}")
        errors.append({
            "step": "place_search",
            "type": "NETWORK_ERROR",
            "message": message,
        })
        return []


# ---------------------------------------------------------------------------
# 3단계: LLM 최종 리포트 생성
# ---------------------------------------------------------------------------

def build_report_prompt(date_str: str, recommendation: dict, restaurants_map: dict, errors: list) -> str:
    payload = {
        "date": date_str,
        "recommended_cities": recommendation.get("recommended_cities", []),
        "restaurants": restaurants_map,
        "errors": errors,
    }
    return f"""당신은 여행 리포트 작성 전문가입니다.
아래 JSON 데이터를 바탕으로 국내 여행 추천 리포트를 Markdown 형식으로 작성하세요.

데이터:
{json.dumps(payload, ensure_ascii=False, indent=2)}

리포트 작성 규칙:
1. 최상단에 "# {date_str} 국내 여행 추천 리포트" 제목을 넣으세요.
2. recommended_cities 배열의 각 도시마다 "## {{도시명}}" 섹션을 만들고, 그 안에
   "### 추천 이유", "### 날씨 요약", "### 행사/축제", "### 맛집 추천", "### 1일 일정 제안"
   소제목을 포함하세요.
3. 맛집 추천 항목에서 restaurants 데이터가 비어있으면 반드시 "데이터 없음"이라고 표기하세요.
   맛집이 있다면 이름/주소/카테고리를 목록으로 정리하세요.
4. 1일 일정 제안은 오전/오후/저녁 수준으로 간단히 작성하세요.
5. 맨 마지막에 "## 오류 요약" 섹션을 만들고 errors 배열 내용을 간단히 요약하세요.
   errors가 비어있으면 "오류 없음"이라고 표기하세요.
6. Markdown 텍스트만 출력하세요. 코드펜스나 별도 설명을 붙이지 마세요.
"""


def fallback_report(date_str: str, recommendation: dict, restaurants_map: dict, errors: list) -> str:
    """LLM 호출이 실패했을 때 사용할, 코드로 직접 구성하는 대체 리포트."""
    lines = [f"# {date_str} 국내 여행 추천 리포트", ""]
    cities = recommendation.get("recommended_cities", [])

    if not cities:
        lines.append("추천 지역 정보를 가져오지 못했습니다.")
    else:
        for c in cities:
            city = c.get("city", "알 수 없음")
            lines.append(f"## {city}")
            lines.append("### 추천 이유")
            lines.append(c.get("reason", "정보 없음"))
            lines.append("### 날씨 요약")
            lines.append(c.get("weather", "정보 없음"))
            lines.append("### 행사/축제")
            events = c.get("events") or []
            if events:
                for ev in events:
                    lines.append(f"- {ev}")
            else:
                lines.append("- 데이터 없음")
            lines.append("### 맛집 추천")
            spots = restaurants_map.get(city, [])
            if spots:
                for s in spots:
                    lines.append(f"- {s.get('name')} ({s.get('category', '')}) - {s.get('address', '')}")
            else:
                lines.append("- 데이터 없음")
            lines.append("### 1일 일정 제안")
            lines.append("- 오전: 자유 일정")
            lines.append("- 오후: 자유 일정")
            lines.append("- 저녁: 자유 일정")
            lines.append("")

    lines.append("## 오류 요약")
    if errors:
        for e in errors:
            lines.append(f"- [{e.get('type')}] {e.get('step')}: {e.get('message')}")
    else:
        lines.append("오류 없음")

    return "\n".join(lines)


def generate_final_report(date_str: str, recommendation: dict, restaurants_map: dict, errors: list) -> str:
    prompt = build_report_prompt(date_str, recommendation, restaurants_map, errors)
    try:
        text = call_openai(prompt, temperature=0.5, timeout=45)
        cleaned = re.sub(r"^```(?:markdown|md)?\s*", "", text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned
    except Exception as e:
        print(f"    [경고] 최종 리포트 생성 실패, 대체 리포트로 전환: {e}")
        errors.append({
            "step": "llm_report",
            "type": "LLM_ERROR",
            "message": str(e),
        })
        return fallback_report(date_str, recommendation, restaurants_map, errors)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="LLM(OpenAI ChatGPT) + 지도(Naver Local) API를 활용한 국내 여행 추천 프로그램"
    )
    parser.add_argument("--date", required=True, help='여행 날짜, 형식: "YYYY-MM-DD"')
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="캐시된 결과가 있어도 API를 다시 호출하여 새로 생성한다.",
    )
    args = parser.parse_args()

    date_str = validate_date(args.date)
    check_api_keys()

    RESULTS_DIR.mkdir(exist_ok=True)
    raw_json_path = RESULTS_DIR / f"{date_str}_raw_data.json"
    md_path = RESULTS_DIR / f"{date_str}_travel_plan.md"

    errors = []
    cached = None
    if raw_json_path.exists() and not args.no_cache:
        try:
            cached = json.loads(raw_json_path.read_text(encoding="utf-8"))
            print(f"[캐시] 기존 원본 데이터({raw_json_path})를 발견했습니다. API 호출 없이 재사용합니다.")
        except (json.JSONDecodeError, OSError):
            cached = None

    if cached:
        recommendation = cached.get("recommendation", {"recommended_cities": []})
        restaurants_map = cached.get("restaurants", {})
        errors = cached.get("errors", [])
        cities = [c.get("city") for c in recommendation.get("recommended_cities", [])]
    else:
        print("[1/3] 1차 추천 생성 중(LLM)...")
        recommendation = get_recommendation(date_str, errors)
        cities = [c.get("city") for c in recommendation.get("recommended_cities", []) if c.get("city")]
        if cities:
            for c in cities:
                print(f"    - recommended_city: \"{c}\"")
        else:
            print("    - 추천 지역을 가져오지 못했습니다. 원인:")
            for e in errors:
                print(f"        [{e.get('type')}] {e.get('message')}")

        print("[2/3] 맛집 검색 중(지도/장소 API)...")
        restaurants_map = {}
        if not cities:
            print("    - 추천된 지역이 없어 맛집 검색을 건너뜁니다.")
        for city in cities:
            spots = search_restaurants(city, errors)
            restaurants_map[city] = spots
            print(f"    - {city}: 맛집 {len(spots)}곳 검색 완료")

    print("[3/3] 최종 리포트 생성 중(LLM)...")
    report_md = generate_final_report(date_str, recommendation, restaurants_map, errors)
    print("    - 리포트 생성 완료")

    raw_data = {
        "date": date_str,
        "recommendation": recommendation,
        "restaurants": restaurants_map,
        "errors": errors,
    }
    raw_json_path.write_text(json.dumps(raw_data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(report_md, encoding="utf-8")

    print()
    print(f"완료! {md_path} 를 확인하세요.")
    if errors:
        print(f"⚠ 실행 중 {len(errors)}건의 오류가 있었습니다. 자세한 내용은 {raw_json_path} 의 errors 항목을 참고하세요.")


if __name__ == "__main__":
    main()