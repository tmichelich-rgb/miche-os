import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

// GET /api/cron/reports — Generate scheduled reports (runs weekly Monday 8am)
// Protected by CRON_SECRET (Vercel sends Authorization: Bearer <secret>)
export async function GET(request: NextRequest) {
  // Verify cron secret
  const authHeader = request.headers.get('authorization');
  const cronSecret = process.env.CRON_SECRET;
  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const db = getServiceSupabase();

    // Find reports that are due
    const now = new Date().toISOString();

    const { data: dueReports } = await db
      .from('reports')
      .select('*, stores(shop_domain, access_token), users(email, name)')
      .eq('enabled', true)
      .or(`next_run.is.null,next_run.lte.${now}`);

    if (!dueReports || dueReports.length === 0) {
      return NextResponse.json({ message: 'No reports due', count: 0 });
    }

    let generated = 0;
    const baseUrl = process.env.NEXT_PUBLIC_APP_URL!;

    for (const report of dueReports) {
      try {
        // Trigger AI analysis for the store
        await fetch(`${baseUrl}/api/ai/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            store_id: report.store_id,
            user_id: report.user_id,
            modules: report.modules,
          }),
        });

        // Update last_run and calculate next_run
        const nextRun = calculateNextRun(report.schedule_cron);
        await db.from('reports').update({
          last_run: now,
          next_run: nextRun,
        }).eq('id', report.id);

        // Create notification
        await db.from('notifications').insert({
          user_id: report.user_id,
          type: 'report_ready',
          channel: 'in_app' as const,
          title: `Reporte "${report.name}" listo`,
          message: `Tu reporte ${report.type} fue generado con datos actualizados de tu tienda.`,
          data: { report_id: report.id },
        });

        generated++;
      } catch (e) {
        console.error(`[Cron Reports] Failed for report ${report.id}:`, e);
      }
    }

    return NextResponse.json({ message: `Generated ${generated} reports`, count: generated });
  } catch (e) {
    console.error('[Cron Reports Error]', e);
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}

function calculateNextRun(cronExpression: string | null): string | null {
  if (!cronExpression) return null;

  // Simple cron parser for common patterns
  const now = new Date();

  if (cronExpression.includes('weekly') || cronExpression === '0 8 * * 1') {
    // Next Monday 8am
    const next = new Date(now);
    next.setDate(next.getDate() + ((1 + 7 - next.getDay()) % 7 || 7));
    next.setHours(8, 0, 0, 0);
    return next.toISOString();
  }

  if (cronExpression.includes('monthly') || cronExpression === '0 8 1 * *') {
    // First of next month 8am
    const next = new Date(now.getFullYear(), now.getMonth() + 1, 1, 8, 0, 0);
    return next.toISOString();
  }

  // Default: 7 days from now
  const next = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  return next.toISOString();
}
