"""
Medical RAG service — LangChain + Qdrant for retrieval,
strict provider routing (Ollama / Gemini / auto) for generation.
"""
from typing import List, Optional, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchAny,
)
import pypdf
import io
import csv
import re
import uuid
import time
import logging
import httpx
import asyncio

from app.core.config import settings
from app.services.ai.provider_selector import route_to_provider

logger = logging.getLogger(__name__)

# ─── Gemini Embeddings client ──────────────────────────────────────────────────
class GeminiEmbeddings(Embeddings):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gemini-embedding-001"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={self.api_key}"
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": t}]}
                } for t in texts
            ]
        }
        for attempt in range(10):
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 429:
                sleep_time = (2 ** attempt) + 1
                logger.warning(f"Rate limited (429) on embed_documents. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            resp.raise_for_status()
            data = resp.json()
            return [emb["values"] for emb in data["embeddings"]]
        raise RuntimeError("Failed to embed documents after multiple retries due to rate limits.")

    def embed_query(self, text: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]}
        }
        for attempt in range(10):
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 429:
                sleep_time = (2 ** attempt) + 1
                logger.warning(f"Rate limited (429) on embed_query. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]["values"]
        raise RuntimeError("Failed to embed query after multiple retries due to rate limits.")

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={self.api_key}"
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": t}]}
                } for t in texts
            ]
        }
        for attempt in range(10):
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code == 429:
                sleep_time = (2 ** attempt) + 1
                logger.warning(f"Rate limited (429) on aembed_documents. Retrying in {sleep_time}s...")
                await asyncio.sleep(sleep_time)
                continue
            resp.raise_for_status()
            data = resp.json()
            return [emb["values"] for emb in data["embeddings"]]
        raise RuntimeError("Failed to embed documents after multiple retries due to rate limits.")

    async def aembed_query(self, text: str) -> List[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]}
        }
        for attempt in range(10):
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code == 429:
                sleep_time = (2 ** attempt) + 1
                logger.warning(f"Rate limited (429) on aembed_query. Retrying in {sleep_time}s...")
                await asyncio.sleep(sleep_time)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]["values"]
        raise RuntimeError("Failed to embed query after multiple retries due to rate limits.")

# ─── Medical safety constants ─────────────────────────────────────────────────

MEDICAL_DISCLAIMER = """
---
⚕️ **Medical Disclaimer**: This information is for educational purposes only and does not replace professional medical advice. Always consult qualified healthcare professionals.
"""

EMERGENCY_PATTERNS = [
    r"\bchest\s*pain\b", r"\bcan'?t\s+breathe\b", r"\bcannot\s+breathe\b",
    r"\bshortness\s+of\s+breath\b", r"\bsevere\s+bleeding\b",
    r"\bloss\s+of\s+consciousness\b", r"\bunconscious\b", r"\bstroke\b",
    r"\bheart\s+attack\b", r"\bsuicidal\b", r"\boverdose\b",
    r"\bseizure\b", r"\bsevere\s+allergic\b", r"\banaphylaxis\b",
    r"\bsevere\s+head\s+injury\b", r"\bpoisoning\b",
]

UNSAFE_PATTERNS = [
    r"take \d+ times the dose",
    r"ignore medical advice",
    r"you don.?t need a doctor",
]

RAG_SYSTEM_PROMPT = """You are MedicalRAG, an expert AI medical assistant. Answer using ONLY the provided medical knowledge context.

Rules:
- Cite document sources by title
- For emergencies: direct the user to call 112 / 911 immediately
- Always recommend consulting a healthcare professional for personal advice
- Be factual, precise, and clear

Medical Knowledge Context:
{context}

User Question: {question}"""


class MedicalRAGService:
    def __init__(self):
        self._initialized = False
        self.embeddings: Optional[Embeddings] = None
        self.qdrant_client: Optional[QdrantClient] = None
        self.vector_size = 1536
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ",", " "],
        )

    async def initialize(self):
        """Lazy-init embeddings + Qdrant. LLM is now resolved per-request."""
        if self._initialized:
            return
        try:
            provider = getattr(settings, "EMBEDDING_PROVIDER", "openai").lower()
            
            if provider == "ollama":
                logger.info(f"Using Ollama Embeddings ({settings.OLLAMA_EMBEDDING_MODEL})...")
                from langchain_community.embeddings import OllamaEmbeddings
                self.embeddings = OllamaEmbeddings(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_EMBEDDING_MODEL,
                )
                # Determine vector size dynamically by embedding a test string
                dummy_emb = await self.embeddings.aembed_query("test")
                self.vector_size = len(dummy_emb)
                logger.info(f"Detected Ollama embedding dimension: {self.vector_size}")
            elif provider == "gemini" or (not settings.OPENAI_API_KEY or "placeholder" in settings.OPENAI_API_KEY):
                logger.info("Using Gemini Embeddings (gemini-embedding-001)...")
                self.embeddings = GeminiEmbeddings(api_key=settings.GEMINI_API_KEY)
                self.vector_size = 3072
            else:
                logger.info("Using OpenAI Embeddings...")
                self.embeddings = OpenAIEmbeddings(
                    api_key=settings.OPENAI_API_KEY,
                    model=settings.OPENAI_EMBEDDING_MODEL,
                )
                self.vector_size = 1536
            self.qdrant_client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=30,
            )
            await self._ensure_collection()
            self._initialized = True
            logger.info(f"RAG service initialized (embeddings: {self.embeddings.__class__.__name__}, LLM: routed per-request)")
        except Exception as e:
            logger.error("RAG init failed: %s", e)
            raise

    async def _ensure_collection(self):
        collections = self.qdrant_client.get_collections().collections
        names = [c.name for c in collections]
        if settings.QDRANT_COLLECTION_NAME in names:
            info = self.qdrant_client.get_collection(settings.QDRANT_COLLECTION_NAME)
            current_size = info.config.params.vectors.size
            if current_size != self.vector_size:
                logger.warning(f"Recreating Qdrant collection due to dimension change ({current_size} -> {self.vector_size})")
                self.qdrant_client.delete_collection(settings.QDRANT_COLLECTION_NAME)
                names = [n for n in names if n != settings.QDRANT_COLLECTION_NAME]

        if settings.QDRANT_COLLECTION_NAME not in names:
            self.qdrant_client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection: %s", settings.QDRANT_COLLECTION_NAME)

    # ─── Safety helpers ───────────────────────────────────────────────────────

    def detect_emergency(self, text: str) -> bool:
        tl = text.lower()
        return any(re.search(p, tl) for p in EMERGENCY_PATTERNS)

    def detect_unsafe_content(self, text: str) -> bool:
        tl = text.lower()
        return any(re.search(p, tl) for p in UNSAFE_PATTERNS)

    # ─── Text extraction ──────────────────────────────────────────────────────

    def extract_text(self, content: bytes, file_type: str) -> str:
        ft = file_type.lower().strip(".")
        if ft == "pdf":
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n\n".join(p.extract_text() or "" for p in reader.pages).strip()
        elif ft == "docx":
            import docx as _docx
            doc = _docx.Document(io.BytesIO(content))
            return "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        elif ft in ("txt", "md", "markdown"):
            return content.decode("utf-8", errors="replace")
        elif ft == "csv":
            text = content.decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            rows = []
            for i, row in enumerate(reader):
                if i >= 500:
                    break
                r = " | ".join(f"{k}: {v}" for k, v in row.items() if v and str(v).strip())
                if r:
                    rows.append(r)
            return "\n".join(rows)
        raise ValueError(f"Unsupported file type: {file_type}")

    # ─── Document indexing ────────────────────────────────────────────────────

    async def process_document(
        self,
        document_id: str,
        content: bytes,
        file_type: str,
        title: str,
        metadata: Optional[Dict] = None,
    ) -> List[str]:
        await self.initialize()
        text = self.extract_text(content, file_type)
        if not text.strip():
            raise ValueError("No text extracted from document")
        chunks = self.text_splitter.split_text(text)
        if not chunks:
            raise ValueError("Document produced no chunks")
        logger.info("Indexing '%s': %d chunks", title, len(chunks))

        vector_ids: List[str] = []
        points: List[PointStruct] = []
        for i in range(0, len(chunks), 50):
            batch = chunks[i:i + 50]
            embeddings = await self.embeddings.aembed_documents(batch)
            await asyncio.sleep(2.5)
            for j, (chunk, emb) in enumerate(zip(batch, embeddings)):
                vid = str(uuid.uuid4())
                vector_ids.append(vid)
                payload: Dict[str, Any] = {
                    "document_id": document_id,
                    "title": title,
                    "chunk_index": i + j,
                    "chunk_text": chunk[:500],
                    "file_type": file_type,
                }
                if metadata:
                    payload.update({k: v for k, v in metadata.items() if v is not None})
                points.append(PointStruct(id=vid, vector=emb, payload=payload))

        for i in range(0, len(points), 100):
            self.qdrant_client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points[i:i + 100],
            )
        logger.info("Indexed '%s': %d vectors", title, len(vector_ids))
        return vector_ids

    # ─── Retrieval ────────────────────────────────────────────────────────────

    async def search_documents(
        self,
        query: str,
        limit: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        await self.initialize()
        q_emb = await self.embeddings.aembed_query(query)
        search_filter = None
        if document_ids:
            search_filter = Filter(
                must=[FieldCondition(key="document_id", match=MatchAny(any=document_ids))]
            )
        results = self.qdrant_client.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=q_emb,
            limit=limit,
            query_filter=search_filter,
            with_payload=True,
        )
        return [
            {
                "document_id": r.payload.get("document_id", ""),
                "title":       r.payload.get("title", "Unknown"),
                "content":     r.payload.get("chunk_text", ""),
                "score":       float(r.score),
                "chunk_index": r.payload.get("chunk_index", 0),
            }
            for r in results if r.score > 0.3
        ]

    # ─── Generation (provider-routed) ─────────────────────────────────────────

    async def generate_answer(
        self,
        query: str,
        provider: str = "auto",          # from X-AI-Provider header
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline:
          1. Emergency check (immediate response, no LLM call)
          2. Retrieve context from Qdrant
          3. Build prompt with context
          4. Route to provider (Ollama / Gemini / auto) — STRICT, no silent fallback
          5. Post-process + tag response
        """
        await self.initialize()
        start = time.time()

        # ── 1. Emergency detection ─────────────────────────────────────────────
        if self.detect_emergency(query):
            logger.warning("[EMERGENCY] Detected emergency in query — bypassing LLM")
            return {
                "answer": (
                    "🚨 **EMERGENCY DETECTED** 🚨\n\n"
                    "Based on your description, this appears to be a **medical emergency**.\n\n"
                    "**Call emergency services immediately:**\n"
                    "- 🇮🇳 India: **112**\n"
                    "- 🇺🇸 US: **911**\n"
                    "- 🌍 International: **112**\n\n"
                    "**Do NOT wait.** Get emergency help right now."
                    + MEDICAL_DISCLAIMER
                ),
                "sources":          [],
                "confidence_score": 1.0,
                "tokens_used":      0,
                "processing_time_ms": int((time.time() - start) * 1000),
                "is_emergency":     True,
                "model_used":       "safety-filter",
                "provider_used":    "safety-filter",
                "provider_tag":     "[EMERGENCY]",
            }

        # ── 2. Retrieve context ────────────────────────────────────────────────
        sources = await self.search_documents(query, limit=5)
        context = (
            "\n\n---\n\n".join(
                f"**{s['title']}** (Relevance: {s['score']:.0%})\n{s['content']}"
                for s in sources
            )
            if sources
            else "No specific documents found in the knowledge base. Providing general medical information."
        )

        # ── 3. Build RAG prompt ────────────────────────────────────────────────
        full_prompt = RAG_SYSTEM_PROMPT.format(context=context, question=query)

        # ── 4. Route to provider (STRICT) ──────────────────────────────────────
        result = await route_to_provider(full_prompt, provider)
        # route_to_provider raises RuntimeError on failure — propagated to caller

        # ── 5. Post-process ────────────────────────────────────────────────────
        answer = result.text
        if self.detect_unsafe_content(answer):
            answer += (
                "\n\n⚠️ **Important**: Please consult a qualified healthcare "
                "professional before making any medical decisions."
            )
        answer += MEDICAL_DISCLAIMER

        # Prefix with provider tag
        tagged_answer = f"{result.tag} {answer}"

        confidence = (
            min(sum(s["score"] for s in sources) / len(sources) * 1.1, 1.0)
            if sources else 0.4
        )

        ms = int((time.time() - start) * 1000)
        logger.info(
            "[RAG] provider=%s  model=%s  sources=%d  confidence=%.2f  ms=%d",
            result.provider_used, result.model_used, len(sources), confidence, ms,
        )

        return {
            "answer":             tagged_answer,
            "sources":            sources,
            "confidence_score":   round(confidence, 3),
            "tokens_used":        0,
            "processing_time_ms": ms,
            "is_emergency":       False,
            "model_used":         result.model_used,
            "provider_used":      result.provider_used,
            "provider_tag":       result.tag,
        }

    async def delete_document_vectors(self, vector_ids: List[str]) -> None:
        await self.initialize()
        if vector_ids:
            self.qdrant_client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=vector_ids,
            )
            logger.info("Deleted %d vectors", len(vector_ids))


rag_service = MedicalRAGService()
