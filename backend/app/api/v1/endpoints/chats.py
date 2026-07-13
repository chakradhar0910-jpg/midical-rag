"""Chat API endpoints — provider-aware, with streaming support."""
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
import json
import logging

from app.db.session import get_db
from app.models.models import Chat, Message, MessageRole, User
from app.schemas.schemas import (
    ChatCreate, ChatUpdate, ChatResponse, ChatListResponse,
    MessageCreate, MessageResponse, ChatWithMessages,
    MessageReactionRequest, MessageOut,
)
from app.api.v1.deps import get_current_active_user
from app.services.ai.rag_service import rag_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["Chat"])


def _resolve_provider(header_value: Optional[str]) -> str:
    """Return the provider string, falling back to DEFAULT_AI_PROVIDER."""
    v = (header_value or "").strip().lower()
    return v if v in {"ollama", "gemini", "auto"} else settings.DEFAULT_AI_PROVIDER


# ─── CRUD ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=ChatResponse, status_code=201)
async def create_chat(
    data: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new chat session."""
    chat = Chat(user_id=current_user.id, title=data.title or "New Chat")
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


@router.get("", response_model=ChatListResponse)
async def list_chats(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    archived: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List user's chats with pagination."""
    query = select(Chat).where(
        Chat.user_id == current_user.id,
        Chat.is_archived == archived,
    )
    if search:
        query = query.where(Chat.title.ilike(f"%{search}%"))
    query = query.order_by(Chat.is_pinned.desc(), Chat.updated_at.desc())

    count_q = select(func.count()).select_from(query.subquery())
    total   = (await db.execute(count_q)).scalar()
    chats   = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return ChatListResponse(chats=list(chats), total=total, page=page, page_size=page_size)


@router.get("/{chat_id}", response_model=ChatWithMessages)
async def get_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get chat with all messages."""
    result = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id, Chat.user_id == current_user.id)
        .options(selectinload(Chat.messages))
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    data: ChatUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update chat properties."""
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(chat, field, value)
    await db.commit()
    await db.refresh(chat)
    return chat


@router.delete("/{chat_id}", response_model=MessageOut)
async def delete_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a chat and all its messages."""
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    await db.delete(chat)
    await db.commit()
    return {"message": "Chat deleted successfully"}


# ─── Messaging (provider-aware) ───────────────────────────────────────────────

@router.post("/{chat_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    chat_id: str,
    data: MessageCreate,
    x_ai_provider: Optional[str] = Header(
        default=None,
        alias="X-AI-Provider",
        description="AI provider: ollama | gemini | auto",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Send a message and receive an AI response from the selected provider."""
    # Resolve provider
    provider = _resolve_provider(x_ai_provider)
    logger.info("[CHAT] user=%s  provider=%s  chat=%s", current_user.id, provider, chat_id)

    # Verify chat ownership
    result = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id, Chat.user_id == current_user.id)
        .options(selectinload(Chat.messages))
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Save user message
    user_msg = Message(chat_id=chat_id, role=MessageRole.USER, content=data.content)
    db.add(user_msg)
    await db.flush()

    # Generate AI response — strict provider routing
    try:
        ai_result = await rag_service.generate_answer(
            query=data.content,
            provider=provider,
            chat_history=[
                {"role": m.role.value, "content": m.content}
                for m in chat.messages[-10:]
            ],
            user_id=current_user.id,
        )
    except RuntimeError as exc:
        # Strict: return error, never swap provider silently
        provider_label = provider.upper() if provider != "auto" else "ALL PROVIDERS"
        error_detail = (
            f"[ERROR] {provider_label} failed: {exc}"
            if provider != "auto"
            else f"[ERROR] All providers failed: {exc}"
        )
        logger.error("[CHAT ERROR] %s", error_detail)
        raise HTTPException(status_code=502, detail=error_detail)

    # Save AI message
    from datetime import datetime, timezone
    ai_msg = Message(
        chat_id=chat_id,
        role=MessageRole.ASSISTANT,
        content=ai_result["answer"],
        sources=ai_result.get("sources"),
        confidence_score=ai_result.get("confidence_score"),
        tokens_used=ai_result.get("tokens_used"),
        processing_time_ms=ai_result.get("processing_time_ms"),
        model_used=f"{ai_result.get('provider_tag', '')} {ai_result.get('model_used', '')}".strip(),
    )
    db.add(ai_msg)

    chat.message_count = (chat.message_count or 0) + 2
    chat.last_message_at = datetime.now(timezone.utc)
    if chat.title == "New Chat" and not chat.messages:
        chat.title = data.content[:50] + ("..." if len(data.content) > 50 else "")

    await db.commit()
    await db.refresh(ai_msg)
    return ai_msg


@router.post("/{chat_id}/messages/stream")
async def stream_message(
    chat_id: str,
    data: MessageCreate,
    x_ai_provider: Optional[str] = Header(
        default=None,
        alias="X-AI-Provider",
        description="AI provider: ollama | gemini | auto",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Stream AI response via Server-Sent Events."""
    provider = _resolve_provider(x_ai_provider)

    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Chat not found")

    user_msg = Message(chat_id=chat_id, role=MessageRole.USER, content=data.content)
    db.add(user_msg)
    await db.commit()

    async def generate():
        try:
            ai_result = await rag_service.generate_answer(
                query=data.content,
                provider=provider,
                user_id=current_user.id,
            )
            answer = ai_result["answer"]
            # Stream word by word
            for word in answer.split(" "):
                yield f"data: {json.dumps({'type': 'chunk', 'content': word + ' '})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'sources': ai_result.get('sources', []), 'confidence_score': ai_result.get('confidence_score', 0), 'provider_tag': ai_result.get('provider_tag', ''), 'model_used': ai_result.get('model_used', ''), 'processing_time_ms': ai_result.get('processing_time_ms', 0)})}\n\n"

            # Persist AI message
            from datetime import datetime, timezone
            ai_msg = Message(
                chat_id=chat_id, role=MessageRole.ASSISTANT, content=answer,
                sources=ai_result.get("sources"), confidence_score=ai_result.get("confidence_score"),
                tokens_used=ai_result.get("tokens_used"), processing_time_ms=ai_result.get("processing_time_ms"),
                model_used=f"{ai_result.get('provider_tag', '')} {ai_result.get('model_used', '')}".strip(),
            )
            db.add(ai_msg)
            result2 = await db.execute(select(Chat).where(Chat.id == chat_id))
            chat = result2.scalar_one_or_none()
            if chat:
                chat.message_count = (chat.message_count or 0) + 2
                chat.last_message_at = datetime.now(timezone.utc)
            await db.commit()

        except RuntimeError as exc:
            provider_label = provider.upper() if provider != "auto" else "ALL PROVIDERS"
            error_msg = f"[ERROR] {provider_label} failed: {exc}"
            logger.error("[STREAM ERROR] %s", error_msg)
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── Messages helpers ─────────────────────────────────────────────────────────

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    chat_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Chat not found")
    msgs = await db.execute(
        select(Message).where(Message.chat_id == chat_id)
        .order_by(Message.created_at)
        .offset((page - 1) * page_size).limit(page_size)
    )
    return msgs.scalars().all()


@router.post("/{chat_id}/messages/{message_id}/reaction", response_model=MessageOut)
async def react_to_message(
    chat_id: str, message_id: str, data: MessageReactionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Message).join(Chat).where(
            Message.id == message_id, Chat.id == chat_id, Chat.user_id == current_user.id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if data.reaction not in ("like", "dislike", "helpful", "unhelpful"):
        raise HTTPException(status_code=400, detail="Invalid reaction")
    msg.reaction = data.reaction
    await db.commit()
    return {"message": "Reaction added"}


@router.get("/{chat_id}/export")
async def export_chat(
    chat_id: str,
    format: str = Query("json", regex="^(pdf|csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
        .options(selectinload(Chat.messages))
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if format == "json":
        data = {
            "chat_id": chat.id, "title": chat.title,
            "messages": [
                {"role": m.role.value, "content": m.content,
                 "model_used": m.model_used, "created_at": m.created_at.isoformat()}
                for m in chat.messages
            ],
        }
        return StreamingResponse(
            iter([json.dumps(data, indent=2)]), media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="chat_{chat_id}.json"'},
        )
    elif format == "csv":
        import csv as csv_mod, io
        output = io.StringIO()
        writer = csv_mod.writer(output)
        writer.writerow(["role", "content", "model_used", "created_at"])
        for m in chat.messages:
            writer.writerow([m.role.value, m.content, m.model_used or "", m.created_at.isoformat()])
        return StreamingResponse(
            iter([output.getvalue()]), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="chat_{chat_id}.csv"'},
        )
    else:
        text_content = "\n\n".join(
            f"[{m.role.value.upper()}] {m.content}" for m in chat.messages
        )
        return StreamingResponse(
            iter([text_content.encode()]), media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="chat_{chat_id}.txt"'},
        )
