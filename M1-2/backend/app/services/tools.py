from app.services import conversation_service, data_service
from app.services.errors import NoDataError

REASON = {"type": "string", "description": "이 도구를 호출하는 이유를 한 문장으로"}


def _fn(name: str, desc: str, props: dict | None = None, required: list | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {**(props or {}), "reason": REASON},
                "required": [*(required or []), "reason"],
            },
        },
    }


TOOLS = [
    _fn("get_data_summary", "주말 박스오피스의 기간, 개수, 평균/최대/최소, 최근 트렌드, 전년 동기 대비, TOP5를 최신 상태로 조회한다."),
    _fn("get_statistics", "월별 통계(평균/최대/최소), 중앙값, 표준편차, 직전 주 대비 증감률, 4주 이동평균을 조회한다."),
    _fn("list_conversations", "저장된 이전 대화 목록(제목, 수정 시각, 메시지 수)을 조회한다."),
    _fn(
        "get_conversation",
        "특정 대화의 메시지를 조회한다. conversation_id는 list_conversations 결과의 id를 사용한다.",
        {"conversation_id": {"type": "string"}},
        ["conversation_id"],
    ),
]


def execute_tool(name: str, args: dict):
    if name == "get_data_summary":
        return data_service.get_summary()
    if name == "get_statistics":
        return data_service.get_statistics()
    if name == "list_conversations":
        return conversation_service.list_all(limit=10)
    if name == "get_conversation":
        conv = conversation_service.get(args["conversation_id"])
        conv["messages"] = conv["messages"][-10:]  # 토큰 절약: 최근 10개만
        return conv
    return {"error": f"알 수 없는 도구: {name}"}


def safe_execute(name: str, args: dict):
    """도구 실패가 대화 전체를 깨뜨리지 않도록 에러를 결과로 돌려준다."""
    try:
        return execute_tool(name, args)
    except (NoDataError, KeyError) as e:
        return {"error": str(e) or "필수 인자가 없어요."}
    except Exception as e:  # NotFoundError 등 서비스 예외 포함
        return {"error": str(e)}