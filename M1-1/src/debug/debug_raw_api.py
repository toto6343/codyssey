"""
특정 날짜의 수출입은행 API 원본 응답을 그대로 찍어보는 디버그용 스크립트.
CNY(CNH)가 왜 빠졌는지 원본 응답에서 직접 확인한다.
"""
import json
import os
import urllib.request

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_URL = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"
API_KEY = os.environ.get("KOREAEXIM_API_KEY")

DATES = ["20250610", "20250814", "20251119", "20260323", "20260520"]

for date_str in DATES:
    url = f"{API_URL}?authkey={API_KEY}&searchdate={date_str}&data=AP01"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    print(f"\n=== {date_str} ===")
    if not data:
        print("  (빈 응답 - 이 날짜는 API 자체가 아무것도 안 줌)")
        continue

    for rec in data:
        if rec.get("cur_unit") in ("USD", "JPY(100)", "CNH"):
            print(f"  {rec.get('cur_unit')}: result={rec.get('result')}, "
                  f"deal_bas_r={rec.get('deal_bas_r')}, cur_nm={rec.get('cur_nm')}")