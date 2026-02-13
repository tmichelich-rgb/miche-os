import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';
import crypto from 'crypto';

// POST /api/webhooks/shopify — Handle incoming Shopify webhooks
export async function POST(request: NextRequest) {
  try {
    const body = await request.text();
    const shopDomain = request.headers.get('x-shopify-shop-domain');
    const topic = request.headers.get('x-shopify-topic');
    const hmac = request.headers.get('x-shopify-hmac-sha256');

    // 1. Verify webhook authenticity
    if (!verifyWebhook(body, hmac)) {
      return NextResponse.json({ error: 'Invalid HMAC' }, { status: 401 });
    }

    if (!shopDomain || !topic) {
      return NextResponse.json({ error: 'Missing headers' }, { status: 400 });
    }

    const data = JSON.parse(body);
    const db = getServiceSupabase();

    // 2. Find store
    const { data: store } = await db
      .from('stores')
      .select('id')
      .eq('shop_domain', shopDomain)
      .single();

    if (!store) {
      console.warn('[Webhook] Store not found:', shopDomain);
      return NextResponse.json({ ok: true }); // Ack anyway
    }

    // 3. Handle by topic
    switch (topic) {
      case 'orders/create':
      case 'orders/updated':
        await handleOrderWebhook(db, store.id, data);
        break;

      case 'products/update':
        await handleProductWebhook(db, store.id, data);
        break;

      case 'products/delete':
        await db.from('products')
          .delete()
          .eq('store_id', store.id)
          .eq('shopify_id', data.id.toString());
        break;

      case 'inventory_levels/update':
        await handleInventoryWebhook(db, store.id, data);
        break;

      case 'app/uninstalled':
        await db.from('stores').delete().eq('shop_domain', shopDomain);
        break;

      default:
        console.log('[Webhook] Unhandled topic:', topic);
    }

    return NextResponse.json({ ok: true });
  } catch (e) {
    console.error('[Webhook Error]', e);
    return NextResponse.json({ ok: true }); // Always 200 to prevent retries
  }
}

// ═══ Helpers ═══

function verifyWebhook(body: string, hmac: string | null): boolean {
  if (!hmac || !process.env.SHOPIFY_API_SECRET) return false;
  const computed = crypto
    .createHmac('sha256', process.env.SHOPIFY_API_SECRET)
    .update(body, 'utf8')
    .digest('base64');
  return crypto.timingSafeEqual(Buffer.from(computed), Buffer.from(hmac));
}

async function handleOrderWebhook(db: ReturnType<typeof getServiceSupabase>, storeId: string, order: Record<string, unknown>) {
  await db.from('orders').upsert(
    {
      store_id: storeId,
      shopify_id: String(order.id),
      order_number: Number(order.order_number),
      total_price: parseFloat(String(order.total_price)),
      subtotal_price: parseFloat(String(order.subtotal_price)),
      total_tax: parseFloat(String(order.total_tax || '0')),
      total_discounts: parseFloat(String(order.total_discounts || '0')),
      currency: String(order.currency || 'USD'),
      financial_status: String(order.financial_status),
      fulfillment_status: order.fulfillment_status ? String(order.fulfillment_status) : null,
      line_items: (order.line_items as unknown[]) || [],
      customer_email: (order.customer as { email?: string })?.email || null,
      order_date: String(order.created_at),
    },
    { onConflict: 'store_id,shopify_id' }
  );
}

async function handleProductWebhook(db: ReturnType<typeof getServiceSupabase>, storeId: string, product: Record<string, unknown>) {
  const variants = product.variants as { id: number; title: string; price: string; compare_at_price: string | null; sku: string | null; inventory_quantity: number; cost?: string; weight?: number }[];
  const mainV = variants?.[0];

  await db.from('products').upsert(
    {
      store_id: storeId,
      shopify_id: String(product.id),
      title: String(product.title),
      vendor: product.vendor ? String(product.vendor) : null,
      product_type: product.product_type ? String(product.product_type) : null,
      status: String(product.status || 'active'),
      variants: variants?.map((v) => ({
        id: String(v.id),
        title: v.title,
        price: parseFloat(v.price),
        compare_at_price: v.compare_at_price ? parseFloat(v.compare_at_price) : null,
        sku: v.sku,
        inventory_quantity: v.inventory_quantity,
        cost: v.cost ? parseFloat(v.cost) : null,
        weight: v.weight || null,
      })) || [],
      tags: typeof product.tags === 'string' ? product.tags.split(',').map((t: string) => t.trim()) : [],
      cost_per_item: mainV?.cost ? parseFloat(mainV.cost) : null,
      price: mainV ? parseFloat(mainV.price) : null,
      inventory_quantity: variants?.reduce((sum, v) => sum + v.inventory_quantity, 0) || 0,
      created_at: String(product.created_at),
    },
    { onConflict: 'store_id,shopify_id' }
  );
}

async function handleInventoryWebhook(db: ReturnType<typeof getServiceSupabase>, storeId: string, data: Record<string, unknown>) {
  await db.from('inventory').upsert(
    {
      store_id: storeId,
      variant_id: String(data.inventory_item_id),
      quantity: Number(data.available ?? 0),
      location_id: String(data.location_id),
    },
    { onConflict: 'store_id,variant_id,location_id' }
  );
}
