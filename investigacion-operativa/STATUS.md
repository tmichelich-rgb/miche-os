# invop.ai — Estado del Proyecto

**Actualizado:** 14 de Febrero de 2026
**Estado general:** Plataforma SaaS live en invop.ai con Shopify integration + AI Analysis + Module Chaining + Auto-Solve
**Dominio:** www.invop.ai (Vercel) | invop.ai redirect → www.invop.ai

---

## Resumen Ejecutivo

invop.ai es una plataforma SaaS de Investigación Operativa que permite resolver problemas reales de negocio usando lenguaje natural en español. Se diferencia de un LLM genérico en 3 ejes: certeza matemática (solvers reales), flujo guiado (detecta módulo, extrae variables, confirma, resuelve), y outputs accionables (gráficos, tablas, PDFs, exports).

El proyecto tiene dos capas principales:
- **Frontend SPA** (`app.html`, ~8,500+ líneas) — Landing, app conversacional, 7 solvers client-side, integración Shopify, module chaining, auto-solve
- **Backend Next.js** (`invop-platform/`) — API routes, OAuth Shopify, Supabase, Stripe, AI Analysis engine

---

## Arquitectura Actual

### Stack de Producción
| Componente | Tecnología | Estado |
|-----------|------------|--------|
| Frontend | Single-file HTML SPA (app.html) | LIVE |
| Backend/API | Next.js 14 (App Router) | LIVE |
| Hosting | Vercel | LIVE |
| Base de Datos | Supabase (PostgreSQL) | LIVE |
| Auth | Google Sign-In (OAuth 2.0) | LIVE |
| Pagos | Stripe (3 planes) | CONFIGURADO |
| E-commerce | Shopify App (OAuth + sync) | LIVE |
| Dominio | invop.ai (GoDaddy → Vercel) | LIVE |
| AI Analysis | Pure logic engine (sin Claude API) | LIVE |
| CRON_SECRET | Vercel env var para cron jobs | CONFIGURADO |

### Stack Legacy (no en producción)
| Componente | Tecnología | Estado |
|-----------|------------|--------|
| Backend Enterprise | FastAPI + PostgreSQL + Redis | COMPLETO, no deployado |
| Solvers server-side | OR-Tools GLOP + Gurobi opcional | COMPLETO, no deployado |

---

## Los 7 Módulos

| # | Módulo | Solver | Qué resuelve |
|---|--------|--------|-------------|
| 1 | Produccion | LP Simplex | ¿Qué fabricar, cuánto, con qué recursos? |
| 2 | Almacenamiento | EOQ | ¿Cuánto pedir y cada cuánto reponer? |
| 3 | Atencion | M/M/s Erlang | ¿Cuántos puestos necesito? |
| 4 | Planificacion | VAN/TIR/Payback | ¿Invierto en A o en B? |
| 5 | Pronosticos | Moving Avg/Exp Smooth/Regression | ¿Cuánto voy a vender? |
| 6 | Rentabilidad | Margen/Punto Eq/ABC | ¿Cuánto gano por producto? |
| 7 | Flujo de Caja | Cashflow projection + DSO/DPO | ¿Me alcanza la plata? |

---

## Features Diferenciales

### Module Chaining (nuevo — sesión 8-9)
Permite encadenar la salida de un solver como entrada del siguiente:
- FORECAST → STOCK (demanda pronosticada → demanda anual EOQ)
- FORECAST → FLUJO_CAJA (forecast mensual → ingreso estimado)
- STOCK → FLUJO_CAJA (CTE → costo inventario mensual)
- RENTABILIDAD → FLUJO_CAJA (revenue/costos → inflows/outflows)
- INVEST → FLUJO_CAJA (inversión + FCF → proyección cash flow)
- QUEUE → FLUJO_CAJA (servidores óptimos × costo → gasto personal)

Botones "🔗 Usar en →" aparecen después de resolver cada módulo. Badge muestra origen de datos.

### Shopify Auto-Solve (nuevo — sesión 9)
1 click resuelve TODOS los módulos con datos reales de Shopify:
- Botón "🚀 Auto-resolver" en panel Shopify
- Llama a `/api/ai/analyze`, mapea inputs, ejecuta los 4 solvers (FORECAST, STOCK, RENTABILIDAD, FLUJO_CAJA)
- Dashboard 2x2 con métricas clave: forecast $, EOQ unidades, margen %, balance final
- Click en cualquier card → resultado completo en chat con sensibilidad, chain, export

### DSO/DPO para Flujo de Caja (nuevo — sesión 8-9)
- NLP extrae plazos de cobro/pago ("cobro a 30 días", "pago a 60 días")
- Solver desfasa inflows/outflows según DSO/DPO
- Calcula CCC (Ciclo de Conversión de Caja) = DSO - DPO
- Campos opcionales en formulario estructurado
- Pregunta opcional en flujo conversacional (skip con "resolver")

### Structured Form Inputs (sesión 8)
Formularios alternativos al NLP para cada módulo con inputs estructurados (`.df-in` class).

---

## Shopify Integration

### Flujo completo (funcionando):
1. Usuario Pro → "Conectar Shopify" → ingresa `store.myshopify.com`
2. OAuth redirect a Shopify → usuario autoriza permisos
3. Callback: token exchange + inline sync de productos/órdenes/inventario a Supabase
4. App muestra stats (17 productos sincronizados en test store)
5. "Analizar con AI" → motor analiza datos, detecta faltantes, recomienda módulos
6. "🚀 Auto-resolver" → resuelve todos los módulos en 1 click

### Scopes: `read_products, read_orders, read_inventory, read_locations`
### App Version activa: `invop-v3-4`
### Redirect URL: `https://www.invop.ai/api/shopify/callback`

---

## AI Analysis Engine

Motor de análisis puro (sin dependencia de Claude API):
- Analiza productos, órdenes, inventario de Shopify
- Detecta datos faltantes (costos, holding cost %, ordering cost, fixed costs)
- Por cada módulo genera checklist: ✓ dato disponible / ✗ dato faltante
- Prioriza módulos (high/medium/low) según completitud de datos
- Permite input de costos vía formulario o carga de Excel/CSV (SheetJS)
- Botón verde "Resolver con datos completos" vs rojo "Resolver (resultado aproximado)"
- Botón "🚀 Auto-resolver todos los módulos" en el modal de análisis

---

## Planes y Monetización

| Plan | Precio | Límites |
|------|--------|---------|
| Free | $0 | 3 problemas por módulo |
| Starter | $3.99/mes | Ilimitado |
| Pro | $49.99/mes | Ilimitado + Shopify + AI Analysis |

### UX de conversión:
- Usuarios Free/Starter ven sección "Shopify + AI" en sidebar con lock overlay (blur + candado + botón "Upgrade a Pro")
- Usuarios Pro ven panel desbloqueado
- En modo embedded (Shopify admin) se desbloquea automáticamente

---

## Estructura del Proyecto

```
investigacion-operativa/
├── invop-platform/                    # ← PLATAFORMA NEXT.JS (producción)
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth/google/route.ts   # Google OAuth (acepta JWT + pre-parsed)
│   │   │   ├── shopify/
│   │   │   │   ├── auth/route.ts      # Shopify OAuth inicio
│   │   │   │   ├── callback/route.ts  # Shopify OAuth callback + sync
│   │   │   │   ├── sync/route.ts      # Sync periódico + manual
│   │   │   │   └── store-data/route.ts # GET datos de tienda
│   │   │   ├── ai/analyze/route.ts    # AI Analysis engine
│   │   │   ├── cron/sync/route.ts     # Cron sync (cada 6h, protegido por CRON_SECRET)
│   │   │   ├── webhooks/shopify/route.ts # Webhooks real-time
│   │   │   ├── debug/                 # Debug endpoints
│   │   │   ├── stripe/               # Webhooks y checkout
│   │   │   └── users/                # User management
│   │   ├── page.tsx                   # Home (redirect to /legacy/app.html)
│   │   └── layout.tsx
│   ├── lib/
│   │   ├── supabase.ts               # Supabase client
│   │   └── shopify.ts                # Shopify API client + OAuth helpers
│   ├── middleware.ts                  # CORS + CSP for Shopify iframe
│   ├── public/legacy/app.html         # ← SPA PRINCIPAL (~8,500+ LOC)
│   ├── .env.local                     # Variables de entorno (no en git)
│   ├── .env.local.example             # Template de env vars
│   └── SETUP.md                       # Guía de setup
├── optisolve/                         # Backend enterprise legacy (FastAPI)
├── STATUS.md                          # ← ESTE ARCHIVO
├── PROMPT_CONTINUACION.md             # Prompt para continuar sesiones
└── BIBLE.md                           # Biblia del producto
```

---

## DNS y Dominios

| Dominio | Tipo | Destino | Estado |
|---------|------|---------|--------|
| invop.ai | A | 216.150.1.1 (Vercel) | Redirect → www |
| www.invop.ai | CNAME | df6eec162613945d.vercel-dns-017.com | Production |
| miche-os.vercel.app | — | Vercel default | Production |

### Google OAuth origins autorizados:
- https://invop.ai
- https://www.invop.ai
- https://miche-os.vercel.app
- https://admin.shopify.com
- http://localhost

---

## Historial de Sesiones

### Sesiones 1-5 (previas)
- Construcción del SPA con 7 módulos y solvers client-side
- Backend enterprise FastAPI completo (4 fases)
- 153 tests automatizados

### Sesión 6 — 13 Feb 2026
- **Plataforma Next.js**: Creación de invop-platform/ con API routes
- **Supabase**: Setup completo con tablas users, stores, products, orders, inventory
- **Shopify App**: OAuth flow, callback con inline sync
- **Shopify debugging**: Debug endpoints, fix scope 403, versiones v3-3 y v3-4
- **17 productos sincronizados** desde test store

### Sesión 7 — 13-14 Feb 2026
- **AI Analysis engine**: Motor puro sin Claude API que analiza datos y recomienda módulos
- **UX del análisis**: Checklist ✓/✗ por módulo, botones color-coded, modal scrolleable
- **Excel upload**: Carga de costos vía Excel/CSV con SheetJS y auto-matching
- **Dominio invop.ai**: DNS GoDaddy → Vercel, 3 dominios validados
- **URLs actualizadas**: API_BASE, Vercel env vars, Shopify app URLs, Google OAuth origins
- **Pro lock overlay**: Sección Shopify+AI visible para todos con blur+lock para Free/Starter

### Sesión 8 — 14 Feb 2026
- **Bug fixes**: NLP robustness, Producción loop, Flujo de Caja re-asking, Rentabilidad "Zapatos y Botas", text overlap hero
- **Structured form inputs**: `.df-in` CSS + formularios RENTABILIDAD, FLUJO_CAJA, STOCK
- **Google Auth fix**: Frontend guardaba `{name, email, picture}` pero backend esperaba JWT `{credential}`. Arreglado ambos lados.
- **CRON_SECRET**: Generado y configurado en Vercel para proteger cron jobs

### Sesión 9 — 14 Feb 2026
- **DSO/DPO para Flujo de Caja**: NLP extraction, solver con desfase temporal, CCC, formulario, checkAndAsk opcional
- **Landing page upgrade**: Social proof bar, tabs interactivos para 7 módulos, mejor copy CTAs, eliminadas secciones redundantes (-44 líneas, -30% scroll)
- **Module Chaining**: 6 cadenas definidas, CHAIN_MAP con extract functions, startChain(), botones "🔗 Usar en →", badge de origen
- **Shopify Auto-Solve**: shopifyAutoSolveAll(), dashboard 2x2 con métricas, loadAutoSolveDetail(), botón "🚀 Auto-resolver" en panel + modal

---

## Pendientes

### Funcionalidad:
- [ ] Sensibilidad interactiva con sliders (post-solve)
- [ ] Monte Carlo / probabilístico (rangos de incertidumbre)
- [ ] Dashboard visual de escenarios guardados
- [ ] Shopify App Store submission (actualmente app privada/desarrollo)
- [ ] Onboarding Shopify — guiar automáticamente al análisis post-install

### Growth:
- [ ] Marketing: LinkedIn posts, demos, caso de uso e-commerce
- [ ] SEO: landing page optimizada para "investigación operativa online"
- [ ] Testimonios reales de usuarios

---

*Documento actualizado el 14 de Febrero de 2026.*
