import { NextRequest, NextResponse } from 'next/server';
import { exchangeCodeForToken, registerWebhooks } from '@/lib/shopify';
import { getServiceSupabase } from '@/lib/supabase';

// GET /api/shopify/callback?code=xxx&shop=xxx&state=xxx
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const code = searchParams.get('code');
  const shop = searchParams.get('shop');
  const userEmail = searchParams.get('user_email'); // passed via state or cookie

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

    // Find or create user by email (from auth cookie/state)
    // For now, we'll associate via a lookup — in production, use JWT from cookie
    let userId: string | null = null;
    if (userEmail) {
      const { data: user } = await db
        .from('users')
        .select('id')
        .eq('email', userEmail)
        .single();
      userId = user?.id || null;
    }

    if (!userId) {
      // Fallback: redirect to app with token to complete connection
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
