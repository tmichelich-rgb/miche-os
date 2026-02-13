-- ═══════════════════════════════════════════════════════════
-- INVOP.ai — Supabase Schema
-- Run this in the Supabase SQL Editor to create all tables
-- ═══════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══ ENUMS ═══
CREATE TYPE plan_type AS ENUM ('free', 'starter', 'pro');
CREATE TYPE sync_status AS ENUM ('pending', 'syncing', 'synced', 'error');
CREATE TYPE report_type AS ENUM ('weekly', 'monthly', 'stock_alert', 'custom');
CREATE TYPE notif_channel AS ENUM ('email', 'in_app');
CREATE TYPE module_type AS ENUM ('LP', 'STOCK', 'QUEUE', 'INVEST', 'FORECAST', 'RENTABILIDAD', 'FLUJO_CAJA');
CREATE TYPE analysis_source AS ENUM ('manual', 'shopify_auto', 'shopify_manual');

-- ═══ USERS ═══
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  picture TEXT,
  plan plan_type DEFAULT 'free',
  plan_since TIMESTAMPTZ,
  stripe_customer_id TEXT,
  fingerprint TEXT,
  solve_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_stripe ON users(stripe_customer_id);

-- ═══ SHOPIFY STORES ═══
CREATE TABLE stores (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  shop_domain TEXT NOT NULL UNIQUE,
  access_token TEXT NOT NULL,
  scopes TEXT DEFAULT '',
  sync_status sync_status DEFAULT 'pending',
  last_sync TIMESTAMPTZ,
  products_count INT DEFAULT 0,
  orders_count INT DEFAULT 0,
  installed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stores_user ON stores(user_id);
CREATE INDEX idx_stores_domain ON stores(shop_domain);

-- ═══ SYNCED PRODUCTS ═══
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  shopify_id TEXT NOT NULL,
  title TEXT NOT NULL,
  vendor TEXT,
  product_type TEXT,
  status TEXT DEFAULT 'active',
  variants JSONB DEFAULT '[]',
  tags TEXT[] DEFAULT '{}',
  cost_per_item NUMERIC(12,2),
  price NUMERIC(12,2),
  inventory_quantity INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  synced_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_id, shopify_id)
);

CREATE INDEX idx_products_store ON products(store_id);
CREATE INDEX idx_products_shopify ON products(store_id, shopify_id);

-- ═══ SYNCED ORDERS ═══
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  shopify_id TEXT NOT NULL,
  order_number INT,
  total_price NUMERIC(12,2) NOT NULL,
  subtotal_price NUMERIC(12,2),
  total_tax NUMERIC(12,2) DEFAULT 0,
  total_discounts NUMERIC(12,2) DEFAULT 0,
  currency TEXT DEFAULT 'USD',
  financial_status TEXT,
  fulfillment_status TEXT,
  line_items JSONB DEFAULT '[]',
  customer_email TEXT,
  order_date TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  synced_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_id, shopify_id)
);

CREATE INDEX idx_orders_store ON orders(store_id);
CREATE INDEX idx_orders_date ON orders(store_id, order_date DESC);
CREATE INDEX idx_orders_shopify ON orders(store_id, shopify_id);

-- ═══ INVENTORY LEVELS ═══
CREATE TABLE inventory (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  variant_id TEXT NOT NULL,
  sku TEXT,
  quantity INT DEFAULT 0,
  location_id TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_id, variant_id, location_id)
);

CREATE INDEX idx_inventory_store ON inventory(store_id);
CREATE INDEX idx_inventory_product ON inventory(product_id);

-- ═══ ANALYSES (solve results) ═══
CREATE TABLE analyses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  store_id UUID REFERENCES stores(id) ON DELETE SET NULL,
  module module_type NOT NULL,
  input_data JSONB NOT NULL DEFAULT '{}',
  output_data JSONB NOT NULL DEFAULT '{}',
  ai_insights TEXT,
  source analysis_source DEFAULT 'manual',
  solve_time_ms INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analyses_user ON analyses(user_id);
CREATE INDEX idx_analyses_store ON analyses(store_id);
CREATE INDEX idx_analyses_module ON analyses(module);
CREATE INDEX idx_analyses_created ON analyses(created_at DESC);

-- ═══ SCHEDULED REPORTS ═══
CREATE TABLE reports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type report_type DEFAULT 'weekly',
  modules module_type[] DEFAULT '{}',
  schedule_cron TEXT,
  config JSONB DEFAULT '{}',
  last_run TIMESTAMPTZ,
  next_run TIMESTAMPTZ,
  enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reports_user ON reports(user_id);
CREATE INDEX idx_reports_next ON reports(next_run) WHERE enabled = true;

-- ═══ NOTIFICATIONS ═══
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  channel notif_channel DEFAULT 'in_app',
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  data JSONB,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  read_at TIMESTAMPTZ
);

CREATE INDEX idx_notifs_user ON notifications(user_id);
CREATE INDEX idx_notifs_unread ON notifications(user_id) WHERE read_at IS NULL;

-- ═══ ROW LEVEL SECURITY ═══
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Users can read/update their own data
CREATE POLICY "Users can view own data" ON users FOR SELECT USING (true);
CREATE POLICY "Users can update own data" ON users FOR UPDATE USING (email = current_setting('request.jwt.claims')::json->>'email');

-- Store data visible to store owner
CREATE POLICY "Store owner access" ON stores FOR ALL USING (user_id IN (SELECT id FROM users WHERE email = current_setting('request.jwt.claims')::json->>'email'));

-- Products/Orders/Inventory visible to store owner
CREATE POLICY "Products store owner" ON products FOR ALL USING (store_id IN (SELECT id FROM stores WHERE user_id IN (SELECT id FROM users WHERE email = current_setting('request.jwt.claims')::json->>'email')));
CREATE POLICY "Orders store owner" ON orders FOR ALL USING (store_id IN (SELECT id FROM stores WHERE user_id IN (SELECT id FROM users WHERE email = current_setting('request.jwt.claims')::json->>'email')));
CREATE POLICY "Inventory store owner" ON inventory FOR ALL USING (store_id IN (SELECT id FROM stores WHERE user_id IN (SELECT id FROM users WHERE email = current_setting('request.jwt.claims')::json->>'email')));

-- Analyses visible to owner
CREATE POLICY "Analyses owner" ON analyses FOR ALL USING (user_id IN (SELECT id FROM users WHERE email = current_setting('request.jwt.claims')::json->>'email'));

-- Reports visible to owner
CREATE POLICY "Reports owner" ON reports FOR ALL USING (user_id IN (SELECT id FROM users WHERE email = current_setting('request.jwt.claims')::json->>'email'));

-- Notifications visible to owner
CREATE POLICY "Notifs owner" ON notifications FOR ALL USING (user_id IN (SELECT id FROM users WHERE email = current_setting('request.jwt.claims')::json->>'email'));

-- ═══ HELPER FUNCTIONS ═══

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Increment solve count
CREATE OR REPLACE FUNCTION increment_solve_count(user_email TEXT)
RETURNS void AS $$
BEGIN
  UPDATE users SET solve_count = solve_count + 1 WHERE email = user_email;
END;
$$ LANGUAGE plpgsql;
