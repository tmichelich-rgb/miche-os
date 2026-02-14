import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

// POST /api/auth/google — Register/login user from Google OAuth
// Accepts EITHER:
//   { credential: "eyJhb..." }  — raw Google JWT (preferred, more secure)
//   { name, email, picture }    — pre-parsed fields (legacy fallback)
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { credential, fingerprint } = body;

    let email: string;
    let name: string;
    let picture: string | null = null;

    if (credential) {
      // Decode Google JWT
      const payload = JSON.parse(
        Buffer.from(credential.split('.')[1], 'base64').toString()
      );
      email = payload.email;
      name = payload.name || payload.given_name || email.split('@')[0];
      picture = payload.picture || null;
    } else if (body.email) {
      // Legacy: pre-parsed fields from frontend
      email = body.email;
      name = body.name || email.split('@')[0];
      picture = body.picture || null;
    } else {
      return NextResponse.json({ error: 'credential or email required' }, { status: 400 });
    }

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
          name,
          picture,
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
