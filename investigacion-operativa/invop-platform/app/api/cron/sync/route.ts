import { NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

// GET /api/cron/sync — Periodic re-sync of all Shopify stores (runs every 6h)
export async function GET() {
  try {
    const db = getServiceSupabase();

    // Get all stores that were synced more than 6 hours ago
    const sixHoursAgo = new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString();

    const { data: stores } = await db
      .from('stores')
      .select('id')
      .or(`last_sync.is.null,last_sync.lt.${sixHoursAgo}`)
      .eq('sync_status', 'synced');

    if (!stores || stores.length === 0) {
      return NextResponse.json({ message: 'No stores to sync', count: 0 });
    }

    // Trigger sync for each store (async, fire-and-forget)
    const baseUrl = process.env.NEXT_PUBLIC_APP_URL!;
    let triggered = 0;

    for (const store of stores) {
      try {
        await fetch(`${baseUrl}/api/shopify/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ store_id: store.id }),
        });
        triggered++;
      } catch (e) {
        console.error(`[Cron Sync] Failed for store ${store.id}:`, e);
      }
    }

    return NextResponse.json({ message: `Triggered sync for ${triggered} stores`, count: triggered });
  } catch (e) {
    console.error('[Cron Sync Error]', e);
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
