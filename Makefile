.PHONY: up down build logs test clean seed help

# Default target
help:
	@echo "MedicalRAG - Available Commands"
	@echo "================================"
	@echo "make up       - Start all services"
	@echo "make build    - Build and start all services"
	@echo "make down     - Stop all services"
	@echo "make logs     - View all logs"
	@echo "make test     - Run backend tests"
	@echo "make seed     - Seed medical knowledge base"
	@echo "make clean    - Stop and remove all volumes (DATA LOSS)"
	@echo "make shell    - Open backend shell"
	@echo "make db       - Open database shell"

up:
	docker compose up -d

build:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

test:
	cd backend && pytest tests/ -v --tb=short

test-unit:
	cd backend && pytest tests/unit/ -v

test-security:
	cd backend && pytest tests/security/ -v

test-integration:
	cd backend && pytest tests/integration/ -v

seed:
	docker compose exec backend python /app/data/seed/seed_medical_knowledge.py

clean:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] && docker compose down -v || echo "Cancelled"

shell:
	docker compose exec backend bash

db:
	docker compose exec postgres psql -U medrag -d medicalrag

redis-cli:
	docker compose exec redis redis-cli -a redispass

ps:
	docker compose ps

restart-backend:
	docker compose restart backend

health:
	@echo "Checking service health..."
	@curl -sf http://localhost:8000/health && echo " ✓ Backend" || echo " ✗ Backend"
	@curl -sf http://localhost:3000 > /dev/null && echo " ✓ Frontend" || echo " ✗ Frontend"
	@curl -sf http://localhost:6333/healthz && echo " ✓ Qdrant" || echo " ✗ Qdrant"
	@docker compose exec redis redis-cli -a redispass ping > /dev/null 2>&1 && echo " ✓ Redis" || echo " ✗ Redis"
