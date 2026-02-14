import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

// POST /api/ai/analyze — Analyze Shopify store data and recommend modules
export async function POST(request: NextRequest) {
  try {
    const { store_id, user_id, modules, user_costs } = await request.json();

    const db = getServiceSupabase();

    // Find store - flexible lookup
    let store;
    if (store_id && store_id !== 'demo') {
      const { data } = await db.from('stores').select('*').eq('id', store_id).single();
      store = data;
    }
    if (!store && user_id) {
      // Try by email first
      const { data: user } = await db.from('users').select('id').eq('email', user_id).single();
      if (user) {
        const { data } = await db.from('stores').select('*').eq('user_id', user.id).limit(1).single();
        store = data;
      }
      // Try by user UUID
      if (!store) {
        const { data } = await db.from('stores').select('*').eq('user_id', user_id).limit(1).single();
        store = data;
      }
    }
    // Last resort: get any store
    if (!store) {
      const { data } = await db.from('stores').select('*').order('created_at', { ascending: false }).limit(1).single();
      store = data;
    }

    if (!store) {
      return NextResponse.json({ error: 'No store found. Connect Shopify first.' }, { status: 404 });
    }

    // Fetch all data
    const [productsRes, ordersRes, inventoryRes] = await Promise.all([
      db.from('products').select('*').eq('store_id', store.id).eq('status', 'active'),
      db.from('orders').select('*').eq('store_id', store.id).order('order_date', { ascending: false }),
      db.from('inventory').select('*').eq('store_id', store.id),
    ]);

    const products = productsRes.data || [];
    const orders = ordersRes.data || [];
    const inventory = inventoryRes.data || [];

    // ═══════════════════════════════════════════════════
    // ANALYSIS ENGINE — Pure logic, no Claude API needed
    // ═══════════════════════════════════════════════════

    // 1. Product metrics
    const productMetrics = products.map(p => {
      const totalInventory = p.inventory_quantity || 0;
      const price = p.price || 0;
      const cost = p.cost_per_item || (user_costs?.[p.shopify_id]?.cost) || null;

      // Find sales from orders
      let unitsSold = 0;
      let revenue = 0;
      for (const o of orders) {
        const lineItems = (o.line_items as Array<{ product_id: string; quantity: number; price: number }>) || [];
        const match = lineItems.find(li => li.product_id === p.shopify_id);
        if (match) {
          unitsSold += match.quantity;
          revenue += match.quantity * match.price;
        }
      }

      return {
        shopify_id: p.shopify_id,
        title: p.title,
        price,
        cost,
        margin: cost ? ((price - cost) / price * 100) : null,
        inventory: totalInventory,
        inventory_value: totalInventory * price,
        units_sold: unitsSold,
        revenue,
        has_cost: !!cost,
        vendor: p.vendor,
        product_type: p.product_type,
      };
    });

    // 2. Aggregates
    const totalProducts = productMetrics.length;
    const totalInventoryValue = productMetrics.reduce((s, p) => s + p.inventory_value, 0);
    const productsWithCost = productMetrics.filter(p => p.has_cost).length;
    const productsOutOfStock = productMetrics.filter(p => p.inventory <= 0).length;
    const totalUnitsSold = productMetrics.reduce((s, p) => s + p.units_sold, 0);
    const totalRevenue = productMetrics.reduce((s, p) => s + p.revenue, 0);

    // 3. Missing data
    const missing_data: { field: string; description: string; affects: string[]; input_type: string }[] = [];

    if (productsWithCost === 0) {
      missing_data.push({
        field: 'cost_per_item',
        description: 'Costo por unidad de cada producto (proveedor)',
        affects: ['RENTABILIDAD', 'STOCK', 'FLUJO_CAJA'],
        input_type: 'per_product',
      });
    }

    if (!user_costs?.ordering_cost) {
      missing_data.push({
        field: 'ordering_cost',
        description: 'Costo de hacer un pedido al proveedor ($)',
        affects: ['STOCK'],
        input_type: 'single_value',
      });
    }
    if (!user_costs?.holding_cost_pct) {
      missing_data.push({
        field: 'holding_cost_pct',
        description: 'Costo de almacenar (% del valor del producto por año)',
        affects: ['STOCK'],
        input_type: 'single_value',
      });
    }
    if (!user_costs?.fixed_costs) {
      missing_data.push({
        field: 'fixed_costs',
        description: 'Costos fijos mensuales (alquiler, sueldos, etc.)',
        affects: ['RENTABILIDAD', 'FLUJO_CAJA'],
        input_type: 'single_value',
      });
    }

    // 4. Module analysis
    const targetModules = modules || ['STOCK', 'FORECAST', 'RENTABILIDAD', 'FLUJO_CAJA'];
    const moduleAnalysis = [];

    // ── RENTABILIDAD ──────────────────────────────────
    if (targetModules.includes('RENTABILIDAD')) {
      // Can run even without cost - will just show what's available
      const productsForAnalysis = productMetrics
        .filter(p => p.price > 0)
        .slice(0, 20)
        .map(p => ({
          name: p.title,
          price_venta: p.price,
          cost: p.cost || user_costs?.[p.shopify_id]?.cost || 0,
          volume: p.units_sold || Math.max(p.inventory, 1),
        }));

      const hasCosts = productsForAnalysis.some(p => p.cost > 0);

      moduleAnalysis.push({
        module: 'RENTABILIDAD',
        applicable: true,
        priority: hasCosts ? 'high' : 'medium',
        insights: hasCosts
          ? `${productsForAnalysis.filter(p => p.cost > 0).length} productos con margen calculable. Click para ver punto de equilibrio y ranking de rentabilidad.`
          : `${productsForAnalysis.length} productos con precios. Cargá los costos para calcular márgenes y punto de equilibrio.`,
        needs: hasCosts ? [] : ['cost_per_item'],
        inputs: {
          products: productsForAnalysis,
          fixed_costs: user_costs?.fixed_costs || undefined,
        },
      });
    }

    // ── STOCK (EOQ) ────────────────────────────────────
    if (targetModules.includes('STOCK')) {
      const hasOrderingCost = !!user_costs?.ordering_cost;
      const hasHoldingCost = !!user_costs?.holding_cost_pct;
      const topByInventory = [...productMetrics].sort((a, b) => b.inventory - a.inventory);
      const topProduct = topByInventory[0];

      // Can estimate demand from inventory if no orders
      const estimatedDemand = topProduct ? (topProduct.units_sold > 0
        ? topProduct.units_sold * 12
        : topProduct.inventory * 4) : 100;

      const canRun = topProduct && hasOrderingCost && hasHoldingCost;

      moduleAnalysis.push({
        module: 'STOCK',
        applicable: !!topProduct,
        priority: canRun ? 'high' : 'medium',
        insights: canRun
          ? `Listo para optimizar inventario de "${topProduct.title}" (demanda estimada: ${estimatedDemand} un/año).`
          : `Necesitamos costo de pedido${!hasHoldingCost ? ' y costo de almacenamiento' : ''} para optimizar el inventario de tus ${totalProducts} productos.`,
        needs: [
          ...(!hasOrderingCost ? ['ordering_cost'] : []),
          ...(!hasHoldingCost ? ['holding_cost_pct'] : []),
        ],
        inputs: canRun ? {
          D: estimatedDemand,
          K: user_costs.ordering_cost,
          h: (user_costs.holding_cost_pct / 100) * (topProduct.cost || topProduct.price),
          L: user_costs?.lead_time || 7,
          product_name: topProduct.title,
        } : null,
      });
    }

    // ── FORECAST ─────────────────────────────────────
    if (targetModules.includes('FORECAST')) {
      // Build monthly time series
      const monthlySales: Record<string, number> = {};
      orders.forEach(o => {
        const month = (o.order_date as string)?.substring(0, 7);
        if (month) {
          monthlySales[month] = (monthlySales[month] || 0) + parseFloat(o.total_price || '0');
        }
      });
      const timeseries = Object.entries(monthlySales)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([, v]) => v);

      const hasEnoughData = timeseries.length >= 3;

      moduleAnalysis.push({
        module: 'FORECAST',
        applicable: hasEnoughData,
        priority: hasEnoughData ? 'high' : 'low',
        insights: hasEnoughData
          ? `${timeseries.length} meses de ventas disponibles. Podemos pronosticar demanda futura.`
          : `Necesitamos al menos 3 meses de ventas para pronosticar. Actualmente tenés ${timeseries.length}. Una vez que vendas, esto se activa automáticamente.`,
        needs: hasEnoughData ? [] : ['sales_history'],
        inputs: hasEnoughData ? { timeseries, method: 'auto' } : null,
      });
    }

    // ── FLUJO_CAJA ───────────────────────────────────
    if (targetModules.includes('FLUJO_CAJA')) {
      const monthlyMap = monthlySalesMap(orders);
      const months = Object.keys(monthlyMap).length;
      const avgMonthlyRevenue = months > 0
        ? Object.values(monthlyMap).reduce((s, v) => s + v, 0) / months
        : totalInventoryValue / 6; // estimate from inventory

      moduleAnalysis.push({
        module: 'FLUJO_CAJA',
        applicable: totalProducts > 0,
        priority: orders.length > 0 ? 'medium' : 'low',
        insights: orders.length > 0
          ? `Ingreso mensual promedio: $${avgMonthlyRevenue.toFixed(0)}. Podemos proyectar flujo de caja a 6 meses.`
          : `Sin ventas aún, pero podemos estimar flujo basado en inventario ($${totalInventoryValue.toFixed(0)} valorizado).`,
        needs: user_costs?.fixed_costs ? [] : ['fixed_costs'],
        inputs: {
          opening_balance: user_costs?.opening_balance || 0,
          periods: 6,
          inflows: [{ name: 'Ventas Shopify', amount: Math.round(avgMonthlyRevenue) }],
          outflows: user_costs?.fixed_costs
            ? [{ name: 'Costos fijos', amount: user_costs.fixed_costs }]
            : [],
        },
      });
    }

    // 5. Recommendations
    const recommendations: string[] = [];

    if (productsWithCost === 0) {
      recommendations.push('Cargá el costo unitario de tus productos para desbloquear el análisis de rentabilidad y optimización de inventario.');
    }
    if (productsOutOfStock > 0) {
      const outNames = productMetrics.filter(p => p.inventory <= 0).slice(0, 3).map(p => p.title).join(', ');
      recommendations.push(`${productsOutOfStock} producto(s) sin stock: ${outNames}. Reponé antes de perder ventas.`);
    }
    if (totalUnitsSold === 0 && orders.length === 0) {
      recommendations.push('No hay órdenes registradas. Los módulos FORECAST y STOCK se activan automáticamente cuando empieces a vender.');
    }
    if (totalProducts > 5) {
      const topByValue = [...productMetrics].sort((a, b) => b.inventory_value - a.inventory_value);
      const top3 = topByValue.slice(0, 3).map(p => `${p.title} ($${p.inventory_value.toFixed(0)})`).join(', ');
      recommendations.push(`Mayor capital inmovilizado en: ${top3}.`);
    }

    // 6. Response
    const analysis = {
      general_insights: `Tu tienda tiene ${totalProducts} productos activos` +
        (totalInventoryValue > 0 ? ` con $${totalInventoryValue.toLocaleString('es')} en inventario` : '') +
        (totalUnitsSold > 0 ? ` y ${totalUnitsSold} unidades vendidas ($${totalRevenue.toLocaleString('es')}).` : '.') +
        (productsOutOfStock > 0 ? ` ${productsOutOfStock} sin stock.` : ''),
      modules: moduleAnalysis,
      recommendations,
      missing_data,
      product_summary: productMetrics.slice(0, 20),
    };

    return NextResponse.json({ analysis });
  } catch (e) {
    console.error('[AI Analyze Error]', e);
    return NextResponse.json(
      { error: 'Analysis failed', detail: (e as Error).message },
      { status: 500 }
    );
  }
}

function monthlySalesMap(orders: Array<{ order_date?: string; total_price?: string }>) {
  const map: Record<string, number> = {};
  orders.forEach(o => {
    const month = (o.order_date as string)?.substring(0, 7);
    if (month) map[month] = (map[month] || 0) + parseFloat(o.total_price || '0');
  });
  return map;
}
