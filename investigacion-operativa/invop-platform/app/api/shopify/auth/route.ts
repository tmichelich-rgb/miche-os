import { NextRequest, NextResponse } from 'next/server';
import { buildShopifyAuthUrl } from '@/lib/shopify';

// GET /api/shopify/auth?shop=my-store.myshopify.com&email=user@example.com
export async function GET(request: NextRequest) {
  const shop = request.nextUrl.searchParams.get('shop');
  const email = request.nextUrl.searchParams.get('email');

  if (!shop || !shop.includes('.myshopify.com')) {
    return NextResponse.json(
      { error: 'Missing or invalid shop parameter. Use: ?shop=your-store.myshopify.com' },
      { status: 400 }
    );
  }

  // Sanitize shop domain
  const cleanShop = shop.replace(/[^a-zA-Z0-9\-\.]/g, '');

  const authUrl = buildShopifyAuthUrl(cleanShop, email || undefined);
  return NextResponse.redirect(authUrl);
}
