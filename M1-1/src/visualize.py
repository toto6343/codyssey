"""analyze.py의 함수들을 사용해 images/ 폴더에 5개 차트를 생성한다.

사용법:
    python visualize.py <db_path> [output_dir]

예:
    python visualize.py exchange_rates.db images

필요 이미지:
    01_price_trend.png            - 통화별 원본 환율 + 이동평균
    02_volatility.png             - 통화별 롤링 변동성(20일)
    03_monthly_return_heatmap.png - 통화 x 월 수익률 히트맵
    04_decomposition_usd.png      - USD 계절분해 (관측/추세/계절/잔차)
    05_naive_forecast_usd.png     - USD 베이스라인(선형 추세) 예측
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")  # 파일 저장 전용 (화면 표시 없음)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns

from analyze import (
    load_long_df,
    to_wide,
    clean,
    moving_average,
    rolling_volatility,
    monthly_return,
    decompose,
    naive_forecast,
)

plt.rcParams["axes.unicode_minus"] = False
sns.set_style("whitegrid")

# 한글 폰트가 있으면 사용 (없으면 기본 폰트로 표시, 한글은 깨질 수 있음)
for font_name in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"):
    if font_name in {f.name for f in matplotlib.font_manager.fontManager.ttflist}:
        plt.rcParams["font.family"] = font_name
        break


def _save(fig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"저장 완료: {path}")


def plot_price_trend(wide: pd.DataFrame, out_path: str, ma_window: int = 20):
    """01_price_trend.png: 통화별 원본 환율 + 이동평균선."""
    ma = moving_average(wide, window=ma_window)
    cols = wide.columns
    fig, axes = plt.subplots(len(cols), 1, figsize=(12, 3.2 * len(cols)), sharex=True)
    if len(cols) == 1:
        axes = [axes]

    for ax, col in zip(axes, cols):
        ax.plot(wide.index, wide[col], label=f"{col} 원값", color="tab:blue", linewidth=1, alpha=0.6)
        ax.plot(ma.index, ma[col], label=f"{col} {ma_window}일 이동평균", color="tab:red", linewidth=1.6)
        ax.set_title(f"{col} 환율 추이")
        ax.legend(loc="upper left")
        ax.set_ylabel("환율")

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    fig.suptitle("통화별 환율 추이 (원값 vs 이동평균)", y=1.02, fontsize=14)
    fig.tight_layout()
    _save(fig, out_path)


def plot_volatility(wide: pd.DataFrame, out_path: str, window: int = 20):
    """02_volatility.png: 통화별 롤링 변동성(수익률 표준편차) 한 그래프에 겹쳐 그림."""
    vol = rolling_volatility(wide, window=window)
    fig, ax = plt.subplots(figsize=(12, 5))
    for col in vol.columns:
        ax.plot(vol.index, vol[col], label=col, linewidth=1.3)

    ax.set_title(f"통화별 롤링 변동성 ({window}일, 일일 수익률 표준편차 %)")
    ax.set_ylabel("변동성 (%)")
    ax.legend(loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, out_path)


def plot_monthly_return_heatmap(wide: pd.DataFrame, out_path: str):
    """03_monthly_return_heatmap.png: 통화(행) x 월(열) 수익률 히트맵."""
    mret = monthly_return(wide).dropna(how="all")
    mret.index = mret.index.strftime("%Y-%m")
    data = mret.T  # 행: 통화, 열: 월

    fig, ax = plt.subplots(figsize=(max(10, 0.5 * data.shape[1]), 1.2 * data.shape[0] + 2))
    sns.heatmap(
        data,
        annot=True,
        fmt=".1f",
        cmap="RdBu_r",
        center=0,
        cbar_kws={"label": "월간 수익률 (%)"},
        ax=ax,
        linewidths=0.5,
        linecolor="white",
    )
    ax.set_title("통화별 월간 수익률 히트맵")
    ax.set_xlabel("월")
    ax.set_ylabel("통화")
    fig.tight_layout()
    _save(fig, out_path)


def plot_decomposition(wide: pd.DataFrame, out_path: str, column: str = "USD", period: int = 21):
    """04_decomposition_usd.png: 계절분해 결과(관측/추세/계절성/잔차) 4단 플롯."""
    result = decompose(wide, column=column, period=period)

    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
    components = [
        (result.observed, "관측값 (Observed)", "tab:blue"),
        (result.trend, "추세 (Trend)", "tab:orange"),
        (result.seasonal, "계절성 (Seasonal)", "tab:green"),
        (result.resid, "잔차 (Residual)", "tab:red"),
    ]
    for ax, (series, title, color) in zip(axes, components):
        ax.plot(series.index, series.values, color=color, linewidth=1.2)
        ax.set_title(title, loc="left", fontsize=11)
        ax.axhline(0, color="grey", linewidth=0.6) if "잔차" in title or "계절" in title else None

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    fig.suptitle(f"{column} 환율 계절분해 (period={period}, additive)", y=1.01, fontsize=14)
    fig.tight_layout()
    _save(fig, out_path)


def plot_naive_forecast(wide: pd.DataFrame, out_path: str, column: str = "USD",
                         horizon: int = 10, window: int = 20, history_days: int = 90):
    """05_naive_forecast_usd.png: 최근 구간 실측치 + 선형 추세 베이스라인 예측."""
    forecast, slope = naive_forecast(wide, column=column, horizon=horizon, window=window)
    history = wide[column].dropna().iloc[-history_days:]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(history.index, history.values, label="실측값", color="tab:blue", linewidth=1.4)
    ax.plot(forecast.index, forecast.values, label=f"베이스라인 예측 ({horizon}일)",
            color="tab:red", linestyle="--", marker="o", markersize=3)

    # 예측 시작점을 실측 마지막 값과 이어줌
    ax.plot([history.index[-1], forecast.index[0]],
            [history.values[-1], forecast.values[0]],
            color="tab:red", linestyle="--", linewidth=1)

    ax.axvline(history.index[-1], color="grey", linestyle=":", linewidth=1)
    ax.set_title(f"{column} 베이스라인(선형 추세) 예측 — 최근 {window}일 기울기: {slope:+.4f}/일")
    ax.set_ylabel("환율")
    ax.legend(loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    fig.tight_layout()
    _save(fig, out_path)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # src/ 의 상위 폴더

    # 기본값: 프로젝트 구조(project_root/data/exchange_rates.db, project_root/outputs)를 가정.
    # ai_client로 실행했을 때 보고서가 모이는 outputs/ 폴더와 위치를 맞춘 것.
    # 인자를 주면 그 값이 우선한다 — 구조가 다르면 인자로 덮어쓰면 됨.
    default_db_path = os.path.join(project_root, "data", "exchange_rates.db")
    default_out_dir = os.path.join(project_root, "outputs")

    db_path = sys.argv[1] if len(sys.argv) > 1 else default_db_path
    out_dir = sys.argv[2] if len(sys.argv) > 2 else default_out_dir

    if not os.path.exists(db_path):
        print(f"DB 파일을 찾을 수 없습니다: {db_path}")
        print("사용법: python visualize.py [db_path] [output_dir]")
        sys.exit(1)

    long_df = load_long_df(db_path)
    wide = to_wide(long_df)
    cleaned, report = clean(wide)
    print("클리닝 리포트:", report)

    # USD 컬럼명이 다를 경우를 대비한 방어적 선택
    usd_col = "USD" if "USD" in cleaned.columns else cleaned.columns[0]

    plot_price_trend(cleaned, os.path.join(out_dir, "01_price_trend.png"))
    plot_volatility(cleaned, os.path.join(out_dir, "02_volatility.png"))
    plot_monthly_return_heatmap(cleaned, os.path.join(out_dir, "03_monthly_return_heatmap.png"))
    plot_decomposition(cleaned, os.path.join(out_dir, "04_decomposition_usd.png"), column=usd_col)
    plot_naive_forecast(cleaned, os.path.join(out_dir, "05_naive_forecast_usd.png"), column=usd_col)


if __name__ == "__main__":
    main()