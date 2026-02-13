import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

// POST /api/auth/google — Register/login user from Google OAuth credential
export async function POST(request: NextRequest) {
  try {
    const { credential, fingerprint } = await request.json();

    if (!credential) {
      return NextResponse.json({ error: 'credential required' }, { status: 400 });
    }

    // Decode Google JWT (same as client-side parseJwt)
    const payload = JSON.parse(
      Buffer.from(credential.split('.')[1], 'base64').toString()
    );

    const { email, name, picture } = payload;

    if (!email) {
      return NextResponse.json({ error: 'Invalid credential — no email' }, { status: 400 });
    }

    const db = getServiceSupabase();

    // Upsert user
    const { data: user, error } = await db
      .from('users')
      .upsert(
        {
          email,
          name: name || email.split('@')[0],
          picture: picture || null,
          fingerprint: fingerprint || null,
        },
        { onConflict: 'email' }
      )
      .select('id, email, name, picture, plan, plan_since, solve_count, created_at')
      .single();

    if (error) throw error;

    // Check for connected Shopify store
    const { data: store } = await db
      .from('stores')
      .select('id, shop_domain, sync_status, last_sync, products_count, orders_count')
      .eq('user_id', user.id)
      .single();

    return NextResponse.json({
      user: {
        ...user,
        has_store: !!store,
        store: store || null,
      },
    });
  } catch (e) {
    console.error('[Auth Error]', e);
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
