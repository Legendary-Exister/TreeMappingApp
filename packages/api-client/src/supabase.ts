import { createClient, SupabaseClient } from '@supabase/supabase-js';

export interface SupabaseConfig {
  supabaseUrl: string;
  supabaseKey: string;
}

export function createTreeMapSupabaseClient(config: SupabaseConfig): SupabaseClient {
  return createClient(config.supabaseUrl, config.supabaseKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
    },
  });
}
