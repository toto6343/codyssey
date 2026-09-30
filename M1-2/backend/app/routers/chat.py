from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, summary="AI 대화 (데이터 요약 컨텍스트 주입 + 자동 저장)")
def chat(body: ChatRequest):
    return chat_service.run_chat(body.message, body.conversation_id)
