import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Handle CORS for API routes (needed when app is embedded in Shopify iframe)
  if (request.nextUrl.pathname.startsWith('/api/')) {
    // Handle preflight
    if (request.method === 'OPTIONS') {
      return new NextResponse(null, {
        status: 200,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // Add CORS headers to response
    const response = NextResponse.next();
    response.headers.set('Access-Control-Allow-Origin', '*');
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    return response;
  }

  // Allow framing by Shopify (X-Frame-Options must not block)
  if (request.nextUrl.pathname.startsWith('/legacy/')) {
    const response = NextResponse.next();
    response.headers.set('Content-Security-Policy', "frame-ancestors 'self' https://*.shopify.com https://admin.shopify.com");
    response.headers.delete('X-Frame-Options'); // Remove default DENY
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/api/:path*', '/legacy/:path*'],
};
