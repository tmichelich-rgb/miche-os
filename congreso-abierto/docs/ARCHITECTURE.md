# Congreso Abierto — Decisiones de Stack y Arquitectura

## 1. Decisiones de Stack

### Backend: NestJS (TypeScript)
**Justificación:** NestJS sobre Fastify. Para un proyecto con múltiples módulos (legislators, bills, feed, social, ETL workers), NestJS provee:
- Inyección de dependencias nativa → testeable, desacoplado.
- Módulos con límites claros → cada dominio es un módulo independiente.
- Decoradores para auth, rate limiting, validación → menos boilerplate.
- Integración directa con BullMQ (@nestjs/bullmq) para workers.
- Swagger/OpenAPI con un decorador → spec auto-generada.
- Fastify como HTTP adapter interno (no Express) → performance comparable.

**Tradeoff:** Más boilerplate que Fastify puro, pero la estructura escala mejor con +10 módulos.

### Mobile: React Native (Expo)
**Justificación:** Comparte ecosistema TypeScript/React con Next.js. Expo simplifica build/deploy para MVP. Reutilizamos types, hooks de API, y lógica de negocio entre web y mobile.

**Tradeoff:** Flutter tiene mejor performance en animaciones, pero la prioridad es velocidad de desarrollo y code sharing.

### DB: PostgreSQL + Prisma
- Postgres: JSONB para raw payloads, full-text search nativo como fallback, extensiones (pg_trgm).
- Prisma: type-safe queries, migraciones versionadas, seeding integrado.

### Cache/Queue: Redis + BullMQ
- Redis para cache de perfiles/feed y como broker de BullMQ.
- BullMQ para jobs de ingesta, normalización, métricas, generación de feed.
- Reintentos configurables, dead letter queues, dashboard con Bull Board.

### Search: Meilisearch
- Más simple que Elastic para MVP. Typo-tolerant, facets, <50ms responses.
- Indexamos legislators y bills. Feed se filtra por DB (queries simples con índices).

### Auth: Magic Link + OAuth Google
- Magic link para onboarding sin fricción.
- OAuth Google como alternativa.
- JWT con refresh tokens.

## 2. Arquitectura End-to-End

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOURCES (Oficiales)                      │
│  CKAN APIs │ CSV Downloads │ HTML Pages (last resort)           │
└──────┬──────────────┬──────────────┬────────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCE ADAPTERS (Conectores)                  │
│  CkanAdapter │ CsvAdapter │ HtmlScraperAdapter                  │
│  Cada uno implementa: fetch() → RawPayload                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGEST WORKER (BullMQ)                        │
│  1. Llama adapter.fetch()                                       │
│  2. Guarda raw en filesystem (dev) / S3 (prod)                  │
│  3. Inserta source_ref en DB (url, checksum, timestamp)         │
│  4. Registra ingestion_run con stats                            │
│  5. Dispara job de normalización                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   NORMALIZE WORKER (BullMQ)                      │
│  1. Lee raw payload desde storage                               │
│  2. Parsea según tipo (legislator/bill/vote/attendance)         │
│  3. Upsert en tablas normalizadas (Prisma)                      │
│  4. Detecta cambios (nuevo bill, nuevo movement, nuevo vote)    │
│  5. Dispara jobs de métricas y feed-generation                  │
└──────────┬────────────────────────┬─────────────────────────────┘
           │                        │
           ▼                        ▼
┌────────────────────┐  ┌────────────────────────────────────────┐
│  METRICS WORKER    │  │  FEED GENERATOR WORKER                  │
│  Calcula KPIs:     │  │  Crea feed_post por evento:             │
│  - bills_authored  │  │  - BILL_CREATED                         │
│  - bills_cosigned  │  │  - BILL_MOVEMENT                        │
│  - advancement_rate│  │  - VOTE_RESULT                          │
│  - attendance_pct  │  │  - ATTENDANCE_RECORD                    │
│  - vote_particip.  │  │  Cada post → source_ref linkado         │
│  Guarda en         │  │                                         │
│  legislator_metric │  │                                         │
└────────────────────┘  └─────────────────────────────────────────┘
           │                        │
           ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL                                  │
│  Tablas normalizadas + métricas + feed + social                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
           ┌───────────┼───────────┐
           ▼           ▼           ▼
┌────────────┐  ┌──────────┐  ┌──────────┐
│ Meilisearch│  │  Redis   │  │ Raw      │
│ (search    │  │ (cache + │  │ Storage  │
│  index)    │  │  queues) │  │ (fs/S3)  │
└────────────┘  └──────────┘  └──────────┘
           │           │
           ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      REST API (NestJS)                           │
│  /legislators  /bills  /feed  /comments  /reactions             │
│  /auth  /search  /reports                                       │
│  Rate limiting │ JWT Auth │ Swagger │ Structured logging        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│   Next.js Web    │    │  React Native    │
│   (SSR + CSR)    │    │  (Expo)          │
└──────────────────┘    └──────────────────┘
```

## 3. Flujo de Datos Detallado

### Ingesta (Cron: cada 6h + on-demand)
1. Scheduler dispara jobs por fuente configurada.
2. Source adapter descarga datos, calcula checksum.
3. Si checksum difiere del último → guarda raw + crea source_ref.
4. Si checksum igual → skip (idempotente).

### Normalización (Event-driven)
1. Toma raw payload, lo parsea según schema esperado.
2. Upsert: si el registro existe (por external_id), actualiza; si no, crea.
3. Para bills: detecta nuevos movements comparando con último known.
4. Emite eventos internos: BILL_CREATED, MOVEMENT_ADDED, VOTE_RECORDED.

### Métricas (Diario + por evento)
1. Job diario recalcula todas las métricas de cada legislator activo.
2. Job por evento recalcula solo el legislator afectado.
3. Métricas se guardan en tabla `legislator_metric` con período.

### Feed Generation (Por evento)
1. Por cada evento detectado, crea un `feed_post` con:
   - type (BILL_CREATED | BILL_MOVEMENT | VOTE_RESULT | ATTENDANCE)
   - entity_type + entity_id (para linking)
   - payload JSON (snapshot del evento)
   - source_ref_id (trazabilidad)
2. Los posts se indexan por fecha, tipo, bloque, provincia → queries eficientes.

## 4. Principios de Resiliencia

- **Idempotencia**: Cada job puede re-ejecutarse sin duplicar datos (upsert by external_id).
- **Reintentos**: BullMQ con backoff exponencial (3 intentos, 1m/5m/15m).
- **Dead Letter Queue**: Jobs fallidos van a DLQ para revisión manual.
- **Monitoreo**: Cada ingestion_run registra started_at, completed_at, records_processed, errors.
- **Alertas**: Sentry para errores, métricas de latencia de jobs en logs estructurados.
- **Source adapters desacoplados**: Cambiar formato de fuente = cambiar solo el adapter, no el pipeline.
