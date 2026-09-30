from firebase_admin import firestore

from app.firebase import get_db
from app.services.errors import NotFoundError

COLLECTION = "conversations"


def _col():
    return get_db().collection(COLLECTION)


def _ts(v):
    return v.isoformat() if v else None


def _to_out(doc_id: str, d: dict) -> dict:
    return {
        "id": doc_id,
        "title": d.get("title", ""),
        "messages": d.get("messages", []),
        "created_at": _ts(d.get("created_at")),
        "updated_at": _ts(d.get("updated_at")),
    }


def create(messages: list[dict], title: str | None = None) -> dict:
    if not title:
        first_user = next((m["content"] for m in messages if m["role"] == "user"), "새 대화")
        title = first_user[:30]
    ref = _col().document()
    ref.set(
        {
            "title": title,
            "messages": messages,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )
    return _to_out(ref.id, ref.get().to_dict())


def list_all(limit: int = 50) -> list[dict]:
    docs = _col().order_by("updated_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
    items = []
    for d in docs:
        o = _to_out(d.id, d.to_dict())
        o["message_count"] = len(o.pop("messages"))  # 목록에는 messages 제외
        items.append(o)
    return items


def get(conv_id: str) -> dict:
    snap = _col().document(conv_id).get()
    if not snap.exists:
        raise NotFoundError("대화를 찾을 수 없어요.")
    return _to_out(snap.id, snap.to_dict())


def replace_messages(conv_id: str, messages: list[dict]) -> None:
    # ArrayUnion은 같은 내용을 중복 제거해 버리므로 전체 배열을 다시 쓴다.
    _col().document(conv_id).update(
        {"messages": messages, "updated_at": firestore.SERVER_TIMESTAMP}
    )


def delete(conv_id: str) -> None:
    ref = _col().document(conv_id)
    if not ref.get().exists:
        raise NotFoundError("대화를 찾을 수 없어요.")
    ref.delete()
