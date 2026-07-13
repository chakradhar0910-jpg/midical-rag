"""Document management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from pathlib import Path
import aiofiles
import os
import logging

from app.db.session import get_db
from app.models.models import Document, DocumentStatus, User, AuditLog, AuditAction
from app.schemas.schemas import DocumentResponse, DocumentUpdate, DocumentListResponse, MessageOut
from app.api.v1.deps import get_current_active_user
from app.services.ai.rag_service import rag_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def process_document_background(document_id: str, file_path: str, file_type: str, title: str):
    """Background task to process document."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()
            if not doc:
                return

            doc.status = DocumentStatus.PROCESSING
            from datetime import datetime, timezone
            doc.processing_started_at = datetime.now(timezone.utc)
            await db.commit()

            with open(file_path, "rb") as f:
                content = f.read()

            vector_ids = await rag_service.process_document(
                document_id=document_id,
                content=content,
                file_type=file_type,
                title=title,
                metadata={"category": doc.category, "tags": doc.tags},
            )

            doc.status = DocumentStatus.PROCESSED
            doc.vector_ids = vector_ids
            doc.chunk_count = len(vector_ids)
            doc.processing_completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Document {document_id} processed: {len(vector_ids)} chunks")
        except Exception as e:
            logger.error(f"Document processing error {document_id}: {e}")
            async with AsyncSessionLocal() as db2:
                result = await db2.execute(select(Document).where(Document.id == document_id))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)
                    await db2.commit()


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    is_public: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload and index a medical document."""
    # Validate file type
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in settings.allowed_extensions_list:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")

    # Validate file size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File too large. Max: {settings.MAX_UPLOAD_SIZE_MB}MB")

    # Save file
    import uuid
    doc_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{doc_id}.{file_ext}"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    doc_title = title or file.filename.rsplit(".", 1)[0]
    doc = Document(
        id=doc_id,
        user_id=current_user.id,
        title=doc_title,
        description=description,
        file_name=file.filename,
        file_type=file_ext,
        file_size=len(content),
        file_path=str(file_path),
        status=DocumentStatus.PENDING,
        category=category,
        is_public=is_public,
    )
    db.add(doc)

    log = AuditLog(
        user_id=current_user.id,
        action=AuditAction.DOCUMENT_UPLOAD,
        resource_type="document",
        resource_id=doc_id,
        details={"file_name": file.filename, "file_size": len(content)},
    )
    db.add(log)
    await db.commit()
    await db.refresh(doc)

    # Process in background
    background_tasks.add_task(process_document_background, doc_id, str(file_path), file_ext, doc_title)
    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List user's documents."""
    query = select(Document).where(Document.user_id == current_user.id)
    if search:
        query = query.where(Document.title.ilike(f"%{search}%"))
    if status:
        query = query.where(Document.status == status)
    if category:
        query = query.where(Document.category == category)
    query = query.order_by(Document.created_at.desc())

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    docs = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return DocumentListResponse(documents=list(docs), total=total, page=page, page_size=page_size)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get document details."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update document metadata."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{doc_id}", response_model=MessageOut)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a document and its vectors."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete vectors
    if doc.vector_ids:
        try:
            await rag_service.delete_document_vectors(doc.vector_ids)
        except Exception as e:
            logger.warning(f"Vector deletion failed: {e}")

    # Delete file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    log = AuditLog(
        user_id=current_user.id,
        action=AuditAction.DOCUMENT_DELETE,
        resource_type="document",
        resource_id=doc_id,
    )
    db.add(log)
    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted successfully"}


@router.post("/{doc_id}/reprocess", response_model=MessageOut)
async def reprocess_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Re-process a failed or pending document."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = DocumentStatus.PENDING
    doc.error_message = None
    await db.commit()

    background_tasks.add_task(
        process_document_background, doc_id, doc.file_path, doc.file_type, doc.title
    )
    return {"message": "Document reprocessing started"}
