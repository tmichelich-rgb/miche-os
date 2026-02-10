#!/bin/bash
set -e
echo "🚀 Starting Congreso Abierto development environment..."

# Start infrastructure
echo "📦 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for Postgres..."
until docker exec congreso-db pg_isready -U congreso -d congreso_abierto > /dev/null 2>&1; do sleep 1; done
echo "✅ Postgres ready"

echo "⏳ Waiting for Redis..."
until docker exec congreso-redis redis-cli ping > /dev/null 2>&1; do sleep 1; done
echo "✅ Redis ready"

echo "⏳ Waiting for Meilisearch..."
until curl -sf http://localhost:7700/health > /dev/null 2>&1; do sleep 1; done
echo "✅ Meilisearch ready"

# Setup backend
cd backend
echo "📦 Installing backend dependencies..."
npm install

echo "🗄️ Running database migrations..."
npm run db:push

echo "🌱 Seeding database..."
npm run db:seed

echo "🔍 Indexing search..."
curl -s -X POST http://localhost:3000/api/v1/search/reindex || true

echo "✅ Development environment ready!"
echo ""
echo "  Backend:     cd backend && npm run dev"
echo "  Frontend:    cd frontend && npm run dev"
echo "  Swagger:     http://localhost:3000/api/docs"
echo "  DB Studio:   cd backend && npm run db:studio"
