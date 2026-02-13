import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

// GET /api/debug/store?shop=invop-ai-test.myshopify.com
export async function GET(request: NextRequest) {
  const shop = request.nextUrl.searchParams.get('shop');
  const db = getServiceSupabase();

  // Get store
  const { data: store, error: storeErr } = await db
    .from('stores')
    .select('*')
    .eq('shop_domain', shop || '')
    .single();

  if (storeErr || !store) {
    // Show all stores instead
    const { data: allStores } = await db.from('stores').select('id, shop_domain, sync_status, last_sync, products_count, orders_count, created_at');
    return NextResponse.json({ error: 'Store not found for domain', shop, all_stores: allStores });
  }

  // Get product count
  const { count: productCount } = await db
    .from('products')
    .select('*', { count: 'exact', head: true })
    .eq('store_id', store.id);

  // Get order count
  const { count: orderCount } = await db
    .from('orders')
    .select('*', { count: 'exact', head: true })
    .eq('store_id', store.id);

  // Get inventory count
  const { count: invCount } = await db
    .from('inventory')
    .select('*', { count: 'exact', head: true })
    .eq('store_id', store.id);

  return NextResponse.json({
    store: {
      id: store.id,
      shop_domain: store.shop_domain,
      sync_status: store.sync_status,
      last_sync: store.last_sync,
      products_count: store.products_count,
      orders_count: store.orders_count,
      has_access_token: !!store.access_token,
      access_token_preview: store.access_token ? store.access_token.substring(0, 8) + '...' : null,
      created_at: store.created_at,
    },
    actual_counts: {
      products: productCount,
      orders: orderCount,
      inventory: invCount,
    },
  });
}
