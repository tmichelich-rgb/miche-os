#!/bin/bash
# ══════════════════════════════════════════════════════════
# MICHE OS — Setup Script
# Crea el repo local, copia los proyectos, y pushea a GitHub
# ══════════════════════════════════════════════════════════

set -e

DESKTOP="$HOME/Desktop"
REPO_DIR="$DESKTOP/miche-os"
REMOTE="https://github.com/tmichelich-rgb/miche-os.git"

echo "🚀 Creando Miche OS..."

# 1. Crear directorio del repo
if [ -d "$REPO_DIR" ]; then
  echo "⚠️  La carpeta $REPO_DIR ya existe. Borrala primero o elegí otro nombre."
  exit 1
fi

mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

# 2. Inicializar git
git init
git branch -m main
git config user.email "tmichelich@gmail.com"
git config user.name "Tomas Michelich"

# 3. Copiar proyectos
echo "📁 Copiando wildfire-ops..."
cp -r "$DESKTOP/wildfire-ops" ./wildfire-ops

echo "📁 Copiando cityops-vial..."
cp -r "$DESKTOP/cityops-vial" ./cityops-vial

echo "📁 Copiando congreso-abierto..."
cp -r "$DESKTOP/congreso-abierto" ./congreso-abierto

echo "📁 Copiando Investigacion Operativa..."
cp -r "$DESKTOP/Investigacion Operativa" ./investigacion-operativa

echo "📁 Extrayendo Bunge Ops como proyecto independiente..."
cp -r "$DESKTOP/Investigacion Operativa/Bunge Ops" ./bunge-ops
rm -rf ./investigacion-operativa/Bunge\ Ops 2>/dev/null || true

# 4. Crear .gitignore
cat > .gitignore << 'GITIGNORE'
# OS
.DS_Store
Thumbs.db

# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/
venv/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Temp files
~$*
*.tmp
*.bak

# Build artifacts
.next/
dist/
build/

# Caches
.rag_index.pkl

# Large binary files (reference books)
*.pdf

# Environment
.env
.env.local
GITIGNORE

# 5. Crear README
cat > README.md << 'README'
# Miche OS

Repositorio central de proyectos de operaciones, optimización y tecnología cívica.

## Proyectos

### wildfire-ops
Sistema de gestión y optimización para operaciones de combate de incendios forestales. Incluye backend de simulación, modelo de asignación de recursos y frontend de visualización geoespacial.

### cityops-vial
Plataforma de optimización vial urbana. Análisis de flujo vehicular, detección de congestión y recomendaciones de intervención para infraestructura de transporte.

### congreso-abierto
Plataforma de transparencia legislativa. Extracción, estructuración y visualización de datos del Congreso argentino — votaciones, proyectos de ley y actividad de legisladores.

### bunge-ops
Plataforma de operaciones para trading de commodities agrícolas. Arquitectura event-driven con motor de riesgo derivado (nunca input manual), optimización logística MILP, y capa de decision intelligence contextual. Diseñado para operaciones de clase mundial en grain trading.

### investigacion-operativa
Suite de herramientas y documentos de Investigación Operativa aplicada. Incluye:
- **INVOP AI**: Producto de IA aplicada a Investigación Operativa (arquitectura, estrategia de contenido, dashboard)
- **OptiSolve**: Solver de programación lineal con interfaz visual

## Stack

- **Backend**: Python (FastAPI), Node.js
- **Frontend**: React, HTML/JS
- **OR/Optimization**: PuLP, scipy, modelos MILP
- **Data**: PostgreSQL, pandas
- **Infra**: Docker, docker-compose

## Autor

Tomas Michelich — [tmichelich@gmail.com](mailto:tmichelich@gmail.com)
README

# 6. Limpiar basura
echo "🧹 Limpiando archivos innecesarios..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "~\$*" -delete 2>/dev/null || true
find . -name ".rag_index.pkl" -delete 2>/dev/null || true
find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf congreso-abierto/frontend/.next 2>/dev/null || true
# Remove large PDFs (reference books, not project files)
rm -f investigacion-operativa/PROGRAMACION\ LINEAL\ Y\ SU\ ENTORNO\ -\ MIGUEL\ MIRANDA.pdf 2>/dev/null || true
rm -f investigacion-operativa/SISTEMAS\ DE\ OPTIMIZACION\ DE\ STOCKS\ -\ MIGUEL\ MIRANDA.pdf 2>/dev/null || true
rm -f investigacion-operativa/TEORIA\ DE\ COLAS\ -\ MIGUEL\ MIRANDA.pdf 2>/dev/null || true

# 7. Stage y commit
echo "📦 Haciendo commit..."
git add -A
git commit -m "Initial commit: consolidate all projects into Miche OS

Five projects unified in a single repository:
- wildfire-ops: wildfire operations optimization platform
- cityops-vial: urban traffic optimization system
- congreso-abierto: legislative transparency platform
- bunge-ops: commodity trading operations platform
- investigacion-operativa: operations research suite (INVOP AI, OptiSolve)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# 8. Push
echo "🚀 Pusheando a GitHub..."
git remote add origin "$REMOTE"
git push -u origin main

echo ""
echo "✅ ¡Listo! Repo publicado en: https://github.com/tmichelich-rgb/miche-os"
echo ""
