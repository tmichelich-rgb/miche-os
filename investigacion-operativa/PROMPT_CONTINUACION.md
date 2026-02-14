# INVOP.ai — Prompt de Continuacion (v5 — Module Chaining + Auto-Solve)

Copia todo lo que esta debajo de la linea y pegalo en la proxima conversacion.

---

## Que es invop.ai

**invop.ai** es el primer ingeniero industrial digital. Una plataforma SaaS que permite a usuarios sin formacion matematica resolver problemas reales de negocio usando lenguaje natural en espanol. Se diferencia de ChatGPT en 3 ejes:

1. **Certeza matematica** — Usa solvers reales (Simplex, EOQ, Erlang, VAN/TIR, regresion). Respuestas exactas, no aproximaciones.
2. **Flujo guiado** — Detecta modulo, extrae variables con NLP, confirma supuestos, resuelve paso a paso.
3. **Outputs accionables** — Graficos Chart.js, tablas de cashflow, analisis de sensibilidad, exports Excel.

---

## Arquitectura actual (Febrero 2026)

### Stack de produccion (TODO LIVE en www.invop.ai):
- **Frontend**: Single-file HTML SPA (`invop-platform/public/legacy/app.html`, ~8,500+ LOC)
- **Backend**: Next.js 14 App Router (`invop-platform/app/api/`)
- **Hosting**: Vercel (auto-deploy desde GitHub main)
- **Base de datos**: Supabase (PostgreSQL) — tablas: users, stores, products, orders, inventory
- **Auth**: Google Sign-In OAuth 2.0
- **Pagos**: Stripe (Free $0 / Starter $3.99 / Pro $49.99)
- **E-commerce**: Shopify App con OAuth + sync de productos/ordenes/inventario
- **AI Analysis**: Motor puro (sin Claude API) que analiza datos y recomienda modulos
- **Dominio**: invop.ai (GoDaddy) → Vercel (A record 216.150.1.1 + CNAME www)
- **CRON_SECRET**: Vercel env var para proteger cron jobs

### Los 7 Modulos:
| Modulo | Solver | Pregunta clave |
|--------|--------|---------------|
| Produccion | LP Simplex | Que fabricar, cuanto, con que recursos? |
| Almacenamiento | EOQ | Cuanto pedir y cada cuanto reponer? |
| Atencion | M/M/s Erlang | Cuantos puestos necesito? |
| Planificacion | VAN/TIR/Payback | Invierto en A o en B? |
| Pronosticos | Moving Avg/Exp Smooth/Regression | Cuanto voy a vender? |
| Rentabilidad | Margen/Punto Eq/ABC | Cuanto gano por producto? |
| Flujo de Caja | Cashflow projection + DSO/DPO | Me alcanza la plata? |

---

## Features Diferenciales

### Module Chaining (sesion 8-9)
Permite encadenar la salida de un solver como entrada del siguiente:
- FORECAST → STOCK (demanda pronosticada → demanda anual EOQ)
- FORECAST → FLUJO_CAJA (forecast mensual → ingreso estimado)
- STOCK → FLUJO_CAJA (CTE → costo inventario mensual)
- RENTABILIDAD → FLUJO_CAJA (revenue/costos → inflows/outflows)
- INVEST → FLUJO_CAJA (inversion + FCF → proyeccion cash flow)
- QUEUE → FLUJO_CAJA (servidores optimos x costo → gasto personal)

**Implementacion:** CHAIN_MAP con extract functions por cadena. Botones "🔗 Usar en →" aparecen post-solve. Badge muestra origen de datos. checkAndAsk() wrappea _checkAndAskInner() para prepend chain badge.

### Shopify Auto-Solve (sesion 9)
1 click resuelve TODOS los modulos con datos reales de Shopify:
- Boton "🚀 Auto-resolver" en panel Shopify + modal de analisis
- Llama a `/api/ai/analyze`, mapea inputs con `mapAIInputsToParams()`, ejecuta SOLVERS client-side
- Dashboard 2x2 con metricas clave: forecast $, EOQ unidades, margen %, balance final
- Click en cualquier card → resultado completo en chat con sensibilidad, chain, export

**Funciones clave:** `shopifyAutoSolveAll()`, `_executeAutoSolve()`, `mapAIInputsToParams()`, `renderAutoSolveDashboard()`, `loadAutoSolveDetail()`

### DSO/DPO para Flujo de Caja (sesion 8-9)
- NLP extrae plazos de cobro/pago ("cobro a 30 dias", "pago a 60 dias")
- Solver desfasa inflows/outflows segun DSO/DPO
- Calcula CCC (Ciclo de Conversion de Caja) = DSO - DPO
- Campos opcionales en formulario estructurado + pregunta opcional en flujo conversacional
- Params `dso` y `dpo` inicializados en 4 code paths (menu "7", detectMod, confirm→collect, collect handler)

### Structured Form Inputs (sesion 8)
Formularios alternativos al NLP para cada modulo con inputs estructurados (`.df-in` class).

---

## Estructura del proyecto

```
investigacion-operativa/
├── invop-platform/                         # PLATAFORMA NEXT.JS (produccion)
│   ├── app/api/
│   │   ├── auth/google/route.ts            # Google OAuth (acepta JWT + pre-parsed)
│   │   ├── shopify/auth/route.ts           # Shopify OAuth inicio
│   │   ├── shopify/callback/route.ts       # OAuth callback + inline sync
│   │   ├── shopify/sync/route.ts           # Sync periodico + manual
│   │   ├── shopify/store-data/route.ts     # GET datos de tienda
│   │   ├── ai/analyze/route.ts             # AI Analysis engine
│   │   ├── cron/sync/route.ts              # Cron sync (cada 6h, protegido por CRON_SECRET)
│   │   ├── webhooks/shopify/route.ts       # Webhooks real-time
│   │   ├── debug/                          # Debug endpoints
│   │   ├── stripe/                         # Webhooks y checkout
│   │   └── users/                          # User management
│   ├── lib/supabase.ts                     # Supabase client
│   ├── lib/shopify.ts                      # Shopify API + OAuth helpers
│   ├── middleware.ts                        # CORS + CSP (Shopify iframe)
│   ├── public/legacy/app.html              # ← SPA PRINCIPAL (~8,500+ LOC)
│   └── .env.local.example                  # Template env vars
├── optisolve/                              # Backend enterprise legacy (FastAPI, no deployado)
├── STATUS.md                               # Estado completo del proyecto
├── PROMPT_CONTINUACION.md                  # Este archivo
└── BIBLE.md                                # Biblia del producto
```

---

## Shopify Integration (funcionando)

Flujo completo:
1. Usuario Pro → sidebar "Conectar Shopify" → ingresa store.myshopify.com
2. OAuth redirect → usuario autoriza en Shopify
3. Callback: token exchange + sync inline de productos/ordenes/inventario a Supabase
4. App muestra stats (17 productos sincronizados en test store invop-ai-test.myshopify.com)
5. "Analizar con AI" → motor analiza, genera checklist por modulo, detecta datos faltantes
6. "🚀 Auto-resolver" → resuelve todos los modulos en 1 click con dashboard de resultados

**Config Shopify:**
- App: INVOP v3, version activa: invop-v3-4
- Scopes: read_products, read_orders, read_inventory, read_locations
- App URL: https://www.invop.ai/legacy/app.html
- Redirect URL: https://www.invop.ai/api/shopify/callback
- Embedded: true (funciona dentro de Shopify admin)

**AI Analysis engine** (`/api/ai/analyze`):
- NO usa Claude API — es logica pura
- Detecta datos faltantes: costos, holding cost %, ordering cost, fixed costs
- Checklist por modulo: check verde = dato disponible, cruz roja = faltante
- Boton verde "Resolver con datos completos" vs rojo "Resolver (resultado aproximado)"
- Upload Excel/CSV para costos (SheetJS, auto-matching por nombre de producto)
- Boton "🚀 Auto-resolver todos los modulos" en el modal de analisis

---

## Planes y UX de conversion

| Plan | Precio | Features |
|------|--------|----------|
| Free | $0 | 3 problemas por modulo |
| Starter | $3.99/mes | Ilimitado |
| Pro | $49.99/mes | Ilimitado + Shopify + AI Analysis |

- Free/Starter: ven seccion "Shopify + AI" en sidebar con lock overlay (blur + candado + boton "Upgrade a Pro")
- Pro: panel desbloqueado completo
- Shopify embedded: se desbloquea automaticamente

---

## Variables de entorno clave (Vercel)

```
NEXT_PUBLIC_SUPABASE_URL=https://[project].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SHOPIFY_API_KEY=...
SHOPIFY_API_SECRET=...
NEXT_PUBLIC_SHOPIFY_APP_URL=https://www.invop.ai
SHOPIFY_SCOPES=read_products,read_orders,read_inventory,read_customers,read_analytics
NEXT_PUBLIC_GOOGLE_CLIENT_ID=759483082155-gf5uqdlf9kee6jo6dts46eu7lesdmcsu.apps.googleusercontent.com
NEXT_PUBLIC_APP_URL=https://invop.ai
CRON_SECRET=... (en Vercel env vars)
```

---

## Lo que hicimos en las ultimas sesiones (14 Feb 2026)

### Sesion 8:
1. **Bug fixes**: NLP robustness, Produccion loop, Flujo de Caja re-asking, Rentabilidad "Zapatos y Botas", text overlap hero
2. **Structured form inputs**: `.df-in` CSS + formularios RENTABILIDAD, FLUJO_CAJA, STOCK
3. **Google Auth fix**: Frontend guardaba `{name, email, picture}` pero backend esperaba JWT `{credential}`. Arreglado ambos lados.
4. **CRON_SECRET**: Generado y configurado en Vercel para proteger cron jobs
5. **Landing page upgrade**: Social proof bar, tabs interactivos para 7 modulos, mejor copy CTAs, eliminadas secciones redundantes

### Sesion 9:
1. **DSO/DPO para Flujo de Caja**: NLP extraction, solver con desfase temporal, CCC, formulario, checkAndAsk opcional. Params inicializados en 4 code paths.
2. **Module Chaining**: CHAIN_MAP con 6 cadenas + extract functions, startChain(), botones "🔗 Usar en →", badge de origen, wrapper checkAndAsk → _checkAndAskInner.
3. **Shopify Auto-Solve**: shopifyAutoSolveAll(), _executeAutoSolve(), mapAIInputsToParams(), renderAutoSolveDashboard() con grid 2x2, loadAutoSolveDetail(), boton en panel Shopify + modal.

**Commits pusheados (todos en main, deployados en Vercel):**
- `feat: DSO/DPO para Flujo de Caja — plazos de cobro y pago` (77+, 8-)
- `feat: module chaining — connect solver outputs to next solver inputs` (94+)
- `feat: Shopify Auto-Solve — 1-click resolve all modules` (195+, 1-)

---

## Pendientes inmediatos (para la proxima sesion)

### Funcionalidad:
1. **Sensibilidad interactiva con sliders** — Post-solve, sliders para variar parametros y ver impacto en tiempo real
2. **Monte Carlo / probabilistico** — Rangos de incertidumbre en vez de valores fijos
3. **Dashboard visual de escenarios guardados** — Guardar y comparar multiples resoluciones
4. **Shopify App Store submission** — Actualmente app privada/desarrollo. Necesita revision de Shopify.
5. **Onboarding Shopify** — Guiar automaticamente al analisis post-install

### Growth:
6. **Marketing**: LinkedIn posts, demos, caso de uso e-commerce
7. **SEO**: Landing page optimizada para "investigacion operativa online"
8. **Testimonios reales de usuarios**

---

## Contexto importante

- **Siempre que me des comandos, asumi que no se nada de codigo y dame el paso a paso completo.**
- El archivo principal de la app es `invop-platform/public/legacy/app.html` (~8,500+ LOC)
- El deploy es automatico: push a main → Vercel rebuilds
- Para testear Shopify usamos la tienda invop-ai-test.myshopify.com
- El email del usuario es tmichelich@gmail.com
- La app funciona tanto standalone (invop.ai) como embedded en Shopify admin
- Module chaining usa CHAIN_MAP (despues del objeto SOLVERS, ~linea 2198)
- Auto-solve funciones estan antes del console.log final (~linea 8748)
- checkAndAsk() es un wrapper de _checkAndAskInner() para el badge de chain

---

Empecemos por lo que necesites.
