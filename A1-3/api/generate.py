# api/generate.py
#
# Vercel Python Serverless Function.
# 프론트에서 POST { goal, duration } 을 받아 OpenAI API로 홈트레이닝 루틴을 생성해 반환한다.
#
# 표준 라이브러리(urllib)만 사용하므로 requirements.txt에 별도 패키지가 필요 없다.

from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone
import json
import os
import urllib.request
import urllib.error

OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TIMEOUT_SEC = 20
WEBHOOK_TIMEOUT_SEC = 5  # 로깅용 웹훅은 응답 지연이 사용자 경험을 막지 않도록 짧게 설정


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length else b""

        try:
            data = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "요청 형식이 올바르지 않습니다."})
            return

        goal = (data.get("goal") or "").strip()
        duration = (data.get("duration") or "").strip()

        # 실패 처리: 빈 입력(필수값 누락)
        if not goal or not duration:
            self._send_json(400, {"error": "운동 목표와 시간을 모두 선택해주세요."})
            return

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self._send_json(500, {"error": "서버에 OPENAI_API_KEY가 설정되지 않았습니다."})
            return

        try:
            routine_text = self._generate_routine(api_key, goal, duration)
            self._send_json(200, {"routine": routine_text})
            # 보너스: 운영 자동화 — 생성된 루틴을 노코드 자동화 웹훅(예: Make.com)으로 로깅.
            # 응답을 이미 보낸 뒤 best-effort로 시도하며, 실패해도 사용자 응답에는 영향 없음.
            self._log_to_webhook(goal, duration, routine_text)
        except TimeoutError:
            self._send_json(504, {"error": "응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요."})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")[:300]
            self._send_json(502, {"error": f"AI API 오류가 발생했습니다 (HTTP {e.code})."})
            print(f"[OpenAI HTTPError] {e.code}: {detail}")
        except Exception as e:
            self._send_json(502, {"error": "루틴 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."})
            print(f"[generate error] {type(e).__name__}: {e}")

    def _generate_routine(self, api_key: str, goal: str, duration: str) -> str:
        prompt = f"""당신은 홈트레이닝 코치입니다.
운동 목표: {goal}
가능한 시간: {duration}분

위 조건에 맞는 홈트레이닝 루틴을 아래 형식에 맞춰 순수 텍스트로만 작성하세요.
설명, 인사말, 코드펜스 없이 번호가 붙은 목록만 출력하세요.

형식 예시:
1. 운동 이름 - 세트/횟수 또는 시간
2. 운동 이름 - 세트/횟수 또는 시간

- 시간 조건에 맞는 현실적인 개수(4~8개)의 운동으로 구성하세요.
- 웜업 1개, 본운동, 마무리 스트레칭 1개를 포함하는 흐름으로 구성하세요.
"""

        payload = json.dumps({
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=OPENAI_TIMEOUT_SEC) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        return result["choices"][0]["message"]["content"].strip()

    def _log_to_webhook(self, goal: str, duration: str, routine_text: str) -> None:
        """생성된 루틴을 외부 노코드 자동화(WEBHOOK_URL)로 전송해 기록/알림 흐름을 만든다.
        WEBHOOK_URL 환경변수가 설정되지 않았으면 조용히 건너뛴다(선택 기능이므로 배포에 필수 아님).
        실패해도 사용자에게 보여지는 루틴 생성 응답에는 영향을 주지 않는다."""
        webhook_url = os.environ.get("WEBHOOK_URL")
        if not webhook_url:
            return

        payload = json.dumps({
            "goal": goal,
            "duration_min": duration,
            "routine": routine_text,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }).encode("utf-8")

        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            urllib.request.urlopen(req, timeout=WEBHOOK_TIMEOUT_SEC)
        except Exception as e:
            # 로깅 실패는 서비스 핵심 기능(루틴 생성)을 막지 않는다. 서버 로그에만 남긴다.
            print(f"[webhook log failed] {type(e).__name__}: {e}")

    def _send_json(self, status: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)