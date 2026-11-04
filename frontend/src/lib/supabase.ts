/**
 * Supabase Client Initialization.
 * 
 * Provides the browser Supabase client used strictly for trainer authentication.
 * The client web application does not query PostgreSQL directly; all application data
 * flows through our FastAPI backend.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder-project.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
