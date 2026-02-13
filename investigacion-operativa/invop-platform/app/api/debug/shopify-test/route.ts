import { NextRequest, NextResponse } from 'next/server';
import { getServiceSupabase } from '@/lib/supabase';

// GET /api/debug/shopify-test?shop=invop-ai-test.myshopify.com
// Tests the Shopify API directly and shows raw results/errors
export async function GET(request: NextRequest) {
  const shop = request.nextUrl.searchParams.get('shop') || 'invop-ai-test.myshopify.com';
  const db = getServiceSupabase();

  // Get store credentials
  const { data: store, error: storeErr } = await db
    .from('stores')
    .select('*')
    .eq('shop_domain', shop)
    .single();

  if (storeErr || !store) {
    return NextResponse.json({ error: 'Store not found', storeErr });
  }

  const apiVersion = '2024-10';
  const results: Record<string, unknown> = {
    shop_domain: store.shop_domain,
    access_token_preview: store.access_token?.substring(0, 12) + '...',
    api_version: apiVersion,
    tests: {},
  };

  // Test 1: Shop info (simplest API call)
  try {
    const shopRes = await fetch(
      `https://${store.shop_domain}/admin/api/${apiVersion}/shop.json`,
      {
        headers: {
          'X-Shopify-Access-Token': store.access_token,
          'Content-Type': 'application/json',
        },
      }
    );
    const shopStatus = shopRes.status;
    const shopBody = await shopRes.text();
    results.tests = {
      ...results.tests as object,
      shop_info: {
        status: shopStatus,
        body: shopStatus === 200 ? JSON.parse(shopBody) : shopBody.substring(0, 500),
      },
    };
  } catch (e) {
    results.tests = {
      ...results.tests as object,
      shop_info: { error: (e as Error).message },
    };
  }

  // Test 2: Products count
  try {
    const prodRes = await fetch(
      `https://${store.shop_domain}/admin/api/${apiVersion}/products/count.json`,
      {
        headers: {
          'X-Shopify-Access-Token': store.access_token,
          'Content-Type': 'application/json',
        },
      }
    );
    const prodStatus = prodRes.status;
    const prodBody = await prodRes.text();
    results.tests = {
      ...results.tests as object,
      products_count: {
        status: prodStatus,
        body: prodStatus === 200 ? JSON.parse(prodBody) : prodBody.substring(0, 500),
      },
    };
  } catch (e) {
    results.tests = {
      ...results.tests as object,
      products_count: { error: (e as Error).message },
    };
  }

  // Test 3: Fetch actual products (limit 5)
  try {
    const prodRes = await fetch(
      `https://${store.shop_domain}/admin/api/${apiVersion}/products.json?limit=5`,
      {
        headers: {
          'X-Shopify-Access-Token': store.access_token,
          'Content-Type': 'application/json',
        },
      }
    );
    const prodStatus = prodRes.status;
    const prodBody = await prodRes.text();
    results.tests = {
      ...results.tests as object,
      products_list: {
        status: prodStatus,
        body: prodStatus === 200 ? JSON.parse(prodBody) : prodBody.substring(0, 500),
      },
    };
  } catch (e) {
    results.tests = {
      ...results.tests as object,
      products_list: { error: (e as Error).message },
    };
  }

  return NextResponse.json(results, { status: 200 });
}
