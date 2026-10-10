from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth.models import User
from auth.utils import get_current_user
from core.chat_interface import ChatInterface
from core.rag_system import RAGSystem
from dependencies import get_rag_system

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


def _sse(generator):
    """Wrap each JSON line as a proper SSE data frame."""
    for line in generator:
        yield f"data: {line}\n\n"


@router.post("/stream")
def chat_stream(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    rag_system: RAGSystem = Depends(get_rag_system),
):
    chat_interface = ChatInterface(rag_system)
    return StreamingResponse(
        _sse(chat_interface.stream(body.message)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/clear")
def clear_chat(
    current_user: User = Depends(get_current_user),
    rag_system: RAGSystem = Depends(get_rag_system),
):
    ChatInterface(rag_system).clear_session()
    return {"message": "Chat session cleared"}
