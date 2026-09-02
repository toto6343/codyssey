import sqlite3

conn = sqlite3.connect("data/exchange_rates.db")
rows = conn.execute(
    "SELECT date, COUNT(*) FROM exchange_rates GROUP BY date HAVING COUNT(*) < 3"
).fetchall()

if rows:
    print(f"통화 3개가 다 채워지지 않은 날짜 {len(rows)}건:")
    for date, cnt in rows:
        print(f"  {date}: {cnt}개")
else:
    print("빠진 날짜 없음 (모든 영업일에 3개 통화 다 저장됨)")

conn.close()