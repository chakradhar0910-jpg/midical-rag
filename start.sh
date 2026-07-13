#!/bin/bash
set -e

echo "╔══════════════════════════════════════╗"
echo "║        MedicalRAG Quick Start        ║"
echo "╚══════════════════════════════════════╝"

# Check for .env
if [ ! -f "backend/.env" ]; then
  cp backend/.env.example backend/.env 2>/dev/null || true
  echo "⚠  Created backend/.env from example"
fi

# Check for OpenAI key
if grep -q "sk-placeholder" backend/.env 2>/dev/null; then
  echo ""
  echo "⚠  WARNING: No OpenAI API key set."
  echo "   Edit backend/.env and set OPENAI_API_KEY=sk-your-key"
  echo "   The app will still run but AI responses will fail."
  echo ""
  read -p "Continue anyway? (y/n): " confirm
  [ "$confirm" != "y" ] && exit 1
fi

echo ""
echo "🚀 Starting all services..."
docker compose up --build -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Wait for backend
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Backend is ready"
    break
  fi
  echo "  Waiting for backend... ($i/30)"
  sleep 5
done

echo ""
echo "╔══════════════════════════════════════╗"
echo "║          MedicalRAG is Ready!        ║"
echo "╠══════════════════════════════════════╣"
echo "║  App:        http://localhost:3000   ║"
echo "║  API Docs:   http://localhost:8000/api/docs  ║"
echo "║  Grafana:    http://localhost:3001   ║"
echo "╠══════════════════════════════════════╣"
echo "║  Admin:   admin@medicalrag.com       ║"
echo "║  Password: Admin@123456              ║"
echo "╚══════════════════════════════════════╝"
