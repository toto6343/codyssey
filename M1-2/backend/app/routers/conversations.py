from fastapi import APIRouter, Response

from app.schemas import ConversationCreate, ConversationListItem, ConversationOut
from app.services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=201, summary="대화 저장")
def create_conversation(body: ConversationCreate):
    return conversation_service.create([m.model_dump() for m in body.messages], body.title)


@router.get("", response_model=list[ConversationListItem], summary="대화 목록 조회 (messages 미포함)")
def list_conversations():
    return conversation_service.list_all()


@router.get("/{conv_id}", response_model=ConversationOut, summary="특정 대화 전체 조회")
def get_conversation(conv_id: str):
    return conversation_service.get(conv_id)


@router.delete("/{conv_id}", status_code=204, summary="대화 삭제")
def delete_conversation(conv_id: str):
    conversation_service.delete(conv_id)
    return Response(status_code=204)
