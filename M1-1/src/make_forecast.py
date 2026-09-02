"""analyze.py의 naive_forecast()를 이용해 USD/JPY/CNY 10일 예측 그래프(PNG)를 생성한다.

베이스라인 예측: 최근 20일 이동평균의 기울기를 향후 10일 선형 연장.
정확도 목적이 아니라 "추세가 유지된다면"이라는 가정을 보여주는 참고용 베이스라인.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from analyze import load_long_df, to_wide, clean, naive_forecast

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 프로젝트 루트
DB_PATH = os.path.join(BASE_DIR, "data", "exchange_rates.db")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.family"] = "DejaVu Sans"

CURRENCIES = ["USD", "JPY", "CNY"]
COLORS = {"USD": "#2563eb", "JPY": "#dc2626", "CNY": "#16a34a"}
CURRENCY_LABELS = {"USD": "USD/KRW", "JPY": "JPY/KRW (100 yen)", "CNY": "CNY/KRW"}

HORIZON = 10   # 예측 기간(영업일)
WINDOW = 20    # 기울기 계산에 사용할 최근 구간
LOOKBACK = 90  # 그래프에 보여줄 과거 구간(영업일)

# ---------- 데이터 로드 & 정제 ----------
long_df = load_long_df(DB_PATH)
wide = to_wide(long_df)
cleaned, report = clean(wide)
print("정제 리포트:", report)

# ================= PNG: 통화별 naive_forecast (3단) =================
fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=False)
fig.suptitle(
    f"Naive Forecast: {HORIZON}-Day Linear Extrapolation of {WINDOW}-Day Trend",
    fontsize=15, fontweight="bold",
)

for ax, cur in zip(axes, CURRENCIES):
    forecast, slope = naive_forecast(cleaned, cur, horizon=HORIZON, window=WINDOW)

    recent = cleaned[cur].dropna().iloc[-LOOKBACK:]
    ax.plot(recent.index, recent.values, color=COLORS[cur], linewidth=1.5, label=f"{cur} (recent {LOOKBACK}D)")

    # 마지막 실측치 -> 예측 시작점을 이어서 끊김 없이 표시
    connect_x = [recent.index[-1], forecast.index[0]]
    connect_y = [recent.values[-1], forecast.values[0]]
    ax.plot(connect_x, connect_y, color=COLORS[cur], linewidth=1.5, linestyle="--", alpha=0.6)
    ax.plot(forecast.index, forecast.values, color=COLORS[cur], linewidth=2.2, linestyle="--",
             marker="o", markersize=3, label=f"{cur} forecast ({HORIZON}D)")

    ax.axvline(recent.index[-1], color="gray", linewidth=0.8, linestyle=":")
    ax.set_title(f"{CURRENCY_LABELS[cur]}  (slope={slope:+.3f}/day)", fontsize=11, loc="left")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylabel("Rate (KRW)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))

axes[-1].set_xlabel("Date")
fig.tight_layout(rect=[0, 0, 1, 0.95])
out_path = os.path.join(OUT_DIR, "06_naive_forecast.png")
fig.savefig(out_path, dpi=150)
plt.close(fig)
print(f"saved: {out_path}")
