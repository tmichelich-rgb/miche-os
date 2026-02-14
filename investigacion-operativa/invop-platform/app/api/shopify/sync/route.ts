import { NextRequest, NextResponse } from 'next/server';
import { fetchProducts, fetchOrders, fetchInventoryLevels } from '@/lib/shopify';
import { getServiceSupabase } from '@/lib/supabase';

// POST /api/shopify/sync — Sync all Shopify data for a store
// Accepts either:
//   { store_id: "uuid" }  — internal (from cron job)
//   { shop: "store.myshopify.com", email: "user@email.com" }  — from frontend re-sync
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const db = getServiceSupabase();

    let storeId: string;
    let store: Record<string, unknown> | null = null;

    if (body.store_id) {
      // Internal call (from cron) — direct store_id lookup
      storeId = body.store_id;
      const { data, error } = await db
        .from('stores')
        .select('*')
        .eq('id', storeId)
        .single();
      if (error || !data) {
        return NextResponse.json({ error: 'Store not found' }, { status: 404 });
      }
      store = data;
    } else if (body.shop && body.email) {
      // Frontend call — verify user owns this store
      const { data: user } = await db
        .from('users')
        .select('id')
        .eq('email', body.email)
        .single();

      if (!user) {
        return NextResponse.json({ error: 'User not found' }, { status: 403 });
      }

      const { data, error } = await db
        .from('stores')
        .select('*')
        .eq('shop_domain', body.shop)
        .eq('user_id', user.id)
        .single();

      if (error || !data) {
        return NextResponse.json({ error: 'Store not connected or not owned by user' }, { status: 404 });
      }
      store = data;
      storeId = (data as { id: string }).id;
    } else {
      return NextResponse.json({ error: 'store_id or (shop + email) required' }, { status: 400 });
    }

    // Rate limit: don't re-sync if last sync was less than 5 minutes ago
    const lastSync = (store as { last_sync?: string }).last_sync;
    if (lastSync && body.email) { // Only rate-limit user-triggered syncs
      const sinceLast = Date.now() - new Date(lastSync).getTime();
      if (sinceLast < 5 * 60 * 1000) {
        const minsAgo = Math.round(sinceLast / 60000);
        return NextResponse.json({
          error: 'rate_limited',
          message: `Último sync hace ${minsAgo} min. Esperá al menos 5 minutos.`,
          last_sync: lastSync,
        }, { status: 429 });
      }
    }

    // Mark as syncing
    await db.from('stores').update({ sync_status: 'syncing' as const }).eq('id', storeId);

    const config = {
      shopDomain: (store as { shop_domain: string }).shop_domain,
      accessToken: (store as { access_token: string }).access_token,
    };

    // Sync Products
    const shopifyProducts = await fetchProducts(config);
    let productsUpserted = 0;
    for (const p of shopifyProducts) {
      const mainVariant = p.variants[0];
      await db.from('products').upsert(
        {
          store_id: storeId,
          shopify_id: p.id.toString(),
          title: p.title,
          vendor: p.vendor || null,
          product_type: p.product_type || null,
          status: p.status,
          variants: p.variants.map((v) => ({
            id: v.id.toString(),
            title: v.title,
            price: parseFloat(v.price),
            compare_at_price: v.compare_at_price ? parseFloat(v.compare_at_price) : null,
            sku: v.sku,
            inventory_quantity: v.inventory_quantity,
            cost: v.cost ? parseFloat(v.cost) : null,
            weight: v.weight || null,
          })),
          tags: p.tags ? p.tags.split(',').map((t: string) => t.trim()) : [],
          cost_per_item: mainVariant?.cost ? parseFloat(mainVariant.cost) : null,
          price: mainVariant ? parseFloat(mainVariant.price) : null,
          inventory_quantity: p.variants.reduce(
            (sum: number, v: { inventory_quantity: number }) => sum + v.inventory_quantity,
            0
          ),
          created_at: p.created_at,
        },
        { onConflict: 'store_id,shopify_id' }
      );
      productsUpserted++;
    }

    // Sync Orders (last 12 months)
    const shopifyOrders = await fetchOrders(config, 12);
    let ordersUpserted = 0;
    for (const o of shopifyOrders) {
      await db.from('orders').upsert(
        {
          store_id: storeId,
          shopify_id: o.id.toString(),
          order_number: o.order_number,
          total_price: parseFloat(o.total_price),
          subtotal_price: parseFloat(o.subtotal_price),
          total_tax: parseFloat(o.total_tax),
          total_discounts: parseFloat(o.total_discounts),
          currency: o.currency,
          financial_status: o.financial_status,
          fulfillment_status: o.fulfillment_status,
          line_items: o.line_items.map((li) => ({
            product_id: li.product_id.toString(),
            variant_id: li.variant_id.toString(),
            title: li.title,
            quantity: li.quantity,
            price: parseFloat(li.price),
            total_discount: parseFloat(li.total_discount),
            sku: li.sku,
          })),
          customer_email: o.customer?.email || null,
          order_date: o.created_at,
        },
        { onConflict: 'store_id,shopify_id' }
      );
      ordersUpserted++;
    }

    // Sync Inventory Levels
    const inventoryLevels = await fetchInventoryLevels(config);
    let invUpserted = 0;
    for (const inv of inventoryLevels) {
      await db.from('inventory').upsert(
        {
          store_id: storeId,
          variant_id: inv.inventory_item_id.toString(),
          quantity: inv.available ?? 0,
          location_id: inv.location_id.toString(),
          sku: null,
        },
        { onConflict: 'store_id,variant_id,location_id' }
      );
      invUpserted++;
    }

    // Update store status
    const now = new Date().toISOString();
    await db.from('stores').update({
      sync_status: 'synced' as const,
      last_sync: now,
      products_count: productsUpserted,
      orders_count: ordersUpserted,
    }).eq('id', storeId);

    return NextResponse.json({
      success: true,
      last_sync: now,
      synced: {
        products: productsUpserted,
        orders: ordersUpserted,
        inventory: invUpserted,
      },
    });
  } catch (e) {
    console.error('[Shopify Sync Error]', e);

    // Mark store as error
    try {
      const body = await request.clone().json();
      const sid = body.store_id;
      if (sid) {
        const db = getServiceSupabase();
        await db.from('stores').update({ sync_status: 'error' as const }).eq('id', sid);
      }
    } catch { /* ignore */ }

    return NextResponse.json(
      { error: 'Sync failed', detail: (e as Error).message },
      { status: 500 }
    );
  }
}
