#!/bin/bash
# Wildfire Ops Allocation Engine - Startup Script

cd "$(dirname "$0")"

PORT=${1:-8080}

echo "Starting Wildfire Ops Allocation Engine..."
echo "Open http://localhost:$PORT in your browser"
echo ""

python3 backend/server.py $PORT
