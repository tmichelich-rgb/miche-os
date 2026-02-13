import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

const FREE_LIMIT = 3;
const STARTER_LIMIT = 999999; // Effectively unlimited

// GET /api/usage?email=xxx — Check usage limits
export async function GET(request: NextRequest) {
  const email = request.nextUrl.searchParams.get('email');

  if (!email) {
    return NextResponse.json({ error: 'email required' }, { status: 400 });
  }

  try {
    const db = getServiceSupabase();

    const { data: user } = await db
      .from('users')
      .select('id, plan, solve_count')
      .eq('email', email)
      .single();

    if (!user) {
      return NextResponse.json({
        allowed: true,
        remaining: FREE_LIMIT,
        solves_used: 0,
        is_pro: false,
        plan: 'free',
      });
    }

    const limit = user.plan === 'pro' || user.plan === 'starter'
      ? STARTER_LIMIT
      : FREE_LIMIT;

    const allowed = user.solve_count < limit;
    const remaining = Math.max(0, limit - user.solve_count);

    return NextResponse.json({
      allowed,
      remaining,
      solves_used: user.solve_count,
      is_pro: user.plan === 'pro',
      plan: user.plan,
    });
  } catch (e) {
    console.error('[Usage Error]', e);
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}

// POST /api/usage — Record a solve
export async function POST(request: NextRequest) {
  try {
    const { email, module, status, time_ms, fingerprint } = await request.json();

    if (!email) {
      return NextResponse.json({ error: 'email required' }, { status: 400 });
    }

    const db = getServiceSupabase();

    // Increment solve count
    await db.rpc('increment_solve_count', { user_email: email });

    // Record analysis
    const { data: user } = await db
      .from('users')
      .select('id')
      .eq('email', email)
      .single();

    if (user) {
      await db.from('analyses').insert({
        user_id: user.id,
        module: module || 'LP',
        input_data: {},
        output_data: { status: status || 'OK' },
        source: 'manual' as const,
        solve_time_ms: time_ms || null,
      });
    }

    return NextResponse.json({ ok: true });
  } catch (e) {
    console.error('[Usage POST Error]', e);
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
