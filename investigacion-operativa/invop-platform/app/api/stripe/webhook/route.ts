import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { getServiceSupabase } from '@/lib/supabase';
import { getStripe } from '@/lib/stripe';

// POST /api/stripe/webhook — Handle Stripe webhook events
export async function POST(request: NextRequest) {
  const body = await request.text();
  const sig = request.headers.get('stripe-signature');

  if (!sig) {
    return NextResponse.json({ error: 'Missing signature' }, { status: 400 });
  }

  const stripe = getStripe();
  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch (e) {
    console.error('[Stripe Webhook] Signature verification failed:', (e as Error).message);
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 });
  }

  const db = getServiceSupabase();

  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object as Stripe.Checkout.Session;
      const email = session.customer_email || session.customer_details?.email;
      const priceId = session.metadata?.price_id;

      if (email) {
        const plan = priceId === process.env.STRIPE_PRICE_PRO ? 'pro' : 'starter';
        await db.from('users').update({
          plan: plan as 'starter' | 'pro',
          plan_since: new Date().toISOString(),
          stripe_customer_id: session.customer as string,
        }).eq('email', email);
      }
      break;
    }

    case 'customer.subscription.updated': {
      const sub = event.data.object as Stripe.Subscription;
      const customerId = sub.customer as string;

      if (sub.status === 'active') {
        const priceId = sub.items.data[0]?.price?.id;
        const plan = priceId === process.env.STRIPE_PRICE_PRO ? 'pro' : 'starter';
        await db.from('users').update({
          plan: plan as 'starter' | 'pro',
        }).eq('stripe_customer_id', customerId);
      }
      break;
    }

    case 'customer.subscription.deleted': {
      const sub = event.data.object as Stripe.Subscription;
      const customerId = sub.customer as string;

      // Downgrade to free
      await db.from('users').update({
        plan: 'free' as const,
      }).eq('stripe_customer_id', customerId);
      break;
    }

    default:
      console.log('[Stripe Webhook] Unhandled event:', event.type);
  }

  return NextResponse.json({ received: true });
}
