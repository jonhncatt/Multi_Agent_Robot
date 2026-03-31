from __future__ import annotations

from fastapi import APIRouter

from app.models import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    from app.main import _process_chat_request_minimal

    return _process_chat_request_minimal(req)

