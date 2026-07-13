# MedicalRAG Architecture Documentation

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          Internet                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │ :80/:443
                    ┌─────────▼─────────┐
                    │   Nginx Reverse   │
                    │   Proxy + TLS     │
                    │   Rate Limiting   │
                    └────────┬──────────┘
              ┌──────────────┼──────────────┐
              │ :3000        │ :8000        │
    ┌─────────▼──────┐  ┌───▼──────────────┐
    │  Next.js 15    │  │  FastAPI Backend  │
    │  Frontend      │  │  (Python 3.12)    │
    │  React 19      │  │  uvicorn 2 workers│
    │  TypeScript    │  │                  │
    └────────────────┘  └───┬──────┬───────┘
                            │      │
              ┌─────────────┘      └─────────────┐
              │                                  │
    ┌─────────▼──────┐              ┌────────────▼────────┐
    │  PostgreSQL 16  │              │   Qdrant Vector DB  │
    │  Primary Store  │              │   Medical Embeddings│
    │  Users/Chats    │              │   text-embed-3-small│
    │  Documents/Logs │              │   1536 dimensions   │
    └─────────────────┘              └─────────────────────┘
              │
    ┌─────────▼──────┐
    │    Redis 7      │
    │  Session Cache  │
    │  Rate Limiting  │
    └─────────────────┘

    ┌─────────────────────────────────────────┐
    │         Monitoring Stack                │
    │  Prometheus (metrics) → Grafana (viz)   │
    └─────────────────────────────────────────┘
```

## RAG Pipeline Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│     Query Pre-Processing        │
│  - Emergency pattern detection  │
│  - Query sanitization           │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│     Embedding Generation        │
│  OpenAI text-embedding-3-small  │
│  1536-dimensional vector        │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│     Vector Similarity Search    │
│  Qdrant cosine similarity       │
│  Top-5 most relevant chunks     │
│  Score threshold filtering      │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│     Context Assembly            │
│  Retrieved chunks + metadata    │
│  Source document titles         │
│  Relevance scores               │
└─────────────────┬───────────────┘
                  │
                  ▼
┌─────────────────────────────────┐
│  Provider Routing (STRICT)      │
│  X-AI-Provider header:          │
│   "ollama" → Ollama ONLY        │
│   "gemini" → Gemini ONLY        │
│   "auto"   → Ollama, else Gemini│
│  No silent fallback, ever       │
└─────────────────┬───────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
┌──────────────────┐ ┌──────────────────┐
│  Ollama (local)   │ │  Gemini (cloud)  │
│  /api/generate    │ │  generateContent │
│  llama3 / mistral │ │  gemini-1.5-flash│
└────────┬──────────┘ └────────┬─────────┘
         │                     │
         └──────────┬──────────┘
                    ▼
┌─────────────────────────────────┐
│     Post-Processing             │
│  - Unsafe content filtering     │
│  - Medical disclaimer appending │
│  - Confidence score calculation │
│  - Source metadata attachment   │
│  - Provider tag prefix          │
│    ([OLLAMA]/[GEMINI]/          │
│     [AUTO-LOCAL]/[AUTO-CLOUD])  │
└─────────────────┬───────────────┘
                  │
                  ▼
              Response

```

## Database Schema (ER Diagram)

```
Users (1) ──────── (N) Chats
  │                      │
  │                      └─── (N) Messages
  │
  ├─── (N) Documents
  │
  ├─── (1) UserSettings
  │
  ├─── (N) Sessions
  │
  ├─── (N) APIKeys
  │
  ├─── (N) AuditLogs
  │
  └─── (N) Notifications

Analytics (standalone time-series)
```

## Security Architecture

```
Request Flow:
Browser → HTTPS/TLS → Nginx → FastAPI → Business Logic → DB

Authentication:
1. Login → verify password (bcrypt) → check MFA (TOTP)
2. Issue JWT access token (30min) + refresh token (7d)
3. Store refresh token session in PostgreSQL
4. Each request: validate JWT signature + expiry + type

Authorization (RBAC):
Admin  → Full platform access
Doctor → Documents + Chats + Analytics
User   → Own Chats + Public Documents  
Viewer → Read-only Chats + Documents

Audit Trail:
All state-changing operations → AuditLog table
Fields: user_id, action, resource_type, resource_id, ip, user_agent, status, timestamp
```

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend Framework | Next.js | 15.x |
| UI Library | React | 19.x |
| Styling | Tailwind CSS | 3.x |
| Type Safety | TypeScript | 5.x |
| State Management | Zustand | 5.x |
| API Client | Axios + React Query | Latest |
| Backend Framework | FastAPI | 0.115 |
| Python Runtime | Python | 3.12 |
| ORM | SQLAlchemy | 2.0 (async) |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Vector DB | Qdrant | Latest |
| AI/LLM (chat) | Ollama (local) + Google Gemini (cloud) | Strict routing |
| AI/LLM (embeddings) | OpenAI text-embedding-3-small | Latest |
| Embeddings | text-embedding-3-small | Latest |
| RAG Framework | LangChain | 0.3.x |
| Container | Docker + Compose | Latest |
| Web Server | Nginx | Alpine |
| Monitoring | Prometheus + Grafana | Latest |
| CI/CD | GitHub Actions | - |
