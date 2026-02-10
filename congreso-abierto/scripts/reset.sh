#!/bin/bash
set -e
echo "🔄 Resetting database..."
cd backend
npm run db:reset
npm run db:seed
echo "✅ Reset complete!"
