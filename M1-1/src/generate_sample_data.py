"""합성 환율 데이터 생성기.

네트워크 환경이 제한된 경우에도 동일한 스키마(`date`, `currency`, `rate`)를
가진 SQLite DB와 CSV를 만들 수 있도록 합니다. 실데이터를 대체하는 샘플이므로
모델 평가/분석/리포트 재현의 기준 데이터로 사용할 수 있습니다.

사용 예:
    python src/generate_sample_data.py --start 2023-01-01 --end 2026-08-31
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import date, timedelta

import numpy as np
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "exchange_rates.db")
DEFAULT_CSV_PATH = os.path.join(PROJECT_ROOT, "data", "sample_exchange_rates.csv")

TARGETS = {
    "USD": {"base": 1280.0, "trend": 0.18, "season_amp": 11.0, "noise": 6.5},
    "JPY": {"base": 9.5, "trend": -0.012, "season_amp": 0.25, "noise": 0.18},
    "CNY": {"base": 188.0, "trend": -0.10, "season_amp": 2.2, "noise": 1.3},
}


def business_days(start: date, end: date):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def generate_rates(start: date, end: date) -> pd.DataFrame:
    dates = list(business_days(start, end))
    rows: list[dict] = []
    rng = np.random.default_rng(42)

    for currency, cfg in TARGETS.items():
        t = np.arange(len(dates), dtype=float)
        trend = cfg["base"] + cfg["trend"] * t
        seasonal = np.sin(t / 11.5) * cfg["season_amp"]
        shocks = rng.normal(0, cfg["noise"], size=len(dates))
        values = trend + seasonal + shocks

        if currency == "JPY":
            values = np.clip(values, 6.0, 12.0)
        elif currency == "CNY":
            values = np.clip(values, 150.0, 230.0)
        elif currency == "USD":
            values = np.clip(values, 1180.0, 1400.0)

        for day, value in zip(dates, values):
            rows.append(
                {
                    "date": day.strftime("%Y%m%d"),
                    "currency": currency,
                    "rate": round(float(value), 3),
                }
            )

    frame = pd.DataFrame(rows)
    frame = frame.sort_values(["currency", "date"]).reset_index(drop=True)
    return frame


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS exchange_rates (
            date TEXT NOT NULL,
            currency TEXT NOT NULL,
            rate REAL NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (date, currency)
        )
        """
    )
    conn.commit()


def write_db(frame: pd.DataFrame, db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    init_db(conn)
    fetched_at = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    rows = [
        (row["date"], row["currency"], float(row["rate"]), fetched_at)
        for _, row in frame.iterrows()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO exchange_rates (date, currency, rate, fetched_at) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


def write_csv(frame: pd.DataFrame, csv_path: str) -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    frame.to_csv(csv_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="합성 환율 데이터를 생성해 SQLite/CSV로 저장")
    parser.add_argument("--start", default="2023-01-01", help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-08-31", help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="SQLite DB 경로")
    parser.add_argument("--csv-path", default=DEFAULT_CSV_PATH, help="CSV 경로")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = pd.to_datetime(args.start).date()
    end = pd.to_datetime(args.end).date()
    frame = generate_rates(start, end)
    write_db(frame, args.db_path)
    write_csv(frame, args.csv_path)
    print(f"생성 완료: {len(frame)} rows -> {args.db_path}")
    print(f"생성 완료: {len(frame)} rows -> {args.csv_path}")


if __name__ == "__main__":
    main()
