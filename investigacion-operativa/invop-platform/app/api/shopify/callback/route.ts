import { NextRequest, NextResponse } from 'next/server';
import { exchangeCodeForToken, registerWebhooks, fetchProducts, fetchOrders, fetchInventoryLevels } from '@/lib/shopify';
import { getServiceSupabase } from '@/lib/supabase';

// GET /api/shopify/callback?code=xxx&shop=xxx&state=xxx
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get('code');
  const shop = searchParams.get('shop');
  const state = searchParams.get('state') || '';

  // Decode email from state param (format: "nonce:base64email" or just "nonce")
  let userEmail: string | null = null;
  if (state.includes(':')) {
    try {
      const base64Email = state.split(':').slice(1).join(':');
      userEmail = Buffer.from(base64Email, 'base64').toString('utf-8');
    } catch { /* ignore decode errors */ }
  }

  if (!code || !shop) {
    return NextResponse.redirect(
      `${process.env.NEXT_PUBLIC_SHOPIFY_APP_URL}/legacy/app.html?shopify_error=missing_params`
    );
  }

  try {
    // 1. Exchange code for permanent access token
    const accessToken = await exchangeCodeForToken(shop, code);

    // 2. Store connection in Supabase
    const db = getServiceSupabase();

    // Find user by email decoded from OAuth state
    let userId: string | null = null;
    if (userEmail) {
      const { data: user } = await db
        .from('users')
        .select('id')
        .eq('email', userEmail)
        .single();
      userId = user?.id || null;
    }

    // Fallback: if no email in state, try to find the most recent pro user
    if (!userId) {
      const { data: user } = await db
        .from('users')
        .select('id')
        .eq('plan', 'pro')
        .order('created_at', { ascending: false })
        .limit(1)
        .single();
      userId = user?.id || null;
    }

    if (!userId) {
      return NextResponse.redirect(
        `${process.env.NEXT_PUBLIC_SHOPIFY_APP_URL}/legacy/app.html?shopify_error=no_user`
      );
    }

    // Upsert store connection
    const { data: store, error } = await db
      .from('stores')
      .upsert(
        {
          user_id: userId,
          shop_domain: shop,
          access_token: accessToken,
          scopes: process.env.SHOPIFY_SCOPES || '',
          sync_status: 'pending' as const,
        },
        { onConflict: 'shop_domain' }
      )
      .select()
      .single();

    if (error) throw error;

    // 3. Register Shopify webhooks (non-blocking, ok if fails)
    const callbackBase = process.env.NEXT_PUBLIC_SHOPIFY_APP_URL!;
    try {
      await registerWebhooks({ shopDomain: shop, accessToken }, callbackBase);
    } catch (webhookErr) {
      console.error('[Webhook Registration Warning]', webhookErr);
    }

    // 4. Sync data INLINE instead of fire-and-forget
    const shopifyConfig = { shopDomain: shop, accessToken };
    let productsCount = 0;
    let ordersCount = 0;
    try {
      // Sync products
      const products = await fetchProducts(shopifyConfig);
      productsCount = products.length;
      for (const p of products) {
        const mainVariant = p.variants[0];
        await db.from('products').upsert(
          {
            store_id: store.id,
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
      }

      // Sync orders
      const orders = await fetchOrders(shopifyConfig, 12);
      ordersCount = orders.length;
      for (const o of orders) {
        await db.from('orders').upsert(
          {
            store_id: store.id,
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
      }

      // Sync inventory
      const inventory = await fetchInventoryLevels(shopifyConfig);
      for (const inv of inventory) {
        await db.from('inventory').upsert(
          {
            store_id: store.id,
            variant_id: inv.inventory_item_id.toString(),
            quantity: inv.available ?? 0,
            location_id: inv.location_id.toString(),
            sku: null,
          },
          { onConflict: 'store_id,variant_id,location_id' }
        );
      }

      // Update store with counts
      await db.from('stores').update({
        sync_status: 'synced' as const,
        last_sync: new Date().toISOString(),
        products_count: productsCount,
        orders_count: ordersCount,
      }).eq('id', store.id);
    } catch (syncErr) {
      console.error('[Inline Sync Error]', syncErr);
      await db.from('stores').update({ sync_status: 'error' as const }).eq('id', store.id);
    }

    // 5. Redirect back to app with success + counts
    return NextResponse.redirect(
      `${callbackBase}/legacy/app.html?shopify_connected=true&shop=${shop}&products=${productsCount}&orders=${ordersCount}`
    );
  } catch (e) {
    console.error('[Shopify Callback Error]', e);
    return NextResponse.redirect(
      `${process.env.NEXT_PUBLIC_SHOPIFY_APP_URL}/legacy/app.html?shopify_error=auth_failed`
    );
  }
}
