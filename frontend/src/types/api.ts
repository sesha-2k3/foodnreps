/**
 * API response types — TypeScript interfaces matching the backend Pydantic schemas.
 *
 * Design choice — Decimal fields as string:
 *   Python Decimal serialises as a JSON string, not a float. FastAPI preserves
 *   this. Fields like prescribed_load_kg, actual_load_kg, tonnage_kg, and all
 *   diet macros arrive as "70.00" | null, not 70.0 | null. The frontend uses
 *   parseFloat() for display purposes only. All comparison and computation on
 *   these fields should use parseFloat() rather than assuming they are numbers.
 *
 * Design choice — pre-computed display fields on prescription responses:
 *   exercise_label ("A", "B", "C"), reps_display ("6–8", "max reps"), and
 *   load_display ("70 kg", "BW") are computed by the backend Pydantic schema
 *   from the domain entity @property methods. The frontend receives them ready
 *   to render — no display transformation logic is duplicated here. 
 *
 * Design choice — logs nested under prescriptions in the workout response:
 *   A separate GET /logs endpoint would add a second network round-trip for
 *   every page load. Since the client view always renders prescriptions and
 *   their logs together, nesting them is the correct data shape for this
 *   read pattern. The larger payload is acceptable — an average day of 6
 *   exercises with 10 log entries each is well under 10 KB.
 *
 * Design choice — no separate PaginatedResponse wrapper here:
 *   The workout programme response is not paginated — the full hierarchy is
 *   always returned for a single active programme. The admin list endpoints
 *   (Sprint 9) will introduce PaginatedResponse; it is not needed here.
 */

// ── Workout programme hierarchy ───────────────────────────────────────────────

/**
 * A single workout log entry (RED side).
 * Maps to backend WorkoutLogResponse Pydantic schema.
 * Maps to database table: workout_logs
 */
export interface WorkoutLogResponse {
  id: string;
  prescription_id: string | null;
  client_id: string;
  /** Free-text exercise name — only populated for orphan logs (no prescription_id). */
  exercise_name: string | null;
  /** ISO date string: "2024-04-08" — DATE type, not TIMESTAMPTZ. */
  logged_at: string;
  actual_sets: number;
  /** Reps per set, not total reps. tonnage = sets × reps × load. */
  actual_reps: number;
  /** Decimal serialised as string: "70.00". Null for bodyweight exercises. */
  actual_load_kg: string | null;
  /** Rate of Perceived Exertion, 1.0–10.0 with half-point precision: "8.5". */
  actual_rpe: string | null;
  /** Pre-session freshness 1–10. Different from RPE (post-exercise). */
  readiness: number | null;
  time_taken_seconds: number | null;
  client_notes: string | null;
  /**
   * Database GENERATED column: sets × reps × load.
   * Null when actual_load_kg is null (bodyweight). "1960.00"
   */
  tonnage_kg: string | null;
  created_at: string;
}

/**
 * A single exercise prescription (BLUE side).
 * Maps to backend WorkoutPrescriptionResponse Pydantic schema.
 * Maps to database table: workout_prescriptions
 */
export interface WorkoutPrescriptionResponse {
  id: string;
  order_index: number;
  /**
   * Pre-computed from order_index: 1 → "A", 2 → "B", 3 → "C".
   * Computed by the backend domain entity @property, serialised by
   * the Pydantic schema. Never compute this on the frontend.
   */
  exercise_label: string;
  exercise_name: string;
  warmup_sets: number | null;
  working_sets: number | null;
  reps_min: number | null;
  reps_max: number | null;
  reps_note: string | null;
  /**
   * Pre-computed display string: "6–8", "5", "max reps — stop when speed drops".
   * Computed by the backend domain entity @property. Never compute on the frontend.
   */
  reps_display: string;
  /** Decimal as string: "70.00". Null for bodyweight. */
  prescribed_load_kg: string | null;
  /** Qualitative descriptor: "BW", "Strict". */
  prescribed_load_text: string | null;
  /**
   * Pre-computed display string: "70 kg", "BW", "Strict form".
   * Computed by the backend domain entity. Never compute on the frontend.
   */
  load_display: string;
  /** Rate of Perceived Exertion target: "8.0", "8.5". Decimal as string. */
  prescribed_rpe: string | null;
  prescribed_rir: number | null;
  rest_seconds: number | null;
  instructions: string | null;
  /** Logs for this prescription, newest first. Nested for single-request load. */
  logs: WorkoutLogResponse[];
}

/**
 * A training day within a week.
 * Maps to backend ProgramDayResponse Pydantic schema.
 * Maps to database table: program_days
 */
export interface ProgramDayResponse {
  id: string;
  day_number: number;
  /** "Day 1", "Upper Body", "Pull Day" — coach-assigned label. */
  label: string;
  notes: string | null;
  prescriptions: WorkoutPrescriptionResponse[];
}

/**
 * A training week within a programme.
 * Maps to backend ProgramWeekResponse Pydantic schema.
 * Maps to database table: program_weeks
 */
export interface ProgramWeekResponse {
  id: string;
  week_number: number;
  /** "Week 1", "Deload Week", "Peak Week" — coach-assigned label. */
  label: string;
  notes: string | null;
  days: ProgramDayResponse[];
}

/**
 * A complete workout programme with full hierarchy.
 * Maps to backend WorkoutProgramFullResponse Pydantic schema.
 * Maps to database table: workout_programs
 *
 * Returned by GET /client/workout and GET /personal/workout.
 * Contains the full week → day → prescription → log tree for a single
 * active programme.
 */
// types/api.ts — WorkoutProgramResponse
export interface WorkoutProgramResponse {
  id: string;
  name: string;
  is_active: boolean;
  is_personal: boolean;
  is_template: boolean;
  coach_notes: string | null;
  owner_id: string;
  created_by_id: string;
  version: number;
  override_reason: string | null;
  created_at: string;
  updated_at: string;
  weeks: ProgramWeekResponse[];
}

// ── Diet plan ─────────────────────────────────────────────────────────────────

/**
 * A single food item in a diet plan.
 * Maps to backend DietEntryResponse Pydantic schema.
 * Maps to database table: diet_entries
 */
export interface DietEntryResponse {
  id: string;
  food_name: string;
  /** Decimal as string: "480.00". Coach-specified, not macro-derived. */
  calories: string;
  protein_g: string;
  fat_g: string;
  carbs_g: string;
  order_index: number;
}

/**
 * A complete diet plan with all entries.
 * Maps to backend DietPlanResponse Pydantic schema.
 * Maps to database table: diet_plans
 *
 * Returned by GET /client/diet and GET /personal/diet.
 */
export interface DietPlanResponse {
  id: string;
  name: string;
  coach_notes: string | null;
  is_personal: boolean;
  /** Ordered by order_index ascending. */
  entries: DietEntryResponse[];
}

// ── Mutation request bodies ───────────────────────────────────────────────────

/**
 * Request body for POST /client/workout-logs.
 * Either prescription_id or exercise_name must be non-null
 * (mirrors DB CHECK: chk_exercise_reference).
 * This constraint is enforced by the LogEntryModal before submission.
 */
export interface WorkoutLogCreateRequest {
  /** Null only for orphan free-text exercise entries. */
  prescription_id: string | null;
  /** Required when prescription_id is null. */
  exercise_name: string | null;
  /** ISO date: "2024-04-08" */
  logged_at: string;
  actual_sets: number;
  actual_reps: number;
  /** Number (not string) in the request body. Backend converts to Decimal. */
  actual_load_kg: number | null;
  actual_rpe: number | null;
  readiness: number | null;
  time_taken_seconds: number | null;
  client_notes: string | null;
}

/**
 * Request body for POST /personal/workout (create personal programme).
 * Only used in PersonalWorkout.tsx when no personal programme exists.
 */
export interface CreateProgrammeRequest {
  name: string;
}

/**
 * Request body for POST /personal/diet (create personal diet plan).
 */
export interface CreateDietPlanRequest {
  name: string;
}

// ── Client summary (for coaching staff client lists) ──────────────────────────

export interface ClientSummaryResponse {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  /** True when this client has at least one active workout programme. */
  has_active_workout: boolean;
  /** True when this client has at least one active diet plan. */
  has_active_diet: boolean;
}

export interface PaginatedClientsResponse {
  data: ClientSummaryResponse[];
  total: number;
  limit: number;
  offset: number;
}

// ── Workout programme mutations ───────────────────────────────────────────────

export interface CreateProgrammeRequest {
  name: string;
  coach_notes?: string;
}

export interface AddWeekRequest {
  week_number: number;
  label: string;
  notes?: string;
}

export interface AddDayRequest {
  day_number: number;
  label: string;
  notes?: string;
}

/**
 * Full prescription creation payload.
 * Mirrors WorkoutPrescription domain entity fields.
 * Reps constraint: reps_min or reps_note must be non-null
 * (enforced by modal before submission).
 */
export interface AddPrescriptionRequest {
  exercise_name: string;
  order_index: number;
  warmup_sets?: number | null;
  working_sets?: number | null;
  reps_min?: number | null;
  reps_max?: number | null;
  reps_note?: string | null;
  prescribed_load_kg?: number | null;
  prescribed_load_text?: string | null;
  prescribed_rpe?: number | null;
  prescribed_rir?: number | null;
  rest_seconds?: number | null;
  instructions?: string | null;
}

/**
 * Partial update — only send changed fields.
 * The backend merges these onto the existing prescription.
 */
export interface UpdatePrescriptionRequest {
  exercise_name?: string;
  working_sets?: number | null;
  warmup_sets?: number | null;
  reps_min?: number | null;
  reps_max?: number | null;
  reps_note?: string | null;
  prescribed_load_kg?: number | null;
  prescribed_load_text?: string | null;
  prescribed_rpe?: number | null;
  prescribed_rir?: number | null;
  rest_seconds?: number | null;
  instructions?: string | null;
}

// ── Diet plan mutations ───────────────────────────────────────────────────────

export interface AddDietEntryRequest {
  food_name: string;
  calories: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
  order_index: number;
}

export interface UpdateDietEntryRequest {
  food_name?: string;
  calories?: number;
  protein_g?: number;
  fat_g?: number;
  carbs_g?: number;
  order_index?: number;
}