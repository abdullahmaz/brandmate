import { createClient } from '@supabase/supabase-js';

/**
 * Browser Supabase client.
 *
 * Sessions are persisted to localStorage by default. The access token
 * lives on the session object and is what we attach to outgoing API
 * requests (see services/api.js).
 *
 * Env vars come from `.env`:
 *   VITE_SUPABASE_URL=...
 *   VITE_SUPABASE_ANON_KEY=...
 */

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  // Surface a clear console error so devs notice missing env quickly.
  // The AuthProvider will still render — it just won't be able to sign
  // anyone in until the env is fixed.
  console.error(
    '[Brandmate] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. ' +
    'Auth is disabled. Add them to frontend/.env and restart the dev server.'
  );
}

export const supabase = createClient(
  supabaseUrl ?? 'http://placeholder.invalid',
  supabaseAnonKey ?? 'placeholder',
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
    },
  },
);
