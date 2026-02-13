import { NextRequest, NextResponse } from 'next/server';
import { fetchProducts, fetchOrders, fetchInventoryLevels } from '@/lib/shopify';
import { getServiceSupabase } from '@/lib/supabase';

// POST /api/shopify/sync — Sync all Shopify data for a store
export async function POST(request: NextRequest) {
  try {
    const { store_id } = await request.json();
    if (!store_id) {
      return NextResponse.json({ error: 'store_id required' }, { status: 400 });
    }

    const db = getServiceSupabase();

    // 1. Get store credentials
    const { data: store, error: storeErr } = await db
      .from('stores')
      .select('*')
      .eq('id', store_id)
      .single();

    if (storeErr || !store) {
      return NextResponse.json({ error: 'Store not found' }, { status: 404 });
    }

    // 2. Mark as syncing
    await db.from('stores').update({ sync_status: 'syncing' as const }).eq('id', store_id);

    const config = { shopDomain: store.shop_domain, accessToken: store.access_token };

    // 3. Sync Products
    const shopifyProducts = await fetchProducts(config);
    let productsUpserted = 0;
    for (const p of shopifyProducts) {
      const mainVariant = p.variants[0];
      await db.from('products').upsert(
        {
          store_id,
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

    // 4. Sync Orders (last 12 months)
    const shopifyOrders = await fetchOrders(config, 12);
    let ordersUpserted = 0;
    for (const o of shopifyOrders) {
      await db.from('orders').upsert(
        {
          store_id,
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

    // 5. Sync Inventory Levels
    const inventoryLevels = await fetchInventoryLevels(config);
    let invUpserted = 0;
    for (const inv of inventoryLevels) {
      // Find matching product by inventory_item_id → variant
      await db.from('inventory').upsert(
        {
          store_id,
          variant_id: inv.inventory_item_id.toString(),
          quantity: inv.available ?? 0,
          location_id: inv.location_id.toString(),
          sku: null, // will be enriched from product variants
        },
        { onConflict: 'store_id,variant_id,location_id' }
      );
      invUpserted++;
    }

    // 6. Update store status
    await db.from('stores').update({
      sync_status: 'synced' as const,
      last_sync: new Date().toISOString(),
      products_count: productsUpserted,
      orders_count: ordersUpserted,
    }).eq('id', store_id);

    return NextResponse.json({
      success: true,
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
      const { store_id } = await request.clone().json();
      if (store_id) {
        const db = getServiceSupabase();
        await db.from('stores').update({ sync_status: 'error' as const }).eq('id', store_id);
      }
    } catch {}

    return NextResponse.json(
      { error: 'Sync failed', detail: (e as Error).message },
      { status: 500 }
    );
  }
}
