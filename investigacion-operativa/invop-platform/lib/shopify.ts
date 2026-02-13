// ═══ Shopify API Client — INVOP.ai ═══

const SHOPIFY_API_VERSION = '2024-10';

interface ShopifyConfig {
  shopDomain: string;
  accessToken: string;
}

// Generic Shopify Admin API request
export async function shopifyFetch<T>(
  config: ShopifyConfig,
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `https://${config.shopDomain}/admin/api/${SHOPIFY_API_VERSION}/${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'X-Shopify-Access-Token': config.accessToken,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`Shopify API Error (${res.status}): ${error}`);
  }

  return res.json();
}

// ═══ Products ═══
export async function fetchProducts(config: ShopifyConfig, limit = 250) {
  const data = await shopifyFetch<{ products: ShopifyProduct[] }>(
    config,
    `products.json?limit=${limit}&fields=id,title,vendor,product_type,status,variants,tags,created_at`
  );
  return data.products;
}

// ═══ Orders (last 12 months) ═══
export async function fetchOrders(config: ShopifyConfig, months = 12) {
  const since = new Date();
  since.setMonth(since.getMonth() - months);
  const sinceISO = since.toISOString();

  let allOrders: ShopifyOrder[] = [];
  let url: string | null = `orders.json?limit=250&status=any&created_at_min=${sinceISO}&fields=id,order_number,total_price,subtotal_price,total_tax,total_discounts,currency,financial_status,fulfillment_status,line_items,customer,created_at`;

  while (url) {
    const data = await shopifyFetch<{ orders: ShopifyOrder[] }>(config, url);
    allOrders = allOrders.concat(data.orders);

    // Pagination — Shopify uses Link header but for simplicity we fetch max 250
    if (data.orders.length < 250) break;
    // TODO: implement cursor-based pagination for stores with >250 orders/month
    url = null;
  }

  return allOrders;
}

// ═══ Inventory Levels ═══
export async function fetchInventoryLevels(config: ShopifyConfig, locationId?: string) {
  // First get locations
  const locData = await shopifyFetch<{ locations: ShopifyLocation[] }>(
    config,
    'locations.json'
  );

  const locId = locationId || locData.locations[0]?.id?.toString();
  if (!locId) return [];

  const invData = await shopifyFetch<{ inventory_levels: ShopifyInventoryLevel[] }>(
    config,
    `inventory_levels.json?location_ids=${locId}&limit=250`
  );

  return invData.inventory_levels;
}

// ═══ Register Webhooks ═══
export async function registerWebhooks(config: ShopifyConfig, callbackBase: string) {
  const topics = [
    'orders/create',
    'orders/updated',
    'products/update',
    'products/delete',
    'inventory_levels/update',
    'app/uninstalled',
  ];

  const results = [];
  for (const topic of topics) {
    try {
      const res = await shopifyFetch<{ webhook: unknown }>(config, 'webhooks.json', {
        method: 'POST',
        body: JSON.stringify({
          webhook: {
            topic,
            address: `${callbackBase}/api/webhooks/shopify`,
            format: 'json',
          },
        }),
      });
      results.push({ topic, status: 'ok', data: res });
    } catch (e) {
      results.push({ topic, status: 'error', error: (e as Error).message });
    }
  }

  return results;
}

// ═══ OAuth Helpers ═══
export function buildShopifyAuthUrl(shop: string): string {
  const apiKey = process.env.SHOPIFY_API_KEY!;
  const scopes = process.env.SHOPIFY_SCOPES!;
  const redirectUri = `${process.env.NEXT_PUBLIC_SHOPIFY_APP_URL}/api/shopify/callback`;

  // Generate nonce for CSRF protection
  const nonce = crypto.randomUUID();

  return `https://${shop}/admin/oauth/authorize?client_id=${apiKey}&scope=${scopes}&redirect_uri=${encodeURIComponent(redirectUri)}&state=${nonce}`;
}

export async function exchangeCodeForToken(shop: string, code: string): Promise<string> {
  const res = await fetch(`https://${shop}/admin/oauth/access_token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: process.env.SHOPIFY_API_KEY!,
      client_secret: process.env.SHOPIFY_API_SECRET!,
      code,
    }),
  });

  if (!res.ok) {
    throw new Error(`Token exchange failed: ${await res.text()}`);
  }

  const data = await res.json();
  return data.access_token;
}

// ═══ Types ═══
export interface ShopifyProduct {
  id: number;
  title: string;
  vendor: string;
  product_type: string;
  status: string;
  variants: {
    id: number;
    title: string;
    price: string;
    compare_at_price: string | null;
    sku: string | null;
    inventory_quantity: number;
    cost?: string;
    weight?: number;
  }[];
  tags: string;
  created_at: string;
}

export interface ShopifyOrder {
  id: number;
  order_number: number;
  total_price: string;
  subtotal_price: string;
  total_tax: string;
  total_discounts: string;
  currency: string;
  financial_status: string;
  fulfillment_status: string | null;
  line_items: {
    product_id: number;
    variant_id: number;
    title: string;
    quantity: number;
    price: string;
    total_discount: string;
    sku: string | null;
  }[];
  customer?: { email: string };
  created_at: string;
}

export interface ShopifyLocation {
  id: number;
  name: string;
  active: boolean;
}

export interface ShopifyInventoryLevel {
  inventory_item_id: number;
  location_id: number;
  available: number;
  updated_at: string;
}
