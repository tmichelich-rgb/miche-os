#!/bin/bash
set -e
echo "🌱 Seeding database..."
cd backend
npm run db:push
npm run db:seed
echo "✅ Seed complete!"
