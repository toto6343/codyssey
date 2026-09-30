from fastapi import APIRouter, Query, Response

from app.schemas import DataCreate, DataOut, DataUpdate, SummaryOut, SyncOut
from app.services import data_service
from app.services.errors import NoDataError

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("", response_model=DataOut, status_code=201, summary="새 데이터 추가")
def create_data(body: DataCreate):
    return data_service.create({"date": body.date.isoformat(), "value": body.value, "memo": body.memo})


@router.get("", response_model=list[DataOut], summary="데이터 목록 조회")
def list_data():
    return data_service.list_all()


@router.get("/summary", response_model=SummaryOut, summary="데이터 요약 (프롬프트 주입용)")
def get_summary():
    summary = data_service.get_summary()
    if summary is None:
        raise NoDataError("저장된 데이터가 없어요.")
    return summary


@router.post("/sync", response_model=SyncOut, summary="KOBIS에서 최신 주말 데이터 가져오기")
def sync_data(weeks: int = Query(8, ge=1, le=12, description="최근 몇 주를 확인할지")):
    return data_service.sync_from_kobis(weeks)


@router.put("/{data_id}", response_model=DataOut, summary="데이터 수정")
def update_data(data_id: str, body: DataUpdate):
    return data_service.update(data_id, body.model_dump())


@router.delete("/{data_id}", status_code=204, summary="데이터 삭제")
def delete_data(data_id: str):
    data_service.delete(data_id)
    return Response(status_code=204)

import csv, io, json
from fastapi import Response

@router.get("/statistics", summary="확장 통계 (중앙값, 표준편차, 월별, 이동평균 등)")
def get_statistics():
    return data_service.get_statistics()


@router.get("/export", summary="데이터 내보내기 (CSV/JSON)")
def export_data(format: str = Query("csv", pattern="^(csv|json)$")):
    items = [
        {"date": str(i["date"]), "value": i["value"], "memo": i.get("memo") or ""}
        for i in data_service.list_all()
    ]
    if format == "json":
        return Response(
            json.dumps(items, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=boxoffice.json"},
        )
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["date", "value", "memo"])
    w.writeheader()
    w.writerows(items)
    return Response(
        "\ufeff" + buf.getvalue(),  # BOM: 엑셀에서 한글 깨짐 방지
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=boxoffice.csv"},
    )