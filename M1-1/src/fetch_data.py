"""
한국수출입은행 Open API(환율) 데이터 수집 스크립트
=================================================

API 문서: https://www.koreaexim.go.kr/ir/HPHKIR019M01
엔드포인트: https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON
파라미터:
    authkey    : 발급받은 인증키
    searchdate : YYYYMMDD (해당 '영업일' 하루치 고시환율만 반환)
    data       : AP01 (환율 고시)

이 API는 하루 1건 조회 형태라서, 기간 데이터를 만들려면 영업일마다
반복 호출을 해야 합니다. 그러다 보니
  1) 호출 횟수가 금방 하루 제한(무료 플랜 기준 1000회/일 등)에 걸릴 수 있고,
  2) 주말/공휴일에는 데이터가 없어 빈 응답이 옵니다.
그래서 이미 수집한 날짜는 SQLite에 캐싱해두고 재실행 시 건너뜁니다.

[수정 사항]
- python-dotenv를 이용해 스크립트가 있는 디렉터리의 .env 파일을 자동으로
  읽어오도록 변경했습니다. (KOREAEXIM_API_KEY=... 형태로 저장된 값을 인식)
- .env / python-dotenv가 없어도 기존처럼 실제 환경변수(export 등)로
  설정된 값이 있으면 그대로 동작합니다.
- [버그 수정 2] result 코드를 확인하지 않고 cur_unit/deal_bas_r만 있으면
  그대로 저장하던 문제를 고쳤습니다. 공식 문서 기준 result 코드는
  1=정상, 2=DATA코드 오류, 3=인증키 오류/만료, 4=일일 요청 한도 초과입니다.
  result != 1인 레코드를 그대로 저장하면서 실제 DB에 하루짜리 스파이크성
  이상값(예: 특정일 USD/JPY/CNY가 동시에 10~28% 튀었다가 다음날 원복)이
  다수 발생한 것을 확인해 반영했습니다.
- [추가] 저장 직전 전일 대비 변화율이 비정상적으로 크면(기본 5% 초과)
  경고만 출력하는 sanity check를 추가했습니다. 이 API가 정상 응답 안에
  드물게 이상한 값을 실어 보내는 경우까지는 result 코드만으로 못 걸러낼
  수 있어, 최소한 로그로 남겨 나중에 눈으로 확인할 수 있게 했습니다.
  자동으로 값을 버리지는 않습니다(정상적인 급변동일 수도 있으므로).
- [버그 수정 3 - SSL, 최종] `CERTIFICATE_VERIFY_FAILED: unable to get local
  issuer certificate` 오류의 실제 원인을 확인했습니다. 인증서 자체는
  DigiCert(Thawte TLS RSA CA G1)가 발급한 정상적인 국제 공인 인증서였지만,
  oapi.koreaexim.go.kr 서버가 TLS 핸드셰이크 시 중간 인증서(intermediate CA)를
  함께 보내지 않는 설정 오류가 있었습니다. 브라우저는 인증서의 AIA
  (Authority Information Access) 필드를 보고 누락된 중간 인증서를 자동으로
  가져와 체인을 완성하지만(AIA chasing), Python 표준 ssl/urllib은 이 동작을
  하지 않아서 서버가 보낸 불완전한 체인만으로 검증에 실패합니다.
  (처음 시도했던 certifi CA 번들 명시 지정은 루트 인증서 신뢰 목록 문제를
  가정한 것이라 이 경우엔 효과가 없었습니다.)
  이를 해결하기 위해 `truststore` 패키지로 OS 네이티브 인증서 검증 엔진을
  사용하도록 변경했습니다. Windows는 CryptoAPI, macOS는 Keychain을 통해
  브라우저와 동일하게 AIA chasing을 지원하므로 이 문제가 해결됩니다.
  사용 전 설치 필요: `pip install truststore`
"""

import argparse
import datetime as dt
import json
import os
import socket
import sqlite3
import ssl
import time
import urllib.request
import urllib.error

# [버그 수정 3 - SSL, 최종] truststore로 OS 네이티브 인증서 검증(Windows
# CryptoAPI / macOS Keychain)을 사용하도록 전역 패치한다. 이 API들은
# 브라우저처럼 누락된 중간 인증서를 자동으로 가져오는 AIA chasing을
# 지원하기 때문에, 서버가 중간 인증서를 빠뜨리고 보내는 경우에도 검증에
# 성공한다. import ssl 직후, 다른 곳에서 SSLContext를 만들기 전에
# 호출해야 한다. 설치: pip install truststore
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    print(
        "  [warn] truststore 패키지가 없어 SSL 검증 시 기본 urllib 방식을 사용합니다.\n"
        "         'unable to get local issuer certificate' 오류가 발생하면\n"
        "         'pip install truststore' 설치 후 다시 실행해보세요."
    )

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

API_URL = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
DB_PATH = os.path.join(BASE_DIR, "..", "data", "exchange_rates.db")

# truststore 적용 후에는 이 기본 컨텍스트가 곧 OS 네이티브 검증 컨텍스트가 된다.
SSL_CONTEXT = ssl.create_default_context()

# 리포트에서 다루는 3개 통화 (수출입은행 표기 기준 cur_unit)
TARGET_CURRENCIES = {
    "USD": "USD",   # 미국 달러
    "JPY(100)": "JPY",  # 일본 옌 100엔 기준으로 고시됨 -> 100으로 나눠 1엔 기준으로 환산
    "CNH": "CNY",   # 위안화(역외) 고시 코드. 위안화는 은행마다 CNH로 고시되는 경우가 많음
}

# result 코드 의미 (한국수출입은행 Open API 공식 문서 기준)
RESULT_CODE_MEANING = {
    "1": "정상",
    "2": "DATA코드 오류(요청 데이터 코드 오류)",
    "3": "인증코드 오류(인증키 만료/오류)",
    "4": "일일제한횟수 마감(요청 횟수 초과)",
}

# 저장 직전 sanity check용: 전일 대비 이 비율(%)을 초과하면 경고만 출력
SANITY_PCT_THRESHOLD = 5.0

# [버그 수정 3 - SSL] 인증서 문제 외의 네트워크 오류(방화벽, 타임아웃 등)를
# 구분해서 안내하기 위한 재시도 횟수
MAX_RETRIES = 2


def load_env_file() -> None:
    """스크립트 디렉터리의 .env 파일을 읽어 os.environ에 반영한다.

    python-dotenv가 설치돼 있으면 그것을 사용하고, 없으면 간단한
    자체 파서로 KEY=VALUE 형식만 최소한으로 지원한다(fallback).
    이미 설정된 실제 환경변수는 덮어쓰지 않는다.
    """
    if not os.path.exists(ENV_PATH):
        return

    if load_dotenv is not None:
        # override=False: 이미 셸 등에서 export된 값이 있으면 그것을 우선시함
        load_dotenv(dotenv_path=ENV_PATH, override=False)
        return

    # python-dotenv가 없는 환경을 위한 아주 단순한 fallback 파서
    print(
        f"  [info] python-dotenv가 설치되어 있지 않아 자체 파서로 {ENV_PATH} 를 읽습니다. "
        f"(pip install python-dotenv 권장)"
    )
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


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


EXPECTED_CURRENCY_COUNT = len(set(TARGET_CURRENCIES.values()))  # 3 (USD, JPY, CNY)


def already_cached(conn: sqlite3.Connection, date_str: str) -> bool:
    """해당 날짜에 필요한 통화(3개)가 '전부' 저장되어 있어야 캐시된 것으로 본다.

    [버그 수정] 예전에는 count > 0 이면(즉 1건만 있어도) 캐시된 것으로 봐서,
    CNH 고시가 아직 발표 전이라 저장이 실패한 날(USD/JPY만 저장됨)도
    영원히 재조회가 안 되는 문제가 있었다. 이제는 3개 통화가 다 있어야
    캐시된 것으로 간주하고, 아니면 다시 API를 호출해 누락분을 채운다.
    """
    cur = conn.execute(
        "SELECT COUNT(*) FROM exchange_rates WHERE date = ?", (date_str,)
    )
    (count,) = cur.fetchone()
    return count >= EXPECTED_CURRENCY_COUNT


def fetch_one_day(api_key: str, date_str: str) -> list[dict]:
    """searchdate=YYYYMMDD 하루치 고시환율을 가져온다. 주말/공휴일은 빈 리스트.

    [버그 수정 3 - SSL] urlopen 호출 시 certifi CA 번들을 사용하는
    SSL_CONTEXT를 명시적으로 전달한다. 인증서 오류(SSLCertVerificationError)와
    그 외 네트워크 오류(타임아웃, 연결 거부 등)를 구분해서 메시지를 다르게
    출력하고, 후자는 짧게 재시도한다(방화벽/사내망의 일시적 문제 대비).
    """
    params = f"?authkey={api_key}&searchdate={date_str}&data=AP01"
    req = urllib.request.Request(API_URL + params)

    for attempt in range(1, MAX_RETRIES + 2):  # 최초 시도 + 재시도
        try:
            with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except (urllib.error.URLError, socket.timeout) as e:
            # [버그 수정 3-1] urllib은 SSL 인증서 오류를 ssl.SSLCertVerificationError로
            # 바로 던지지 않고 urllib.error.URLError로 한 번 감싸서 던진다.
            # e.reason에 원래 예외가 들어있으므로 이를 확인해서 인증서 문제인지
            # 판별해야 한다. 이 확인 없이는 인증서 오류도 매번 무의미하게
            # 재시도만 반복하게 된다(같은 오류가 절대 재시도로 해결되지 않는데도).
            is_cert_error = isinstance(
                getattr(e, "reason", None), ssl.SSLCertVerificationError
            ) or isinstance(e, ssl.SSLCertVerificationError)

            if is_cert_error:
                print(
                    f"  [error] {date_str} SSL 인증서 검증 실패: {e}\n"
                    f"         certifi 경로 확인: python -c \"import certifi; print(certifi.where())\"\n"
                    f"         회사망/VPN이라면 IT팀의 루트 CA 인증서를 위 파일에 추가해야 할 수 있습니다.\n"
                    f"         (인증서 문제는 재시도해도 해결되지 않으므로 이 날짜는 즉시 건너뜁니다)"
                )
                return []

            if attempt <= MAX_RETRIES:
                print(f"  [warn] {date_str} 요청 실패({attempt}/{MAX_RETRIES + 1}차 시도): {e} - 재시도")
                time.sleep(1.0)
                continue
            print(f"  [warn] {date_str} 요청 최종 실패: {e}")
            return []
    return []


def business_days(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        if d.weekday() < 5:  # 월~금만 (공휴일은 API가 빈 배열로 알아서 걸러줌)
            yield d
        d += dt.timedelta(days=1)


def get_last_rate(conn: sqlite3.Connection, currency: str, before_date: str) -> float | None:
    """sanity check용: 해당 통화의 가장 최근(before_date 이전) 저장값을 가져온다."""
    cur = conn.execute(
        "SELECT rate FROM exchange_rates WHERE currency = ? AND date < ? "
        "ORDER BY date DESC LIMIT 1",
        (currency, before_date),
    )
    row = cur.fetchone()
    return row[0] if row else None


def save_day(conn: sqlite3.Connection, date_str: str, records: list[dict]) -> int:
    saved = 0
    fetched_at = dt.datetime.now().isoformat(timespec="seconds")
    for rec in records:
        # [버그 수정 2] result 코드 확인 - 정상(1)이 아니면 저장하지 않는다.
        result_code = str(rec.get("result", ""))
        if result_code != "1":
            meaning = RESULT_CODE_MEANING.get(result_code, "알 수 없는 코드")
            print(
                f"  [warn] {date_str} {rec.get('cur_unit')} result={result_code}"
                f"({meaning}) - 비정상 응답이라 건너뜀"
            )
            continue

        cur_unit = rec.get("cur_unit")
        if cur_unit not in TARGET_CURRENCIES:
            continue
        try:
            rate = float(rec["deal_bas_r"].replace(",", ""))
        except (KeyError, ValueError):
            print(
                f"  [warn] {date_str} {cur_unit} 값 파싱 실패 "
                f"(deal_bas_r={rec.get('deal_bas_r')!r}, result={rec.get('result')}) - 건너뜀"
            )
            continue
        if cur_unit == "JPY(100)":
            rate = rate / 100.0  # 100엔 -> 1엔 기준으로 정규화
        currency = TARGET_CURRENCIES[cur_unit]

        # sanity check: 전일 대비 급변이면 경고만 출력(저장은 그대로 진행)
        last_rate = get_last_rate(conn, currency, date_str)
        if last_rate:
            pct_change = abs(rate - last_rate) / last_rate * 100
            if pct_change > SANITY_PCT_THRESHOLD:
                print(
                    f"  [warn] {date_str} {currency} 급변 감지: "
                    f"{last_rate} -> {rate} ({pct_change:.1f}%) - 값은 저장하되 확인 필요"
                )

        conn.execute(
            "INSERT OR REPLACE INTO exchange_rates (date, currency, rate, fetched_at) "
            "VALUES (?, ?, ?, ?)",
            (date_str, currency, rate, fetched_at),
        )
        saved += 1
    conn.commit()
    return saved


def main():
    load_env_file()  # .env 파일이 있으면 여기서 os.environ에 반영됨

    parser = argparse.ArgumentParser(description="수출입은행 환율 API 수집 + SQLite 캐싱")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--sleep", type=float, default=0.3, help="호출 간 대기(초)")
    args = parser.parse_args()

    api_key = os.environ.get("KOREAEXIM_API_KEY")
    if not api_key:
        raise SystemExit(
            "KOREAEXIM_API_KEY 를 찾을 수 없습니다.\n"
            f"  1) {ENV_PATH} 파일에 KOREAEXIM_API_KEY=발급받은키 형태로 넣거나\n"
            "  2) export KOREAEXIM_API_KEY=발급받은키 로 환경변수를 직접 설정하세요.\n"
            "발급: https://www.koreaexim.go.kr/ir/HPHKIR019M01"
        )

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_calls, total_cached, total_saved = 0, 0, 0
    for d in business_days(start, end):
        date_str = d.strftime("%Y%m%d")
        if already_cached(conn, date_str):
            total_cached += 1
            continue
        records = fetch_one_day(api_key, date_str)
        total_calls += 1
        saved = save_day(conn, date_str, records)
        total_saved += saved
        print(f"{date_str}: {saved}건 저장 (신규 API 호출)")
        time.sleep(args.sleep)

    print(
        f"\n완료: 신규 API 호출 {total_calls}회, 캐시 적중(스킵) {total_cached}일, "
        f"저장된 레코드 {total_saved}건 -> {DB_PATH}"
    )
    conn.close()


if __name__ == "__main__":
    main()