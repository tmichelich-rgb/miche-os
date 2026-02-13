import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

// GET /api/shopify/store-data?shop=xxx.myshopify.com
// Returns store products, orders summary, and inventory for the embedded app
export async function GET(request: NextRequest) {
  const shop = request.nextUrl.searchParams.get('shop');

  if (!shop) {
    return NextResponse.json({ error: 'shop parameter required' }, { status: 400 });
  }

  try {
    const db = getServiceSupabase();

    // Find store by domain
    const { data: store, error: storeErr } = await db
      .from('stores')
      .select('*')
      .eq('shop_domain', shop)
      .single();

    if (storeErr || !store) {
      return NextResponse.json({
        connected: false,
        error: 'Store not connected yet',
        needs_sync: true,
      });
    }

    // Get products
    const { data: products } = await db
      .from('products')
      .select('shopify_id, title, vendor, product_type, status, price, cost_per_item, inventory_quantity, variants')
      .eq('store_id', store.id)
      .order('title');

    // Get recent orders summary
    const { data: orders } = await db
      .from('orders')
      .select('shopify_id, order_number, total_price, subtotal_price, currency, financial_status, line_items, order_date')
      .eq('store_id', store.id)
      .order('order_date', { ascending: false })
      .limit(100);

    // Get inventory
    const { data: inventory } = await db
      .from('inventory')
      .select('variant_id, sku, quantity, location_id')
      .eq('store_id', store.id);

    return NextResponse.json({
      connected: true,
      store: {
        id: store.id,
        shop_domain: store.shop_domain,
        sync_status: store.sync_status,
        last_sync: store.last_sync,
        products_count: store.products_count,
        orders_count: store.orders_count,
      },
      products: products || [],
      orders: orders || [],
      inventory: inventory || [],
    });
  } catch (e) {
    console.error('[Store Data Error]', e);
    return NextResponse.json(
      { error: 'Failed to fetch store data', detail: (e as Error).message },
      { status: 500 }
    );
  }
}
