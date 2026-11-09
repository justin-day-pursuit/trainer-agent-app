/**
 * Shared TypeScript Type Definitions.
 * 
 * Mirrors the backend Pydantic schemas to ensure type-safe communication
 * across API endpoints, client logging components, and trainer dashboards.
 */

export interface PrescribedExercise {
  exercise_id: string;
  name: string;
  sets: number;
  target_reps: number;
  target_weight_lbs: number | null;
}

export type Effort = "easy" | "challenging";

export interface ExtractedSet {
  exercise_id: string;
  set_num: number;
  weight_lbs: number | null;
  reps: number;
  pain_flag: boolean;
  note?: string | null;
  effort?: Effort | null;
}

export interface SafetyFlag {
  severity: "info" | "warning" | "critical";
  exercise_id?: string | null;
  message: string;
}

export interface WorkoutPlan {
  id: number;
  client_id: number;
  week_label: string;
  status: "draft" | "approved" | "archived";
  exercises: PrescribedExercise[];
  safety_flags: SafetyFlag[];
  trainer_notes?: string | null;
  approved_at?: string | null;
  created_at: string;
}

export interface WorkoutLog {
  id: number;
  client_id: number;
  plan_id?: number | null;
  raw_input: string;
  extracted_sets: ExtractedSet[];
  has_pain_flag: boolean;
  pain_summary?: string | null;
  logged_at: string;
}

export interface ClientProfile {
  id: number;
  trainer_id: number;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  primary_goal?: string | null;
  experience_level?: string | null;
  injuries: string[];
  intake_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClientSession {
  session_id: number;
  client_id: number;
  session_token: string;
  session_url: string;
  is_active: boolean;
  created_at: string;
}

export interface TriageCard {
  client_id: number;
  client_name: string;
  urgency: "high" | "medium" | "low";
  reason: string;
  recommended_action: string;
  draft_message?: string | null;
}

export interface TrainerDashboardData {
  pending_drafts_count: number;
  total_active_clients: number;
  triage_queue: TriageCard[];
}
