"""KOBIS 주말 박스오피스 -> Firestore(data 컬렉션) 초기 적재 스크립트 (최초 1회, 예: 120주)

키는 backend/.env 에서 자동으로 읽습니다. (export 불필요)
backend 가상환경을 켠 상태에서 프로젝트 루트에서 실행하세요.

  python scripts/collect_weekend_boxoffice.py --weeks 120 --dry-run   # data.json만 생성
  python scripts/collect_weekend_boxoffice.py --weeks 120             # Firestore 적재

이후 새 주말 데이터는 웹 화면의 '최신 데이터 가져오기' 버튼(POST /api/data/sync)으로 추가합니다.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services import kobis_service  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=120)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    records, failed = kobis_service.collect(args.weeks)
    for r in records:
        print(f"[ok] {r['date']} {r['value']:,} {r['memo']}")
    Path("data.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n수집 {len(records)}건 (실패 {failed}주) -> data.json")

    if args.dry_run:
        return

    from app.firebase import get_db

    db = get_db()
    batch = db.batch()
    for r in records:  # 문서 ID = date -> 여러 번 실행해도 중복되지 않음
        batch.set(db.collection("data").document(r["date"]), r)
    batch.commit()
    print(f"Firestore data 컬렉션에 {len(records)}건 저장 완료")


if __name__ == "__main__":
    main()
