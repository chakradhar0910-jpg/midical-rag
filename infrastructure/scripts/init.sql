-- MedicalRAG Database Initialization
-- This runs once when the postgres container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE medicalrag TO medrag;

-- Create indexes for full-text search (after tables are created by SQLAlchemy)
-- These will be applied post-initialization by Alembic migrations
