import time

from google.api_core.exceptions import AlreadyExists

from app.firebase import get_db
from app.services import kobis_service, summary_service
from app.services.errors import ConflictError, NoDataError, NotFoundError, RateLimitError
from collections import defaultdict
from statistics import mean, median, pstdev

COLLECTION = "data"
_CACHE_TTL_SEC = 30  # 채팅마다 Firestore를 전부 읽지 않도록 짧게 캐시
_cache: dict = {"at": 0.0, "rows": None}
_SYNC_COOLDOWN_SEC = 20  # 연타로 KOBIS 호출 한도를 소진하지 않도록
_last_sync = 0.0


def _col():
    return get_db().collection(COLLECTION)


def _invalidate() -> None:
    _cache["rows"] = None


def list_all() -> list[dict]:
    if _cache["rows"] is not None and time.time() - _cache["at"] < _CACHE_TTL_SEC:
        return _cache["rows"]
    rows = [{"id": d.id, **d.to_dict()} for d in _col().order_by("date").stream()]
    _cache.update(at=time.time(), rows=rows)
    return rows


def get_summary() -> dict | None:
    return summary_service.compute_summary(list_all())


def create(item: dict) -> dict:
    ref = _col().document(item["date"])  # 문서 ID = 날짜 (수집 스크립트와 동일)
    try:
        ref.create(item)
    except AlreadyExists:
        raise ConflictError(f"{item['date']} 데이터가 이미 있어요. 수정(PUT)을 사용하세요.")
    _invalidate()
    return {"id": ref.id, **item}


def update(data_id: str, fields: dict) -> dict:
    ref = _col().document(data_id)
    snap = ref.get()
    if not snap.exists:
        raise NotFoundError("해당 데이터를 찾을 수 없어요.")
    ref.update(fields)
    _invalidate()
    return {"id": data_id, **snap.to_dict(), **fields}


def delete(data_id: str) -> None:
    ref = _col().document(data_id)
    if not ref.get().exists:
        raise NotFoundError("해당 데이터를 찾을 수 없어요.")
    ref.delete()
    _invalidate()


def sync_from_kobis(weeks: int) -> dict:
    """KOBIS에서 최근 N개 주말을 가져와 '없는 날짜만' 추가한다 (기존/수정한 데이터는 건드리지 않음)."""
    global _last_sync
    kobis_service.require_key()  # 설정 오류로 실패한 요청이 쿨다운을 소모하지 않도록 먼저 확인
    if time.time() - _last_sync < _SYNC_COOLDOWN_SEC:
        raise RateLimitError("방금 동기화했어요. 잠시 후 다시 시도해 주세요.")
    _last_sync = time.time()

    records, failed = kobis_service.collect(weeks)
    added = skipped = 0
    for rec in records:
        try:
            _col().document(rec["date"]).create(rec)
            added += 1
        except AlreadyExists:
            skipped += 1
    _invalidate()
    return {"fetched": len(records), "added": added, "skipped": skipped, "failed": failed}


def get_statistics() -> dict:
    items = sorted(list_all(), key=lambda i: str(i["date"]))
    if not items:
        raise NoDataError("저장된 데이터가 없어요.")  # 이미 import돼 있지 않으면 app.services.errors에서 import

    values = [i["value"] for i in items]

    monthly = defaultdict(list)
    for i in items:
        monthly[str(i["date"])[:7]].append(i["value"])

    top = max(items, key=lambda i: i["value"])
    prev, last = (values[-2], values[-1]) if len(values) > 1 else (None, values[-1])

    return {
        "median": median(values),
        "std_dev": round(pstdev(values), 2),
        "top_week": {"date": str(top["date"]), "value": top["value"], "memo": top.get("memo")},
        "wow_change_pct": round((last - prev) / prev * 100, 1) if prev else None,  # 직전 주 대비
        "monthly": {m: {"avg": round(mean(v), 2), "max": max(v), "min": min(v), "count": len(v)}
                    for m, v in sorted(monthly.items())},
        "moving_avg_4w": [
            {"date": str(items[k]["date"]), "value": round(mean(values[max(0, k - 3):k + 1]), 2)}
            for k in range(len(items))
        ],
        "series": [{"date": str(i["date"]), "value": i["value"]} for i in items],
    }