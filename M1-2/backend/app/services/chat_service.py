import logging

from openai import OpenAI, OpenAIError

from app.config import settings
from app.services import conversation_service, data_service
from app.services.errors import LLMError, NoDataError
import json
from app.services.tools import TOOLS, safe_execute

MAX_TOOL_ROUNDS = 3  # 도구 호출 반복 상한 (무한 루프/과금 방지)

logger = logging.getLogger(__name__)
_client: OpenAI | None = None

SYSTEM_TEMPLATE = """당신은 한국 영화 주말 박스오피스 데이터 분석 비서입니다.

[데이터 요약]
- 기간: {period} (금~일 주말 기준, 총 {count}개 주말)
- 지표 정의: 각 주말 박스오피스 상위 10편의 관객수 합계
- 주말 평균: {average}
- 최고: {max_date} {max} (메모: {max_memo})
- 최저: {min_date} {min} (메모: {min_memo})
- 가장 최근 주말: {latest_date} {latest_value} (메모: {latest_memo})
- 최근 트렌드: {trend}
- 전년 동기 대비: {yoy}
- 관객수 TOP 5 주말:
{top5}

규칙:
- 기본은 위 요약을 근거로 답하세요.
- 요약으로 부족한 질문(월별 통계, 중앙값, 표준편차, 이동평균, 직전 주 대비 증감, 이전 대화 조회 등)은 도구를 호출해 확인하세요. 도구를 호출할 때는 reason에 이유를 적으세요.
- 요약과 도구 결과 어디에도 없는 내용(특정 영화의 흥행 원인 등)은 추측하지 말고 "제공된 데이터로는 알 수 없어요"라고 답하세요.
- 수치는 '만 명' 단위로 쉽게 풀어 쓰세요. (도구 결과의 관객수는 '명' 단위 원본이에요)
- 친근한 말투(~요)로 3~4문장 이내로 답하세요."""


def fmt_audience(n: int) -> str:
    return f"{n / 10000:,.0f}만 명"


def build_system_prompt(s: dict) -> str:
    """요약(dict)을 시스템 프롬프트에 주입한다 = 컨텍스트 주입."""
    m = s["metrics"]
    top5 = "\n".join(
        f"  {i}. {p['date']} {fmt_audience(p['value'])} ({p['memo']})"
        for i, p in enumerate(s["top5"], 1)
    )
    return SYSTEM_TEMPLATE.format(
        period=s["period"],
        count=s["count"],
        average=fmt_audience(m["average"]),
        max=fmt_audience(m["max"]),
        max_date=m["max_date"],
        max_memo=m["max_memo"],
        min=fmt_audience(m["min"]),
        min_date=m["min_date"],
        min_memo=m["min_memo"],
        latest_date=s["latest"]["date"],
        latest_value=fmt_audience(s["latest"]["value"]),
        latest_memo=s["latest"]["memo"],
        trend=s["trend"],
        yoy=s["yoy"] or "비교할 작년 데이터가 없음",
        top5=top5,
    )


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,  # 비어 있으면 기본 OpenAI 주소
            timeout=30,
        )
    return _client


def call_llm(messages: list[dict]) -> str:
    try:
        # 참고: 일부 최신 모델은 max_tokens 대신 max_completion_tokens를 요구한다.
        res = _get_client().chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=settings.chat_max_tokens,
            temperature=0.3,
        )
        return (res.choices[0].message.content or "").strip()
    except OpenAIError as e:
        logger.exception("OpenAI 호출 실패")
        raise LLMError(str(e)) from e
    
def call_llm_with_tools(messages: list[dict]) -> tuple[str, list[dict]]:
    msgs = list(messages)
    tool_log: list[dict] = []
    try:
        client = _get_client()
        for _ in range(MAX_TOOL_ROUNDS):
            res = client.chat.completions.create(
                model=settings.openai_model,
                messages=msgs,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=settings.chat_max_tokens,
                temperature=0.3,
            )
            m = res.choices[0].message
            if not m.tool_calls:
                return (m.content or "").strip(), tool_log

            msgs.append({
                "role": "assistant",
                "content": m.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in m.tool_calls
                ],
            })
            for tc in m.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = safe_execute(tc.function.name, args)
                tool_log.append({
                    "tool": tc.function.name,
                    "reason": args.get("reason", ""),
                    "args": {k: v for k, v in args.items() if k != "reason"},
                })
                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        # 상한에 도달하면 도구 없이 마무리 답변을 받는다
        res = client.chat.completions.create(
            model=settings.openai_model, messages=msgs,
            max_tokens=settings.chat_max_tokens, temperature=0.3,
        )
        return (res.choices[0].message.content or "").strip(), tool_log
    except OpenAIError as e:
        logger.exception("OpenAI 호출 실패")
        raise LLMError(str(e)) from e


def run_chat(message: str, conversation_id: str | None) -> dict:
    # 1) 데이터 요약 조회 (HTTP 재호출 없이 같은 서비스 함수를 직접 사용)
    summary = data_service.get_summary()
    if summary is None:
        raise NoDataError("저장된 데이터가 없어요. 먼저 데이터를 추가해 주세요.")

    # 2) 이어 말하기면 이전 대화 로드 (프롬프트에는 최근 N개만)
    past: list[dict] = []
    if conversation_id:
        past = conversation_service.get(conversation_id)["messages"]
    recent = [{"role": m["role"], "content": m["content"]} for m in past[-settings.chat_max_history :]]

    # 3) 요약을 시스템 프롬프트에 삽입 + GPT 호출
    prompt = [
        {"role": "system", "content": build_system_prompt(summary)},
        *recent,
        {"role": "user", "content": message},
    ]
    reply, tool_calls = call_llm_with_tools(prompt)

    # 4) 자동 저장
    full = [
        *({"role": m["role"], "content": m["content"]} for m in past),
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    if conversation_id:
        conversation_service.replace_messages(conversation_id, full)
    else:
        conversation_id = conversation_service.create(full)["id"]

    return {"reply": reply, "conversation_id": conversation_id, "tool_calls": tool_calls}