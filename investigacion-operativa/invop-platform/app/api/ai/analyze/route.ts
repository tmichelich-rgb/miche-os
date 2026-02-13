import { NextRequest, NextResponse } from 'next/server';
import { getAnthropic } from '@/lib/anthropic';
import { getServiceSupabase } from '@/lib/supabase';

// POST /api/ai/analyze — AI analyzes Shopify data and prepares module inputs
export async function POST(request: NextRequest) {
  try {
    const { store_id, user_id, modules } = await request.json();

    if (!store_id || !user_id) {
      return NextResponse.json({ error: 'store_id and user_id required' }, { status: 400 });
    }

    const db = getServiceSupabase();

    // 1. Verify user has Pro plan
    const { data: user } = await db.from('users').select('plan').eq('id', user_id).single();
    if (!user || user.plan !== 'pro') {
      return NextResponse.json({ error: 'Pro plan required for AI analysis' }, { status: 403 });
    }

    // 2. Fetch store data
    const [productsRes, ordersRes] = await Promise.all([
      db.from('products').select('*').eq('store_id', store_id).limit(100),
      db.from('orders').select('*').eq('store_id', store_id).order('order_date', { ascending: false }).limit(500),
    ]);

    const products = productsRes.data || [];
    const orders = ordersRes.data || [];

    if (products.length === 0 && orders.length === 0) {
      return NextResponse.json({
        error: 'No data synced yet. Please sync your Shopify store first.',
      }, { status: 400 });
    }

    // 3. Prepare data summary for Claude
    const dataSummary = buildDataSummary(products, orders);

    // 4. Call Claude to analyze
    const targetModules = modules || ['STOCK', 'FORECAST', 'RENTABILIDAD', 'FLUJO_CAJA'];

    const message = await getAnthropic().messages.create({
      model: 'claude-sonnet-4-5-20250514',
      max_tokens: 4000,
      messages: [
        {
          role: 'user',
          content: `Sos un analista de operaciones experto. Analizá los siguientes datos de una tienda Shopify y prepará los inputs necesarios para los módulos de optimización indicados.

## Datos de la Tienda

${dataSummary}

## Módulos a Analizar
${targetModules.join(', ')}

## Instrucciones
Para cada módulo, respondé en JSON con esta estructura:
{
  "modules": [
    {
      "module": "STOCK",
      "applicable": true/false,
      "confidence": 0.0-1.0,
      "inputs": { /* inputs formateados para el solver */ },
      "insights": "Explicación en español de qué encontraste y por qué recomendás esto",
      "priority": "high/medium/low"
    }
  ],
  "general_insights": "Resumen general del estado del negocio",
  "recommendations": ["recomendación 1", "recomendación 2"]
}

### Reglas por módulo:
- **STOCK**: Necesita demand_D (demanda anual), order_cost_k (costo por pedido), holding_cost_c1 (costo almacenamiento), acquisition_cost_b (costo unitario), lead_time (días). Calculá demand_D del historial de ventas. Estimá order_cost_k y holding_cost_c1 si no hay data directa.
- **FORECAST**: Necesita una serie temporal de ventas (array de números). Agrupá ventas por mes de los últimos 12 meses.
- **RENTABILIDAD**: Necesita products[{name, price_venta, cost, volume}] y fixed_costs. Calculá volume del historial de órdenes.
- **FLUJO_CAJA**: Necesita opening_balance (estimá del último mes), periods (6), inflows[{name,amount}], outflows[{name,amount}]. Agrupá por categoría.

Respondé SOLO con JSON válido, sin markdown.`,
        },
      ],
    });

    // 5. Parse Claude's response
    const aiText = message.content[0].type === 'text' ? message.content[0].text : '';
    let analysis;
    try {
      analysis = JSON.parse(aiText);
    } catch {
      // Try to extract JSON from response
      const jsonMatch = aiText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        analysis = JSON.parse(jsonMatch[0]);
      } else {
        throw new Error('Claude did not return valid JSON');
      }
    }

    // 6. Save analysis results
    for (const mod of analysis.modules || []) {
      if (mod.applicable) {
        await db.from('analyses').insert({
          user_id,
          store_id,
          module: mod.module,
          input_data: mod.inputs || {},
          output_data: {},  // Will be populated when solver runs
          ai_insights: mod.insights,
          source: 'shopify_auto' as const,
        });
      }
    }

    return NextResponse.json({
      success: true,
      analysis,
      tokens_used: message.usage.input_tokens + message.usage.output_tokens,
    });
  } catch (e) {
    console.error('[AI Analyze Error]', e);
    return NextResponse.json(
      { error: 'AI analysis failed', detail: (e as Error).message },
      { status: 500 }
    );
  }
}

// ═══ Helpers ═══

function buildDataSummary(products: Record<string, unknown>[], orders: Record<string, unknown>[]): string {
  // Products summary
  const productLines = products.slice(0, 30).map((p: Record<string, unknown>) => {
    const variants = p.variants as { price: number; cost: number | null; inventory_quantity: number }[];
    const mainV = variants?.[0];
    return `- ${p.title}: precio $${mainV?.price || p.price}, costo $${mainV?.cost || p.cost_per_item || '?'}, stock: ${p.inventory_quantity}`;
  });

  // Monthly sales aggregation
  const monthlySales: Record<string, { total: number; count: number }> = {};
  for (const o of orders) {
    const date = new Date(o.order_date as string);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    if (!monthlySales[key]) monthlySales[key] = { total: 0, count: 0 };
    monthlySales[key].total += Number(o.total_price);
    monthlySales[key].count++;
  }

  const salesLines = Object.entries(monthlySales)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, data]) => `- ${month}: $${data.total.toFixed(2)} (${data.count} órdenes)`);

  // Product sales volume from line items
  const productVolume: Record<string, number> = {};
  for (const o of orders) {
    const lineItems = o.line_items as { title: string; quantity: number }[];
    for (const li of lineItems || []) {
      const key = li.title || 'Unknown';
      productVolume[key] = (productVolume[key] || 0) + li.quantity;
    }
  }

  const volumeLines = Object.entries(productVolume)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 20)
    .map(([name, qty]) => `- ${name}: ${qty} unidades vendidas`);

  return `### Productos (${products.length} total)
${productLines.join('\n')}
${products.length > 30 ? `\n... y ${products.length - 30} productos más` : ''}

### Ventas Mensuales (últimos ${Object.keys(monthlySales).length} meses)
${salesLines.join('\n')}

### Volumen por Producto (top 20)
${volumeLines.join('\n')}

### Resumen
- Total productos: ${products.length}
- Total órdenes (período): ${orders.length}
- Ventas totales período: $${orders.reduce((s, o) => s + Number(o.total_price), 0).toFixed(2)}
- Promedio por orden: $${orders.length > 0 ? (orders.reduce((s, o) => s + Number(o.total_price), 0) / orders.length).toFixed(2) : '0'}`;
}
