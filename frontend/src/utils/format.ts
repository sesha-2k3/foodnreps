/**
 * Formatting utilities for display values.
 *
 * Design choice — pure functions with no dependencies:
 *   These functions convert raw API values (Decimal-as-string, seconds,
 *   ISO date strings) into human-readable display strings. They have no
 *   imports from application code. This makes them individually testable
 *   and reusable across all views without creating circular dependencies.
 *
 * Design choice — all numeric inputs as string | null:
 *   Backend Decimal fields arrive as strings. All format functions accept
 *   the wire format directly — callers do not need to parseFloat before
 *   passing. The function handles null, empty string, and NaN gracefully.
 *
 * Design choice — ISO date with manual timezone handling:
 *   new Date("2024-04-08") parses as UTC midnight and converts to local
 *   time, which can shift the date one day backward for UTC- timezones.
 *   Appending "T00:00:00" forces local-timezone parsing and keeps the
 *   displayed date consistent with the date the client logged the entry.
 */

/**
 * Format an ISO date string for display.
 * "2024-04-08" → "8 Apr" (locale-aware, short form)
 */
export function formatDate(isoDate: string): string {
  const d = new Date(`${isoDate}T00:00:00`);
  if (isNaN(d.getTime())) return isoDate;
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

/**
 * Format an ISO date for today's date as the default log date.
 * Returns "2024-04-08" format for use in the LogEntryModal date input.
 */
export function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * Format a Decimal-as-string load value for display.
 * "70.00"  → "70 kg"
 * "70.50"  → "70.5 kg"
 * null     → "BW"    (bodyweight)
 * ""       → "BW"
 */
export function formatLoad(loadKg: string | null | undefined): string {
  if (!loadKg) return 'BW';
  const num = parseFloat(loadKg);
  if (isNaN(num)) return 'BW';
  // Trim trailing zeros: 70.00 → 70, 70.50 → 70.5
  const display = num % 1 === 0 ? String(num) : num.toFixed(2).replace(/\.?0+$/, '');
  return `${display} kg`;
}

/**
 * Format a Decimal-as-string tonnage value for display.
 * "1960.00" → "1,960 kg"
 * null      → "—"
 */
export function formatTonnage(tonnageKg: string | null | undefined): string {
  if (!tonnageKg) return '—';
  const num = parseFloat(tonnageKg);
  if (isNaN(num) || num === 0) return '—';
  return `${num.toLocaleString('en-GB', { maximumFractionDigits: 1 })} kg`;
}

/**
 * Format seconds into a readable rest/time duration.
 * 60   → "1 min"
 * 90   → "1:30"
 * 180  → "3 min"
 * 3600 → "1:00:00"
 * null → "—"
 */
export function formatRest(seconds: number | null | undefined): string {
  if (seconds == null || seconds <= 0) return '—';
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (secs === 0) return `${mins} min`;
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

/**
 * Format time_taken_seconds for the log table display.
 * Same as formatRest but semantically "elapsed time" not "rest period".
 * 1200 → "20 min"
 * 4500 → "1:15:00"
 */
export function formatElapsedTime(seconds: number | null | undefined): string {
  if (seconds == null || seconds <= 0) return '—';
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (secs === 0) return `${mins} min`;
    return `${mins}:${String(secs).padStart(2, '0')}`;
  }
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hrs}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Compute live tonnage for the modal preview.
 * Mirrors the DB GENERATED ALWAYS AS column: sets × reps × load.
 * Returns null when load is null (bodyweight — no meaningful tonnage).
 */
export function computeTonnage(
  sets: number | string,
  reps: number | string,
  loadKg: number | string | null,
): number | null {
  if (!loadKg) return null;
  const s = Number(sets);
  const r = Number(reps);
  const l = Number(loadKg);
  if (isNaN(s) || isNaN(r) || isNaN(l) || s <= 0 || r <= 0 || l <= 0) return null;
  return s * r * l;
}

/**
 * Format the live tonnage preview in the modal.
 * 1960 → "1,960 kg"
 * null → "—"
 */
export function formatLiveTonnage(tonnage: number | null): string {
  if (tonnage == null) return '—';
  return `${tonnage.toLocaleString('en-GB', { maximumFractionDigits: 1 })} kg`;
}

/**
 * Format a Decimal-as-string RPE value for table display.
 * "8.0"  → "@ 8"
 * "8.5"  → "@ 8.5"
 * null   → "—"
 */
export function formatRpe(rpe: string | null | undefined): string {
  if (!rpe) return '—';
  const num = parseFloat(rpe);
  if (isNaN(num)) return '—';
  // Drop .0 suffix: 8.0 → "@ 8", keep .5: 8.5 → "@ 8.5"
  const display = num % 1 === 0 ? String(Math.floor(num)) : String(num);
  return `@ ${display}`;
}

/**
 * Convert minutes (user input) to seconds (schema storage).
 * "20" → 1200
 * "1:30" → 90
 * "" → null
 */
export function minutesToSeconds(input: string): number | null {
  if (!input.trim()) return null;
  if (input.includes(':')) {
    const [mins, secs] = input.split(':').map(Number);
    if (isNaN(mins) || isNaN(secs)) return null;
    return mins * 60 + secs;
  }
  const mins = parseFloat(input);
  if (isNaN(mins) || mins <= 0) return null;
  return Math.round(mins * 60);
}

/**
 * Summarise diet macros from an array of entry values.
 * Returns rounded totals for display.
 */
export function sumMacros(entries: { calories: string; protein_g: string; fat_g: string; carbs_g: string }[]): {
  calories: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
} {
  return entries.reduce(
    (acc, e) => ({
      calories: acc.calories + parseFloat(e.calories || '0'),
      protein_g: acc.protein_g + parseFloat(e.protein_g || '0'),
      fat_g: acc.fat_g + parseFloat(e.fat_g || '0'),
      carbs_g: acc.carbs_g + parseFloat(e.carbs_g || '0'),
    }),
    { calories: 0, protein_g: 0, fat_g: 0, carbs_g: 0 },
  );
}
