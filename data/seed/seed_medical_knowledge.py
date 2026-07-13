"""
Seed script to load medical knowledge base into the vector database.
Run: python scripts/seed_medical_knowledge.py
"""
import asyncio
import csv
import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.services.ai.rag_service import rag_service
from app.db.session import AsyncSessionLocal
from app.models.models import Document, DocumentStatus, User, UserSettings
from app.core.security import get_password_hash
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "medical_knowledge"


async def seed_admin_user():
    """Ensure admin user exists."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if not result.scalar_one_or_none():
            from app.models.models import UserRole, UserStatus
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                full_name="System Administrator",
                is_email_verified=True,
            )
            db.add(admin)
            await db.flush()
            db.add(UserSettings(user_id=admin.id))
            await db.commit()
            logger.info(f"Admin user created: {settings.ADMIN_EMAIL}")
        else:
            logger.info("Admin user already exists")


async def seed_medical_documents():
    """Load medical knowledge files into vector database."""
    await rag_service.initialize()

    files_to_seed = [
        ("WHO Clinical Guidelines", DATA_DIR / "who_guidelines.md", "md", "WHO Guidelines"),
        ("Emergency Medical Protocols", DATA_DIR / "emergency_protocols.md", "md", "Emergency Care"),
        ("Medical Knowledge Base", DATA_DIR / "medical_knowledge_base.csv", "csv", "General Medicine"),
    ]

    async with AsyncSessionLocal() as db:
        # Get admin user id
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin = result.scalar_one_or_none()
        if not admin:
            logger.error("Admin user not found. Run seed_admin_user first.")
            return

        for title, filepath, file_type, category in files_to_seed:
            if not filepath.exists():
                logger.warning(f"File not found: {filepath}")
                continue

            # Check if already seeded
            result = await db.execute(select(Document).where(Document.title == title))
            if result.scalar_one_or_none():
                logger.info(f"Already seeded: {title}")
                continue

            content = filepath.read_bytes()
            import uuid
            doc_id = str(uuid.uuid4())

            doc = Document(
                id=doc_id,
                user_id=admin.id,
                title=title,
                description=f"Seeded medical knowledge: {title}",
                file_name=filepath.name,
                file_type=file_type,
                file_size=len(content),
                file_path=str(filepath),
                status=DocumentStatus.PROCESSING,
                category=category,
                is_public=True,
                source_type="system",
            )
            db.add(doc)
            await db.commit()

            try:
                logger.info(f"Indexing: {title}...")
                vector_ids = await rag_service.process_document(
                    document_id=doc_id,
                    content=content,
                    file_type=file_type,
                    title=title,
                    metadata={"category": category, "is_system": True},
                )
                doc.status = DocumentStatus.PROCESSED
                doc.vector_ids = vector_ids
                doc.chunk_count = len(vector_ids)
                from datetime import datetime, timezone
                doc.processing_completed_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info(f"✓ Indexed {title}: {len(vector_ids)} chunks")
            except Exception as e:
                logger.error(f"✗ Failed to index {title}: {e}")
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                await db.commit()

    # Also seed diseases.json as a separate document
    diseases_file = DATA_DIR / "diseases.json"
    if diseases_file.exists():
        diseases = json.loads(diseases_file.read_text())
        diseases_text = "\n\n".join([
            f"# {d['disease']}\n"
            f"**Symptoms**: {', '.join(d.get('symptoms', []))}\n"
            f"**Treatments**: {', '.join(d.get('treatments', []))}\n"
            f"**Emergency Signs**: {', '.join(d.get('emergency_signs', []))}\n"
            f"**References**: {', '.join(d.get('references', []))}"
            for d in diseases
        ])
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
            admin = result.scalar_one_or_none()
            result2 = await db.execute(select(Document).where(Document.title == "Disease Reference Database"))
            if not result2.scalar_one_or_none() and admin:
                import uuid
                doc_id = str(uuid.uuid4())
                doc = Document(
                    id=doc_id, user_id=admin.id, title="Disease Reference Database",
                    description="Curated disease reference with symptoms, treatments, and emergency signs",
                    file_name="diseases.txt", file_type="txt", file_size=len(diseases_text),
                    file_path="seeded", status=DocumentStatus.PROCESSING,
                    category="Disease Reference", is_public=True, source_type="system",
                )
                db.add(doc)
                await db.commit()
                try:
                    vector_ids = await rag_service.process_document(
                        doc_id, diseases_text.encode(), "txt",
                        "Disease Reference Database", {"category": "Disease Reference"}
                    )
                    doc.status = DocumentStatus.PROCESSED
                    doc.vector_ids = vector_ids
                    doc.chunk_count = len(vector_ids)
                    await db.commit()
                    logger.info(f"✓ Indexed Disease Reference: {len(vector_ids)} chunks")
                except Exception as e:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)
                    await db.commit()
                    logger.error(f"Failed disease seeding: {e}")

    logger.info("Medical knowledge seeding complete!")


async def main():
    logger.info("Starting medical knowledge seeding...")
    await seed_admin_user()
    await seed_medical_documents()
    logger.info("All done!")


if __name__ == "__main__":
    asyncio.run(main())
