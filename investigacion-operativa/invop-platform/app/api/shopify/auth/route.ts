import { NextRequest, NextResponse } from 'next/server';
import { buildShopifyAuthUrl } from '@/lib/shopify';

// GET /api/shopify/auth?shop=my-store.myshopify.com
export async function GET(request: NextRequest) {
  const shop = request.nextUrl.searchParams.get('shop');

  if (!shop || !shop.includes('.myshopify.com')) {
    return NextResponse.json(
      { error: 'Missing or invalid shop parameter. Use: ?shop=your-store.myshopify.com' },
      { status: 400 }
    );
  }

  // Sanitize shop domain
  const cleanShop = shop.replace(/[^a-zA-Z0-9\-\.]/g, '');

  const authUrl = buildShopifyAuthUrl(cleanShop);
  return NextResponse.redirect(authUrl);
}
