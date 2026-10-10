from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from auth.models import User
from auth.utils import get_current_user
from core.rag_system import RAGSystem
from eval.evaluator import run_evaluation
from dependencies import get_rag_system

router = APIRouter(prefix="/eval", tags=["eval"])


def _sse(generator):
    for line in generator:
        yield f"data: {line}\n\n"


@router.post("/run")
def run_eval(
    current_user: User = Depends(get_current_user),
    rag_system: RAGSystem = Depends(get_rag_system),
):
    return StreamingResponse(
        _sse(run_evaluation(rag_system)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
