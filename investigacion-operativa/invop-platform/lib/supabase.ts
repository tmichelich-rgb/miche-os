import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Lazy-initialized clients (avoid build-time errors when env vars aren't set)
let _client: SupabaseClient | null = null;
let _serviceClient: SupabaseClient | null = null;

// Client-side (browser) — uses anon key
export function getSupabase(): SupabaseClient {
  if (!_client) {
    _client = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
  }
  return _client;
}

// Server-side — uses service role key (full access, bypasses RLS)
export function getServiceSupabase(): SupabaseClient {
  if (!_serviceClient) {
    _serviceClient = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      { auth: { persistSession: false } }
    );
  }
  return _serviceClient;
}
