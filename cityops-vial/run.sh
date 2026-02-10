#!/bin/bash
# CityOps Vial - Script de inicio

cd "$(dirname "$0")"
PORT=${1:-8080}

echo "Iniciando CityOps Vial..."
echo "Abrir http://localhost:$PORT en el navegador"
echo ""

python3 backend/server.py $PORT
