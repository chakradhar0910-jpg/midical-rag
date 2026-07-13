# Stop on error
$ErrorActionPreference = "Stop"

echo "1/7 Initializing Git Repository..."
git init
git branch -M main

echo "2/7 Commit 1: Root config and docs"
git add README.md LICENSE docker-compose.yml .gitignore .dockerignore AGENTS.md CONTRIBUTING.md SECURITY.md .editorconfig .pre-commit-config.yaml pyproject.toml requirements.txt .vulture Makefile start.sh .env.example
git commit -m "chore: add root configuration, documentation, and docker setup"

echo "3/7 Commit 2: Backend core"
git add backend/app/core backend/app/db backend/app/models backend/Dockerfile backend/requirements.txt backend/alembic.ini backend/app/__init__.py
git commit -m "feat(backend): add core config, database setup, and dependencies"

echo "4/7 Commit 3: Backend APIs and Services"
git add backend/app/api backend/app/services backend/app/schemas backend/main.py backend/tests backend/pytest.ini
git commit -m "feat(backend): implement API endpoints and AI/RAG services"

echo "5/7 Commit 4: Frontend config"
git add frontend/package.json frontend/package-lock.json frontend/next.config.js frontend/postcss.config.js frontend/tailwind.config.ts frontend/tsconfig.json frontend/tsconfig.tsbuildinfo frontend/.eslintrc.json frontend/.env.example frontend/next-env.d.ts frontend/Dockerfile
git commit -m "feat(frontend): add Next.js configuration and dependencies"

echo "6/7 Commit 5: Frontend UI"
git add frontend/src frontend/public
git commit -m "feat(frontend): build UI application and components"

echo "7/7 Commit 6: Infrastructure and Data"
# Add everything else that remains (infrastructure, data, docs)
git add infrastructure data docs
git add .
git commit -m "docs: add architecture infrastructure and static data"

echo "Setting remote and pushing to GitHub..."
git remote add origin https://github.com/chakradhar0910-jpg/midical-rag.git
git push -u origin main

echo "Done!"
