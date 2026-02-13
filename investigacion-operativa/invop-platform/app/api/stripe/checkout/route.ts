import { NextRequest, NextResponse } from 'next/server';
import { getStripe } from '@/lib/stripe';

// POST /api/stripe/checkout — Create checkout session
export async function POST(request: NextRequest) {
  try {
    const { plan, email } = await request.json();

    if (!plan || !email) {
      return NextResponse.json({ error: 'plan and email required' }, { status: 400 });
    }

    const stripe = getStripe();
    const priceId = plan === 'pro'
      ? process.env.STRIPE_PRICE_PRO!
      : process.env.STRIPE_PRICE_STARTER!;

    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      payment_method_types: ['card'],
      customer_email: email,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${process.env.NEXT_PUBLIC_APP_URL}/legacy/app.html?payment_success=true&plan=${plan}`,
      cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/legacy/app.html?payment_cancelled=true`,
      metadata: { price_id: priceId, plan },
    });

    return NextResponse.json({ url: session.url });
  } catch (e) {
    console.error('[Stripe Checkout Error]', e);
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
