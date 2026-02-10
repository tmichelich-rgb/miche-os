#!/bin/bash
set -e
echo "🧪 Running tests..."

cd backend

echo "📋 Unit tests..."
npx jest test/unit --verbose

echo "📋 Integration tests..."
npx jest --config test/jest-e2e.json --verbose

echo "✅ All tests passed!"
