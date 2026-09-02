import sqlite3

TARGET_DATES = ["20250610", "20250814", "20251119", "20260323", "20260520"]
ALL_CURRENCIES = {"USD", "JPY", "CNY"}

conn = sqlite3.connect("data/exchange_rates.db")

for date in TARGET_DATES:
    rows = conn.execute(
        "SELECT currency FROM exchange_rates WHERE date = ?", (date,)
    ).fetchall()
    present = {r[0] for r in rows}
    missing = ALL_CURRENCIES - present
    print(f"{date}: 존재={sorted(present)}  누락={sorted(missing)}")

conn.close()