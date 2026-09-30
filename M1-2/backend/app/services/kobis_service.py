"""KOBIS 주간/주말 박스오피스 API 호출. (동기화 API와 수집 스크립트가 함께 사용)"""
import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

from app.config import settings
from app.services.errors import ConfigError

logger = logging.getLogger(__name__)

URL = "http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchWeeklyBoxOfficeList.json"


def last_sunday(today: date | None = None) -> date:
    """직전에 끝난 일요일 (일요일 당일은 집계 전일 수 있어 그 전 주로)."""
    today = today or date.today()
    days_back = (today.weekday() + 1) % 7 or 7
    return today - timedelta(days=days_back)


def fetch_weekend(key: str, target: date) -> dict | None:
    params = urllib.parse.urlencode(
        {"key": key, "targetDt": target.strftime("%Y%m%d"), "weekGb": "1", "itemPerPage": "10"}
    )
    with urllib.request.urlopen(f"{URL}?{params}", timeout=10) as res:
        body = json.load(res)
    result = body.get("boxOfficeResult", {})
    rows = result.get("weeklyBoxOfficeList", [])
    if not rows:
        return None

    start = result["showRange"].split("~")[0]  # 예: "20260925~20260927" -> 금요일
    top = rows[0]
    new_cnt = sum(1 for r in rows if r["rankOldAndNew"] == "NEW")
    return {
        "date": f"{start[:4]}-{start[4:6]}-{start[6:]}",
        "value": sum(int(r["audiCnt"]) for r in rows),
        "memo": f"1위: {top['movieNm']} | 신규 진입 {new_cnt}편",
    }


def require_key() -> str:
    key = settings.kobis_api_key
    if not key:
        raise ConfigError("KOBIS_API_KEY 환경변수가 설정되지 않았어요.")
    return key


def collect(weeks: int, sleep: float = 0.2) -> tuple[list[dict], int]:
    """최근 N개 주말 수집. (기록 목록, 실패한 주 수)를 반환한다."""
    key = require_key()
    end = last_sunday()
    records: list[dict] = []
    failed = 0
    for i in range(weeks):
        target = end - timedelta(weeks=i)
        try:
            rec = fetch_weekend(key, target)
        except Exception:  # 네트워크/파싱 오류는 건너뛰고 계속
            logger.warning("KOBIS 조회 실패: %s", target, exc_info=True)
            failed += 1
            continue
        if rec:
            records.append(rec)
        time.sleep(sleep)
    return sorted(records, key=lambda r: r["date"]), failed
