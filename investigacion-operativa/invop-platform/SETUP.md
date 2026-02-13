# INVOP.ai Platform — Setup Guide

## Lo que ya está listo
- Proyecto Next.js con TypeScript + Tailwind
- 12 API routes funcionando:
  - `/api/auth/google` — Login con Google
  - `/api/usage` — Control de uso (GET check + POST registro)
  - `/api/shopify/auth` — Inicio OAuth de Shopify
  - `/api/shopify/callback` — Callback OAuth de Shopify
  - `/api/shopify/sync` — Sync de products, orders, inventory
  - `/api/webhooks/shopify` — Webhooks en real-time de Shopify
  - `/api/ai/analyze` — Analisis AI con Claude de data de Shopify
  - `/api/stripe/checkout` — Crear session de checkout (3 planes)
  - `/api/stripe/webhook` — Manejar eventos de Stripe
  - `/api/cron/sync` — Re-sync automatico cada 6h
  - `/api/cron/reports` — Generar reportes semanales
- SPA actual copiada a `/public/legacy/app.html`
- Schema SQL listo para ejecutar en Supabase

---

## Paso 1: Supabase (ya tenés cuenta)

1. Creá un **nuevo proyecto** en https://supabase.com/dashboard
   - Nombre: `invop-platform`
   - Region: us-east-1 (o la que prefieras)
   - Password: generá una segura

2. Andá a **SQL Editor** y pegá todo el contenido de `supabase/schema.sql`
   - Click "Run" — esto crea todas las tablas

3. Copiá las keys de **Settings > API**:
   - `Project URL` → `NEXT_PUBLIC_SUPABASE_URL`
   - `anon public key` → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role key` → `SUPABASE_SERVICE_ROLE_KEY`

---

## Paso 2: Shopify Partners

1. Andá a https://partners.shopify.com/ y registrate (es gratis)

2. Creá una **App** nueva:
   - Nombre: "INVOP.ai — Business Intelligence"
   - App URL: `https://tu-dominio.vercel.app`
   - Allowed redirection URL(s): `https://tu-dominio.vercel.app/api/shopify/callback`

3. Copiá las keys:
   - `API key` → `SHOPIFY_API_KEY`
   - `API secret key` → `SHOPIFY_API_SECRET`

---

## Paso 3: Anthropic API (Claude)

1. Andá a https://console.anthropic.com/
2. Creá una API key
3. Copiá → `ANTHROPIC_API_KEY`

---

## Paso 4: Stripe (ya tenés cuenta)

1. En Stripe Dashboard, creá 2 **Products** con recurring pricing:
   - **INVOP Starter**: $3.99/month
   - **INVOP Pro**: $49.99/month

2. Copiá los Price IDs (empiezan con `price_`):
   - Starter → `STRIPE_PRICE_STARTER`
   - Pro → `STRIPE_PRICE_PRO`

3. En **Developers > Webhooks**, creá un endpoint:
   - URL: `https://tu-dominio.vercel.app/api/stripe/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copiá el Signing secret → `STRIPE_WEBHOOK_SECRET`

---

## Paso 5: Deploy en Vercel

1. Pusheá este directorio (`invop-platform/`) a un repo en GitHub

2. En Vercel, importá el repo

3. En **Settings > Environment Variables**, agregá TODAS las variables de `.env.local.example`

4. Deploy! Vercel hace el build automáticamente

---

## Paso 6: Conectar tu Shopify store de prueba

1. En Shopify Partners, creá una **Development store** (gratis)

2. Instalá la app: `https://tu-dominio.vercel.app/api/shopify/auth?shop=tu-store.myshopify.com`

3. Autorizá los permisos → se conecta automáticamente

4. Los datos se sincronizan y ya podés usar el AI analysis

---

## Estructura del Proyecto

```
invop-platform/
├── app/
│   ├── api/
│   │   ├── auth/google/route.ts      # Google OAuth
│   │   ├── usage/route.ts            # Usage tracking
│   │   ├── shopify/
│   │   │   ├── auth/route.ts         # Shopify OAuth start
│   │   │   ├── callback/route.ts     # Shopify OAuth callback
│   │   │   └── sync/route.ts         # Data sync engine
│   │   ├── webhooks/shopify/route.ts  # Shopify real-time webhooks
│   │   ├── ai/analyze/route.ts       # Claude AI analysis
│   │   ├── stripe/
│   │   │   ├── checkout/route.ts     # Stripe checkout
│   │   │   └── webhook/route.ts      # Stripe events
│   │   └── cron/
│   │       ├── sync/route.ts         # Auto re-sync (6h)
│   │       └── reports/route.ts      # Weekly reports
│   ├── layout.tsx
│   └── page.tsx                      # Redirects to SPA
├── lib/
│   ├── supabase.ts                   # DB client
│   ├── shopify.ts                    # Shopify API client
│   ├── stripe.ts                     # Stripe client
│   ├── anthropic.ts                  # Claude client
│   └── database.types.ts             # TypeScript types
├── public/legacy/
│   ├── app.html                      # Current SPA
│   └── admin.html                    # Current admin
├── supabase/
│   └── schema.sql                    # Full database schema
├── vercel.json                       # Cron config
└── .env.local.example                # All env vars needed
```
