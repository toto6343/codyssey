"""시계열 데이터 -> 요약 정보 계산 (순수 파이썬, 외부 의존성 없음)."""
from datetime import date, timedelta
from statistics import mean

WINDOW_DAYS = 27  # 최근 4개 주말을 포함하는 구간 (금요일 기준 0/7/14/21일 전)
MIN_POINTS = 3  # 비교 구간에 최소 이 개수의 데이터가 있어야 비교
THRESHOLD_PCT = 5.0  # ±5% 이내면 '유지'


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _pct(new: float, old: float) -> float | None:
    return round((new - old) / old * 100, 1) if old else None


def _label(pct: float | None) -> str:
    if pct is None:
        return "판단 불가"
    if pct > THRESHOLD_PCT:
        return "상승"
    if pct < -THRESHOLD_PCT:
        return "하락"
    return "유지"


def _window_avg(rows: list[dict], start: date, end: date) -> tuple[float | None, int]:
    vals = [r["value"] for r in rows if start <= _d(r["date"]) <= end]
    return (mean(vals), len(vals)) if vals else (None, 0)


def _point(r: dict) -> dict:
    return {"date": r["date"], "value": r["value"], "memo": r.get("memo", "")}


def compute_summary(records: list[dict]) -> dict | None:
    if not records:
        return None

    rows = sorted(records, key=lambda r: r["date"])
    values = [r["value"] for r in rows]
    hi = max(rows, key=lambda r: r["value"])
    lo = min(rows, key=lambda r: r["value"])
    latest = rows[-1]
    end = _d(latest["date"])

    # 최근 4주 vs 직전 4주 (날짜 기준 구간이라 결측 주가 있어도 안전)
    recent_avg, _ = _window_avg(rows, end - timedelta(days=WINDOW_DAYS), end)
    prev_avg, prev_n = _window_avg(
        rows, end - timedelta(days=WINDOW_DAYS + 28), end - timedelta(days=28)
    )
    trend_pct = _pct(recent_avg, prev_avg) if prev_n >= MIN_POINTS and prev_avg else None
    trend = (
        f"최근 4주 평균이 직전 4주 대비 {trend_pct:+.1f}% ({_label(trend_pct)})"
        if trend_pct is not None
        else "비교할 이전 데이터가 부족해 판단 불가"
    )

    # 전년 동기 대비: 같은 4주 구간을 52주(364일, 같은 금요일) 전과 비교
    shift = timedelta(days=364)
    ly_avg, ly_n = _window_avg(rows, end - shift - timedelta(days=WINDOW_DAYS), end - shift)
    yoy_pct = _pct(recent_avg, ly_avg) if ly_n >= MIN_POINTS and ly_avg else None
    yoy = (
        f"작년 같은 시기(최근 4주 기준) 대비 {yoy_pct:+.1f}% ({_label(yoy_pct)})"
        if yoy_pct is not None
        else None
    )

    return {
        "period": f"{rows[0]['date']} ~ {rows[-1]['date']}",
        "count": len(rows),
        "metrics": {
            "total": sum(values),
            "average": round(mean(values)),
            "max": hi["value"],
            "max_date": hi["date"],
            "max_memo": hi.get("memo", ""),
            "min": lo["value"],
            "min_date": lo["date"],
            "min_memo": lo.get("memo", ""),
        },
        "latest": _point(latest),
        "trend": trend,
        "trend_pct": trend_pct,
        "yoy": yoy,
        "yoy_pct": yoy_pct,
        "top5": [_point(r) for r in sorted(rows, key=lambda r: r["value"], reverse=True)[:5]],
    }
