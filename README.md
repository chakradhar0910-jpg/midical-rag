# 🏥 MedicalRAG — Enterprise Medical AI Chatbot Platform

[![CI/CD](https://github.com/yourorg/medicalrag/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/yourorg/medicalrag/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)

A production-ready, full-stack Medical RAG (Retrieval-Augmented Generation) chatbot platform built for healthcare professionals. Features HIPAA-inspired security, source-cited AI responses, emergency detection, and a comprehensive admin dashboard.

---

## ✨ Features

### 🤖 AI & RAG Engine
- **Retrieval-Augmented Generation** — answers grounded in your medical knowledge base
- **Strict multi-provider routing** — Ollama (local) and Gemini (cloud), selectable per-request, with zero silent fallback
- **Source citations** with confidence scores on every response
- **Multi-format document ingestion** — PDF, DOCX, TXT, CSV, Markdown
- **Emergency detection** — automatic recognition of life-threatening situations with 911 guidance
- **Hallucination mitigation** — unsafe content filtering and medical disclaimers
- **Streaming responses** — real-time token-by-token streaming via SSE
- **1000+ preloaded medical entries** — WHO guidelines, emergency protocols, disease references

### 🔐 Security (HIPAA-Inspired)
- **JWT authentication** with automatic refresh token rotation
- **Role-Based Access Control (RBAC)** — Admin, Doctor, User, Viewer roles
- **Multi-Factor Authentication (MFA)** — TOTP-based (Google Authenticator compatible)
- **bcrypt password hashing** with configurable rounds
- **Brute-force protection** — account lockout after failed attempts
- **Complete audit trail** — every action logged with IP, user agent, timestamp
- **Security headers** — XSS, CSRF, clickjacking protection
- **Rate limiting** — per-endpoint rate limits via slowapi

### 💻 Frontend
- **Next.js 15 + React 19** with TypeScript
- **Responsive design** with Tailwind CSS and shadcn/ui components
- **Dark mode** support
- **Chat interface** — streaming, reactions (👍/👎), export (PDF/CSV/JSON)
- **Document manager** — drag-and-drop upload, real-time processing status
- **Admin dashboard** — analytics charts, user management, audit logs

### 🏗️ Infrastructure
- **Docker Compose** — one command to run everything
- **PostgreSQL 16** — primary database with full-text search
- **Redis 7** — caching and session management
- **Qdrant** — high-performance vector database for RAG
- **Nginx** — reverse proxy with rate limiting and security headers
- **Prometheus + Grafana** — monitoring and metrics dashboards
- **GitHub Actions** — automated CI/CD with security scanning

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- 4GB+ RAM recommended
- OpenAI API key (for production AI responses)

### 1. Clone the repository
```bash
git clone https://github.com/yourorg/medicalrag.git
cd medicalrag
```

### 2. Configure environment
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set your **OpenAI API key**:
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 3. Launch the platform
```bash
docker compose up --build
```

This automatically:
- Starts all 8 services (postgres, redis, qdrant, backend, frontend, nginx, prometheus, grafana)
- Runs database migrations
- Seeds admin + 10 test users
- Loads medical knowledge base into the vector database

### 4. Access the platform

| Service | URL |
|---------|-----|
| 🌐 Frontend | http://localhost:3000 |
| 📡 API Docs | http://localhost:8000/api/docs |
| 📊 Grafana | http://localhost:3001 |
| 🔍 Prometheus | http://localhost:9090 |
| 🗄️ Qdrant Dashboard | http://localhost:6333/dashboard |

### 5. Login credentials

| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@medicalrag.com | Admin@123456 |
| Doctor | doctor1@medicalrag.com | User@123456 |
| User | user1@medicalrag.com | User@123456 |

---

## 🗂️ Project Structure

```
medicalrag/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/endpoints/   # REST API endpoints
│   │   │   ├── auth.py         # Authentication & MFA
│   │   │   ├── chats.py        # Chat + streaming
│   │   │   ├── documents.py    # Document upload & RAG indexing
│   │   │   ├── users.py        # Profile & settings
│   │   │   └── admin.py        # Admin dashboard API
│   │   ├── core/
│   │   │   ├── config.py       # Application settings
│   │   │   └── security.py     # JWT, bcrypt, RBAC, TOTP
│   │   ├── db/session.py       # AsyncSQLAlchemy setup
│   │   ├── models/models.py    # All SQLAlchemy ORM models
│   │   ├── schemas/schemas.py  # Pydantic request/response schemas
│   │   └── services/
│   │       ├── ai/rag_service.py    # LangChain + Qdrant RAG engine
│   │       └── auth/auth_service.py # Authentication business logic
│   └── tests/                  # pytest test suites
├── frontend/                   # Next.js 15 frontend
│   └── src/app/
│       ├── landing/            # Public landing page
│       ├── auth/               # Login, register, password reset
│       ├── dashboard/          # User dashboard
│       ├── chat/               # AI chat interface
│       ├── documents/          # Document manager
│       ├── profile/            # Profile, MFA, settings
│       └── admin/              # Admin dashboard
├── data/
│   ├── medical_knowledge/      # 1000+ curated medical entries
│   └── seed/                   # Database seeding scripts
├── infrastructure/
│   ├── nginx/                  # Reverse proxy config
│   ├── monitoring/             # Prometheus + Grafana
│   └── scripts/                # DB init scripts
├── docs/                       # Architecture documentation
├── .github/workflows/          # CI/CD pipeline
└── docker-compose.yml          # Full stack orchestration
```

---

## 🛠️ Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Edit with your settings
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local  # Edit NEXT_PUBLIC_API_URL
npm run dev
```

---

## 🧪 Running Tests

```bash
cd backend

# All tests with coverage
pytest --cov=app --cov-report=html

# Individual test suites
pytest tests/unit/           # Unit tests
pytest tests/integration/    # API integration tests
pytest tests/security/       # Security (OWASP) tests
pytest tests/unit/test_rag_service.py  # RAG & safety tests
```

---

## 📡 API Reference

Full OpenAPI documentation available at: **http://localhost:8000/api/docs**

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| POST | `/api/v1/auth/refresh` | Rotate refresh token |
| POST | `/api/v1/auth/mfa/setup` | Setup TOTP MFA |
| GET | `/api/v1/users/me` | Get profile |
| POST | `/api/v1/chats` | Create chat |
| POST | `/api/v1/chats/{id}/messages` | Send message (AI response, respects `X-AI-Provider` header) |
| POST | `/api/v1/chats/{id}/messages/stream` | Streaming SSE response |
| POST | `/api/v1/documents` | Upload & index document |
| GET | `/api/v1/ai/health` | Check Ollama + Gemini provider availability |
| GET | `/api/v1/ai/providers` | List supported provider values and their behavior |
| GET | `/api/v1/admin/stats` | Platform statistics |
| GET | `/api/v1/admin/users` | Manage users |
| GET | `/api/v1/admin/logs` | Audit logs |

---

## 🧭 AI Provider Routing (Strict, No Silent Fallback)

MedicalRAG supports two AI inference backends for chat generation, selectable **per request** via the `X-AI-Provider` HTTP header. Routing is strict: a request for one provider **never** silently falls back to the other.

| Header value | Behavior |
|---|---|
| `ollama` | Uses local Ollama only. If Ollama is unreachable or fails, the API returns `502` with `[ERROR] Ollama not responding: ...`. **Never** calls Gemini. |
| `gemini` | Uses Google Gemini only. If the API key is missing or the call fails, returns `502` with `[ERROR] Gemini API failed: ...`. **Never** calls Ollama. |
| `auto` (default) | Tries Ollama first. If Ollama is unreachable or has no installed models, explicitly logs the reason and switches to Gemini. Both decisions are logged — never silent. |

Every successful response is prefixed with a tag so you always know which engine answered:

| Tag | Meaning |
|---|---|
| `[OLLAMA]` | Strict local mode |
| `[GEMINI]` | Strict cloud mode |
| `[AUTO-LOCAL]` | Auto mode resolved to Ollama |
| `[AUTO-CLOUD]` | Auto mode resolved to Gemini |

### Configuration

Set in `backend/.env`:

```env
DEFAULT_AI_PROVIDER=auto          # used when no X-AI-Provider header is sent

GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=30

OLLAMA_BASE_URL=http://host.docker.internal:11434   # Ollama running on your host machine
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_DEFAULT_MODEL=                                # empty = auto-discover best installed model
```

> **Note:** `OPENAI_API_KEY` is still used, but only for generating embeddings during document indexing (RAG retrieval). It is no longer used for chat answer generation — that responsibility now belongs to Ollama/Gemini.

### Usage examples

```bash
# Force local Ollama — fails hard if Ollama is down, never touches Gemini
curl -X POST http://localhost:8000/api/v1/chats/{chat_id}/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-AI-Provider: ollama" \
  -H "Content-Type: application/json" \
  -d '{"content": "What are symptoms of diabetes?"}'

# Force cloud Gemini — fails hard if key is invalid, never touches Ollama
curl -X POST http://localhost:8000/api/v1/chats/{chat_id}/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-AI-Provider: gemini" \
  -H "Content-Type: application/json" \
  -d '{"content": "How to manage hypertension?"}'

# Check provider health
curl http://localhost:8000/api/v1/ai/health
```

In the UI, a **provider selector** (🧠 Auto / 💻 Ollama / ☁️ Gemini) is available in the chat header, and the **Admin → AI Providers** tab shows real-time status of both backends, including installed Ollama models.

---

## 🔒 Security Architecture

- **Transport**: All traffic through Nginx TLS termination (configure certs for production)
- **Authentication**: JWT access tokens (30min) + refresh tokens (7 days) with rotation
- **Authorization**: RBAC with 4 roles — every endpoint checks role and permissions
- **Passwords**: bcrypt with 12 rounds — never stored in plain text
- **MFA**: TOTP-based (RFC 6238), compatible with Google Authenticator / Authy
- **Audit Logs**: Every action logged — login, logout, CRUD operations, admin changes
- **Rate Limiting**: 60 req/min general, 10 req/min auth endpoints
- **Input Validation**: Pydantic v2 strict validation on all inputs
- **SQL Injection**: SQLAlchemy ORM with parameterized queries
- **Secrets**: Environment variables only — no hardcoded credentials

---

## 🏥 Medical Safety Features

1. **Emergency Detection** — 15+ emergency patterns (chest pain, stroke, overdose, etc.) trigger immediate 911 guidance
2. **Source Citations** — every AI answer includes document sources and confidence scores
3. **Hallucination Filtering** — unsafe content patterns detected and flagged
4. **Medical Disclaimers** — automatically appended to all AI responses
5. **Confidence Scoring** — 0-100% confidence score based on retrieval relevance
6. **Message Reactions** — users can flag unhelpful/incorrect responses

---

## 📊 Monitoring

| Tool | URL | Credentials |
|------|-----|-------------|
| Grafana | http://localhost:3001 | admin / Admin@123456 |
| Prometheus | http://localhost:9090 | None |
| Backend Metrics | http://localhost:8000/metrics | None (internal) |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## ⚠️ Medical Disclaimer

MedicalRAG is an educational and informational tool. It is **not** a substitute for professional medical advice, diagnosis, or treatment. Always consult qualified healthcare professionals for medical decisions. In emergencies, call 911 or your local emergency number immediately.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ for healthcare innovation*
