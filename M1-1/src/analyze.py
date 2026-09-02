"""분석 유틸 함수 모음 (이동평균 / 변화율 / 월별 통계 / 변동성 / 분해 / 베이스라인 예측)."""

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose


def load_long_df(db_path: str) -> pd.DataFrame:
    import sqlite3

    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT date, currency, rate FROM exchange_rates", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    return df.sort_values(["currency", "date"])


def to_wide(long_df: pd.DataFrame) -> pd.DataFrame:
    wide = long_df.pivot(index="date", columns="currency", values="rate").sort_index()
    return wide


def clean(
    wide: pd.DataFrame,
    z_thresh: float = 3.0,
    level_window: int = 20,
    level_z_thresh: float = 5.0,
):
    report = {}
    cleaned = wide.copy()
    for col in cleaned.columns:
        n_missing = int(cleaned[col].isna().sum())
        cleaned[col] = cleaned[col].interpolate(method="linear").ffill().bfill()

        # (1) 수익률 기준 이상치: 하루짜리 급등락(스파이크 후 복귀) 탐지
        ret = cleaned[col].pct_change()
        z = (ret - ret.mean()) / ret.std()
        return_outlier_mask = z.abs() > z_thresh

        # (2) 레벨 점프 기준 이상치: rolling median 대비 편차 탐지
        #
        # [추가 이유] (1)의 수익률 기준 z-score는 '스파이크 후 즉시 복귀'하는
        # 패턴에는 잘 작동하지만, 하루 만에 레벨이 이동한 뒤 그 상태로 며칠~몇 주
        # 유지되는 '레벨 점프'는 잡아내지 못한다. 예를 들어 이 데이터의 USD는
        # 2024-07-16에 하루 만에 약 3.5% 뛴 뒤(1292 -> 1337) 그 수준을 계속
        # 유지하는데, 이때의 수익률 z-score(약 2.9)는 임계값(3.0)에 살짝 못
        # 미쳐 탐지되지 않았다. 레벨 자체가 최근 구간의 중앙값(median)에서
        # 얼마나 벗어났는지를 MAD(median absolute deviation) 기준으로 보는
        # robust z-score를 함께 사용하면, 점프 직후 며칠(rolling median이
        # 새 레벨을 따라잡기 전까지)을 이상치로 잡아 완만하게 보간하게 된다.
        # 즉 레벨이 실제로 계단식으로 튄 '전환 구간'만 다듬고, 이미 새 레벨에
        # 안착한 이후의 데이터는 그대로 둔다(중앙값이 새 레벨을 따라잡으면
        # 더 이상 이상치로 잡히지 않기 때문).
        med = cleaned[col].rolling(window=level_window, min_periods=5).median()
        mad = (cleaned[col] - med).abs().rolling(window=level_window, min_periods=5).median()
        level_z = 0.6745 * (cleaned[col] - med) / mad.replace(0, np.nan)
        level_outlier_mask = level_z.abs() > level_z_thresh

        outlier_mask = return_outlier_mask | level_outlier_mask
        n_outliers = int(outlier_mask.sum())
        n_return_only = int((return_outlier_mask & ~level_outlier_mask).sum())
        n_level_only = int((level_outlier_mask & ~return_outlier_mask).sum())

        cleaned.loc[outlier_mask, col] = np.nan  # 이상치도 결측 처리 후 보간
        cleaned[col] = cleaned[col].interpolate(method="linear").ffill().bfill()

        report[col] = {
            "missing_filled": n_missing,
            "outliers_replaced": n_outliers,
            "return_based_only": n_return_only,
            "level_jump_only": n_level_only,
        }
    return cleaned, report


def moving_average(wide, window=20):
    return wide.rolling(window=window, min_periods=1).mean()


def daily_return(wide):
    return wide.pct_change() * 100


def rolling_volatility(wide, window=20):
    return daily_return(wide).rolling(window=window, min_periods=5).std()


def monthly_return(wide):
    monthly = wide.resample("ME").last()
    return monthly.pct_change() * 100


def decompose(wide, column, period=21):
    series = wide[column].asfreq("B").interpolate()
    result = seasonal_decompose(series, model="additive", period=period, extrapolate_trend="period")
    return result


def naive_forecast(wide, column, horizon=10, window=20):
    series = wide[column].dropna()
    recent = series.iloc[-window:]
    x = np.arange(len(recent))
    slope, intercept = np.polyfit(x, recent.values, 1)
    future_x = np.arange(len(recent), len(recent) + horizon)
    forecast_values = slope * future_x + intercept
    last_date = series.index[-1]
    future_dates = pd.bdate_range(last_date + pd.Timedelta(days=1), periods=horizon)
    return pd.Series(forecast_values, index=future_dates), slope