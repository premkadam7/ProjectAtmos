from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from typing import Optional, AsyncGenerator
import uuid
from sse_starlette.sse import EventSourceResponse

from services.chatbot import AtmosChatbotService

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    language: str = Field(default="en")
    conversation_id: Optional[str] = None
    stream: bool = Field(default=False)


@router.post("")
async def chat(request: Request, chat_request: ChatRequest):
    conv_id = chat_request.conversation_id or f"conv_{uuid.uuid4().hex[:8]}"

    # Check if developer requested to force real RAG in testing
    force_rag = request.headers.get("x-force-rag", "").lower() == "true"

    # Check Accept header or stream parameter
    accept_header = request.headers.get("accept", "")
    is_stream = "text/event-stream" in accept_header or chat_request.stream

    if is_stream:
        async def event_generator() -> AsyncGenerator[dict, None]:
            async for chunk in AtmosChatbotService.chat_stream(
                message=chat_request.message,
                language=chat_request.language,
                conversation_id=conv_id,
                force_rag=force_rag
            ):
                yield {"data": chunk}

        return EventSourceResponse(event_generator())
    else:
        response_data = await AtmosChatbotService.chat_non_stream(
            message=chat_request.message,
            language=chat_request.language,
            conversation_id=conv_id,
            force_rag=force_rag
        )
        return response_data
