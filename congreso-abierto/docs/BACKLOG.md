# Congreso Abierto — Backlog MVP (Semanas 1-4)

## Semana 1: Fundación
- [x] Definir stack y arquitectura
- [x] Diseñar esquema de base de datos (Prisma)
- [x] Configurar docker-compose (Postgres + Redis + Meilisearch)
- [x] Scaffold backend NestJS con Fastify
- [x] Implementar PrismaService + módulo global
- [x] Crear fixtures con datos ficticios pero realistas
- [x] Implementar seed script
- [ ] Configurar CI básico (lint + test)

## Semana 2: Pipeline + API Core
- [x] Implementar IngestWorker con source adapters
- [x] Implementar NormalizeWorker (legislators, bills, votes, attendance)
- [x] Implementar MetricsWorker (cálculo de KPIs)
- [x] Implementar FeedGeneratorWorker
- [x] API: GET /legislators (listado + filtros)
- [x] API: GET /legislators/:id (perfil con KPIs)
- [x] API: GET /bills (listado + filtros)
- [x] API: GET /bills/:id (detalle con movimientos)
- [x] API: GET /feed (feed con filtros)
- [ ] Conectar primer source adapter real (CKAN HCDN)
- [ ] Unit tests para parsers (fixtures)
- [ ] Integration tests para endpoints principales

## Semana 3: Social + Frontend
- [x] API: POST/GET /comments (CRUD + threading)
- [x] API: POST/GET /reactions (toggle + counts)
- [x] API: POST /comments/:id/report (reportar)
- [x] Moderación: auto-hide por umbral de reportes + strikes
- [x] Frontend: Home feed con filtros
- [x] Frontend: Perfil de diputado con KPIs
- [x] Frontend: Ficha de proyecto con historial
- [x] Frontend: Explorer / buscador
- [x] Frontend: Módulo "Cómo funciona"
- [ ] Auth: magic link + OAuth Google
- [ ] Rate limiting en endpoints sociales

## Semana 4: Pulido + Deploy
- [ ] Conectar al menos 2 fuentes reales del HCDN
- [ ] Meilisearch: indexación automática post-normalización
- [ ] Anti-brigading: detección de picos
- [ ] Observabilidad: Sentry + logs estructurados
- [ ] Mobile: Scaffold React Native (Expo) con pantallas básicas
- [ ] Deploy staging (Railway / Fly.io / similar)
- [ ] Testing end-to-end del pipeline completo
- [ ] Documentación de API (Swagger completo)
- [ ] README final con contribución

## Fase 2 (Post-MVP)
- Senado (segunda cámara)
- GraphQL API
- Notificaciones push
- Comparador de diputados
- Análisis por bloque/provincia
- Dashboard de asesores (si hay datos públicos)
- Machine learning: clasificación temática de proyectos
