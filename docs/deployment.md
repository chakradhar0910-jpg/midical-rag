# MedicalRAG Deployment Guide

## Local Development (Docker Compose)

### Prerequisites
- Docker Engine 24+
- Docker Compose v2.x
- 4GB RAM minimum (8GB recommended)
- 10GB free disk space

### Step 1: Environment Configuration

```bash
cd medical-rag/backend
cp .env.example .env
```

**Required variables to set in `backend/.env`:**

```env
# REQUIRED: Your OpenAI API key
OPENAI_API_KEY=sk-your-key-here

# REQUIRED: Strong secret key (minimum 32 characters)
SECRET_KEY=your-super-secret-key-change-me-32chars

# Admin credentials (change before production)
ADMIN_EMAIL=admin@medicalrag.com
ADMIN_PASSWORD=Admin@123456
```

### Step 2: Launch

```bash
docker compose up --build
```

Expected startup sequence (takes 2-3 minutes):
1. PostgreSQL starts & initializes
2. Redis starts
3. Qdrant starts
4. Backend starts → creates DB tables → seeds admin + test users
5. Frontend builds & starts
6. Nginx starts

### Step 3: Seed Medical Knowledge (Optional - runs automatically in production)

To manually load the full medical knowledge base into Qdrant:

```bash
docker compose exec backend python -c "
import asyncio
import sys
sys.path.insert(0, '.')
exec(open('/app/data/seed/seed_medical_knowledge.py').read())
asyncio.run(main())
"
```

Or from outside Docker:
```bash
cd data/seed
OPENAI_API_KEY=your-key python seed_medical_knowledge.py
```

### Step 4: Verify Services

```bash
# Check all containers are running
docker compose ps

# Check backend health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:3000

# Check Qdrant
curl http://localhost:6333/healthz
```

---

## Production Deployment

### Server Requirements
- Ubuntu 22.04 LTS or similar
- 4 vCPU, 8GB RAM minimum
- 50GB SSD storage
- Domain name with DNS configured

### Step 1: Server Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install docker-compose-plugin -y
```

### Step 2: Configure for Production

```bash
# Clone repository
git clone https://github.com/yourorg/medicalrag.git
cd medicalrag

# Configure environment
cp backend/.env.example backend/.env
nano backend/.env
```

Production-critical settings:
```env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate with: openssl rand -base64 32>
DATABASE_URL=postgresql+asyncpg://medrag:STRONG_PASSWORD@postgres:5432/medicalrag
OPENAI_API_KEY=sk-your-production-key
CORS_ORIGINS=https://yourdomain.com
ADMIN_PASSWORD=<very-strong-password>
```

### Step 3: SSL/TLS with Certbot

```bash
sudo apt-get install certbot -y

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Certificates will be at:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

Update `infrastructure/nginx/conf.d/default.conf` to enable HTTPS:
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # ... rest of config
}
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

### Step 4: Deploy

```bash
docker compose -f docker-compose.yml up -d --build
```

### Step 5: Backup Strategy

```bash
# Add to crontab (daily at 2am)
0 2 * * * docker compose exec -T postgres pg_dump -U medrag medicalrag | gzip > /backups/db_$(date +%Y%m%d).sql.gz

# Qdrant backup
0 3 * * * docker compose exec -T qdrant tar czf - /qdrant/storage > /backups/qdrant_$(date +%Y%m%d).tar.gz

# Keep last 30 days
find /backups -name "*.gz" -mtime +30 -delete
```

---

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | MedicalRAG |
| `SECRET_KEY` | JWT signing key (32+ chars) | **Required** |
| `DATABASE_URL` | PostgreSQL connection URL | **Required** |
| `REDIS_URL` | Redis connection URL | **Required** |
| `QDRANT_HOST` | Qdrant hostname | qdrant |
| `OPENAI_API_KEY` | OpenAI key — used ONLY for embeddings (RAG retrieval) | **Required** |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | text-embedding-3-small |
| `DEFAULT_AI_PROVIDER` | Provider used when no `X-AI-Provider` header sent: `ollama` \| `gemini` \| `auto` | auto |
| `GEMINI_API_KEY` | Google Gemini API key (cloud chat generation) | — |
| `GEMINI_MODEL` | Gemini model name | gemini-1.5-flash |
| `GEMINI_TIMEOUT_SECONDS` | Gemini request timeout | 30 |
| `OLLAMA_BASE_URL` | Ollama server URL (local chat generation) | http://host.docker.internal:11434 |
| `OLLAMA_TIMEOUT_SECONDS` | Ollama request timeout (local models are slower) | 120 |
| `OLLAMA_DEFAULT_MODEL` | Force a specific Ollama model; empty = auto-discover best installed model | — |
| `ADMIN_EMAIL` | Admin account email | admin@medicalrag.com |
| `ADMIN_PASSWORD` | Admin account password | Admin@123456 |
| `CORS_ORIGINS` | Allowed CORS origins | http://localhost:3000 |
| `MAX_UPLOAD_SIZE_MB` | Max document upload size | 50 |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | 60 |
| `BCRYPT_ROUNDS` | Password hash rounds | 12 |
| `MAX_LOGIN_ATTEMPTS` | Before account lockout | 5 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token TTL | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | 7 |

### Setting up Ollama for local AI (optional)

If you want to use the `ollama` or `auto` provider modes, install Ollama on your **host machine** (not inside Docker):

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.2:1b      # or any model: mistral, llama3, gemma2, etc.
ollama serve                  # usually starts automatically after install
```

The backend container reaches your host's Ollama via `host.docker.internal:11434` (already configured in `docker-compose.yml` with `extra_hosts: host-gateway`). Verify connectivity:

```bash
curl http://localhost:8000/api/v1/ai/health
```

---

## Monitoring Setup


### Grafana Dashboard

1. Navigate to http://localhost:3001
2. Login: admin / Admin@123456
3. Go to Dashboards → Import
4. Import the pre-configured dashboards from `infrastructure/monitoring/grafana/`

### Key Metrics to Monitor

| Metric | Alert Threshold |
|--------|----------------|
| `http_request_duration_seconds` | p99 > 5s |
| `http_requests_total{status="5xx"}` | > 1% error rate |
| PostgreSQL connections | > 80% of max |
| Redis memory usage | > 80% |
| Qdrant collection size | Monitor growth |

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker compose logs backend --tail=50

# Common issues:
# 1. Database not ready - wait longer or check postgres logs
# 2. Invalid OpenAI key - check OPENAI_API_KEY
# 3. Port conflict - check if 8000 is in use
```

### Documents not processing
```bash
# Check if Qdrant is running
curl http://localhost:6333/healthz

# Check backend logs for processing errors
docker compose logs backend | grep "ERROR"

# Manually reprocess via API
curl -X POST http://localhost:8000/api/v1/documents/{doc_id}/reprocess \
  -H "Authorization: Bearer your-token"
```

### Frontend can't reach backend
```bash
# Check NEXT_PUBLIC_API_URL is set correctly
# Default: http://localhost:8000

# Check Nginx routing
docker compose logs nginx

# Test direct backend access
curl http://localhost:8000/health
```

### Reset everything (clean slate)
```bash
docker compose down -v  # WARNING: deletes all data
docker compose up --build
```
