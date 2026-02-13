import { NextRequest, NextResponse } from 'next/server';
import { exchangeCodeForToken, registerWebhooks } from '@/lib/shopify';
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

    // 3. Register Shopify webhooks
    const callbackBase = process.env.NEXT_PUBLIC_SHOPIFY_APP_URL!;
    await registerWebhooks({ shopDomain: shop, accessToken }, callbackBase);

    // 4. Trigger initial data sync (async — don't wait)
    fetch(`${callbackBase}/api/shopify/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ store_id: store.id }),
    }).catch(() => {}); // fire and forget

    // 5. Redirect back to app with success
    return NextResponse.redirect(
      `${process.env.NEXT_PUBLIC_SHOPIFY_APP_URL}/legacy/app.html?shopify_connected=true&shop=${shop}`
    );
  } catch (e) {
    console.error('[Shopify Callback Error]', e);
    return NextResponse.redirect(
      `${process.env.NEXT_PUBLIC_SHOPIFY_APP_URL}/legacy/app.html?shopify_error=auth_failed`
    );
  }
}
