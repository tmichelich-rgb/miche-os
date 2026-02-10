# Congreso Abierto

Plataforma ciudadana de transparencia del Congreso argentino. MVP enfocado en la Cámara de Diputados.

## Stack

- **Backend:** NestJS (TypeScript) + Fastify
- **Database:** PostgreSQL + Prisma ORM
- **Queue/Cache:** Redis + BullMQ
- **Search:** Meilisearch
- **Frontend:** Next.js 14 + TailwindCSS
- **Mobile:** React Native (Expo) — pendiente

## Requisitos

- Docker + Docker Compose
- Node.js 20+
- npm 10+

## Inicio Rápido

### 1. Clonar e instalar

    git clone <repo>
    cd congreso-abierto

### 2. Levantar infraestructura

    docker-compose up -d

Esto inicia Postgres (5432), Redis (6379) y Meilisearch (7700).

### 3. Configurar backend

    cd backend
    cp .env.example .env
    npm install
    npx prisma generate --schema=src/prisma/schema.prisma
    npx prisma db push --schema=src/prisma/schema.prisma
    npm run db:seed

### 4. Iniciar backend

    npm run dev

API disponible en http://localhost:3000/api/v1
Swagger docs en http://localhost:3000/api/docs

### 5. Iniciar frontend

    cd ../frontend
    npm install
    npm run dev

Frontend en http://localhost:3001

## Scripts

| Script | Descripción |
|--------|-------------|
| `./scripts/dev.sh` | Setup completo (docker + install + migrate + seed) |
| `./scripts/test.sh` | Ejecutar unit + integration tests |
| `./scripts/seed.sh` | Re-seed la base de datos |
| `./scripts/reset.sh` | Reset completo de la DB |
| `cd backend && npm run dev` | Backend en modo watch |
| `cd backend && npm run db:studio` | Prisma Studio (GUI para DB) |
| `cd backend && npm run workers:dev` | Workers ETL |
| `cd frontend && npm run dev` | Frontend Next.js |

## Estructura del Proyecto

    congreso-abierto/
    ├── backend/
    │   ├── src/
    │   │   ├── main.ts                    # Entry point
    │   │   ├── app.module.ts              # Root module
    │   │   ├── modules/
    │   │   │   ├── prisma/                # Database service
    │   │   │   ├── legislators/           # Diputados API
    │   │   │   ├── bills/                 # Proyectos API
    │   │   │   ├── feed/                  # Feed de eventos
    │   │   │   ├── comments/              # Comentarios + moderación
    │   │   │   ├── reactions/             # Reacciones
    │   │   │   └── search/               # Meilisearch integration
    │   │   ├── workers/
    │   │   │   ├── ingest/               # Ingesta de datos
    │   │   │   ├── normalize/            # Normalización
    │   │   │   ├── metrics/              # Cálculo de KPIs
    │   │   │   └── feed-generator/       # Generación de posts
    │   │   └── prisma/
    │   │       ├── schema.prisma         # DB schema
    │   │       └── seed.ts               # Seed script
    │   └── test/
    │       ├── fixtures/                 # Datos de prueba
    │       ├── unit/                     # Unit tests
    │       └── integration/              # Integration tests
    ├── frontend/
    │   └── src/
    │       ├── app/                      # Next.js pages
    │       ├── components/               # React components
    │       ├── lib/                      # API client
    │       └── types/                    # TypeScript types
    ├── docs/
    │   ├── ARCHITECTURE.md               # Decisiones técnicas
    │   ├── API_SPEC.md                   # Especificación API
    │   └── BACKLOG.md                    # Plan de sprints
    ├── docker-compose.yml
    └── scripts/

## Pipeline de Datos

    Fuentes Oficiales → Source Adapters → Ingest Worker → Raw Storage
                                                    ↓
                                          Normalize Worker → DB
                                                    ↓
                                    ┌───────────────┴────────────────┐
                                    ↓                                ↓
                              Metrics Worker                Feed Generator
                                    ↓                                ↓
                           legislator_metrics                   feed_posts

## Principios

1. **Data-driven:** El sistema muestra hechos, no opiniones.
2. **Trazabilidad:** Cada dato tiene source_ref (URL + timestamp + checksum).
3. **Sin inferencias:** Si no hay datos directos, se muestra "No disponible".
4. **Idempotencia:** Toda ingesta puede re-ejecutarse sin duplicar datos.
5. **Resiliencia:** Jobs con reintentos, dead letter queues, monitoreo.

## Verificación

Con docker-compose y seed, deberías poder:

- Ver listado de diputados: `GET /api/v1/legislators`
- Ver perfil con KPIs: `GET /api/v1/legislators/:id`
- Ver proyectos con historial: `GET /api/v1/bills/:id`
- Ver feed con posts automáticos: `GET /api/v1/feed`
- Crear comentarios y reacciones: `POST /api/v1/comments`, `POST /api/v1/reactions/toggle`
- Cada feed_post tiene source_ref asociado

## Licencia

MIT
