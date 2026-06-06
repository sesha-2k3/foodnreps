/**
 * WorkoutView — renders the client's assigned workout programme.
 *
 * Hierarchy rendered:
 *   WorkoutProgramme
 *     └── Week (collapsible; first week expanded by default)
 *           └── Day
 *                 ├── Prescription table (blue — read-only: what to do)
 *                 └── Log table (amber — existing entries + Log button)
 *
 * Design choice — two FitnessTable instances per day:
 *   The prescription table (blue) and log table (amber) are separate
 *   FitnessTable instances with different column definitions, row types,
 *   and editable props. They share the FitnessTable facade but render
 *   completely independent data shapes. Using the same component for
 *   both keeps the table rendering consistent; the editable=false vs
 *   editable=false+standalone-button distinction keeps their concerns
 *   cleanly separated.
 *
 * Design choice — log table uses editable=false with standalone button:
 *   workout_logs is append-only (no update path in the repository).
 *   Passing editable=true to the log table would render an action column
 *   with no row-level actions (no Edit, no Delete), wasting column width.
 *   A standalone "Log workout" button outside the table is cleaner UX
 *   and communicates that logging is a session-level action, not a
 *   row-level action.
 *
 * Design choice — view-model row types, not raw API types:
 *   FitnessTable<T> requires T extends Record<string, unknown>. The raw
 *   API types (WorkoutPrescriptionResponse, WorkoutLogResponse) contain
 *   nested objects (logs array on prescription) that FitnessTable does
 *   not know how to render. View-model row types (PrescriptionRow,
 *   DayLogRow) are flat objects with exactly the columns to display.
 *   The toPrescriptionRow / toDayLogRows mapping functions are the
 *   single point of translation — analogous to the repository's
 *   _to_entity() / _to_model() pattern in the backend.
 *
 * Design choice — flat day-level log table:
 *   All logs for a day are shown in one table, not separate tables per
 *   exercise. The exercise label ("A", "B") identifies which prescription
 *   each log belongs to. This matches how clients experience logging:
 *   "what did I do today" rather than per-exercise history lists.
 *
 * Design choice — collapsible weeks, first week expanded:
 *   With a 12-week programme, all weeks open would require scrolling
 *   past hundreds of rows. The first week defaults open. Collapse state
 *   is local React state (not persisted) so clients always see week 1
 *   on first load, the most relevant starting point.
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { FitnessTable } from '../../components/table/FitnessTable';
import type { FitnessColumnDef } from '../../components/table/FitnessTable';
import { LogEntryModal } from '../../components/workout/LogEntryModal';
import { useClientWorkout } from '../../hooks/useClientWorkout';
import {
  formatLoad,
  formatRest,
  formatTonnage,
  formatElapsedTime,
  formatDate,
  formatRpe,
} from '../../utils/format';
import type {
  WorkoutProgramResponse,
  ProgramWeekResponse,
  ProgramDayResponse,
  WorkoutPrescriptionResponse,
} from '../../types/api';

// ── View-model row types ──────────────────────────────────────────────────────
// These flat types satisfy FitnessTable<T extends Record<string, unknown>>.
// They contain only the columns to display — no nested objects.

interface PrescriptionRow extends Record<string, unknown> {
  id: string;
  exercise_label: string;
  exercise_name: string;
  working_sets: string;      // "4", "—"
  reps_display: string;      // "6–8", "max reps"
  load_display: string;      // "70 kg", "BW"
  rpe_display: string;       // "@ 8", "—"
  rest_display: string;      // "3 min", "1:30"
  instructions: string;
}

interface DayLogRow extends Record<string, unknown> {
  id: string;
  exercise_label: string;
  exercise_name: string;
  logged_at_display: string; // "8 Apr"
  actual_sets: number;
  actual_reps: number;
  load_display: string;      // "70 kg", "BW"
  rpe_display: string;       // "@ 8.5", "—"
  tonnage_display: string;   // "1,960 kg", "—"
}

// ── Column definitions ────────────────────────────────────────────────────────

const PRESCRIPTION_COLUMNS: FitnessColumnDef<PrescriptionRow>[] = [
  { key: 'exercise_label', header: '',           width: 36,  editable: false },
  { key: 'exercise_name',  header: 'Exercise',              editable: false },
  { key: 'working_sets',   header: 'Sets',       width: 60,  editable: false },
  { key: 'reps_display',   header: 'Reps',       width: 90,  editable: false },
  { key: 'load_display',   header: 'Load',       width: 100, editable: false },
  { key: 'rpe_display',    header: 'RPE',        width: 72,  editable: false },
  { key: 'rest_display',   header: 'Rest',       width: 80,  editable: false },
  { key: 'instructions',   header: 'Notes',                  editable: false },
];

const LOG_COLUMNS: FitnessColumnDef<DayLogRow>[] = [
  { key: 'exercise_label',    header: '',        width: 36,  editable: false },
  { key: 'exercise_name',     header: 'Exercise',            editable: false },
  { key: 'logged_at_display', header: 'Date',   width: 76,  editable: false },
  { key: 'actual_sets',       header: 'Sets',   width: 60,  editable: false },
  { key: 'actual_reps',       header: 'Reps',   width: 60,  editable: false },
  { key: 'load_display',      header: 'Load',   width: 100, editable: false },
  { key: 'rpe_display',       header: 'RPE',    width: 72,  editable: false },
  { key: 'tonnage_display',   header: 'Volume', width: 110, editable: false },
];

// ── Row mapping functions ─────────────────────────────────────────────────────
// The translation layer between API response types and view-model row types.
// Analogous to repository _to_entity() — one place to update when field names change.

function toPrescriptionRow(p: WorkoutPrescriptionResponse): PrescriptionRow {
  return {
    id: p.id,
    exercise_label: p.exercise_label,
    exercise_name: p.exercise_name,
    working_sets: p.working_sets != null ? String(p.working_sets) : '—',
    reps_display: p.reps_display,
    load_display: p.load_display,
    rpe_display: formatRpe(p.prescribed_rpe),
    rest_display: formatRest(p.rest_seconds),
    instructions: p.instructions ?? '',
  };
}

function toDayLogRows(day: ProgramDayResponse): DayLogRow[] {
  return day.prescriptions
    .flatMap((p) =>
      (p.logs ?? []).map((log) => ({   // ← add ?? []
        id: log.id,
        exercise_label: p.exercise_label,
        exercise_name: p.exercise_name,
        logged_at_display: formatDate(log.logged_at),
        actual_sets: log.actual_sets,
        actual_reps: log.actual_reps,
        load_display: formatLoad(log.actual_load_kg),
        rpe_display: formatRpe(log.actual_rpe),
        tonnage_display: formatTonnage(log.tonnage_kg),
      })),
    )
    .sort((a, b) => b.logged_at_display.localeCompare(a.logged_at_display));
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ProgrammeHeader({ programme }: { programme: WorkoutProgramResponse }) {
  return (
    <div className="mb-6">
      <h1 className="text-xl font-bold text-gray-900">{programme.name}</h1>
      {programme.coach_notes && (
        <p className="mt-1 text-sm text-gray-600 bg-gray-50 rounded-lg px-4 py-3 border-l-4 border-gray-300">
          {programme.coach_notes}
        </p>
      )}
    </div>
  );
}

function DaySection({
  day,
  onLogClick,
}: {
  day: ProgramDayResponse;
  onLogClick: (day: ProgramDayResponse) => void;
}) {
  const prescriptionRows = day.prescriptions.map(toPrescriptionRow);
  const logRows = toDayLogRows(day);
  const totalLogCount = day.prescriptions.reduce((sum, p) => sum + p.logs.length, 0);

  return (
    <div className="mb-6 last:mb-0">
      {/* Day header */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
          <span className="text-xs font-bold text-gray-500">{day.day_number}</span>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-800">{day.label}</h3>
          {day.notes && <p className="text-xs text-gray-500">{day.notes}</p>}
        </div>
      </div>

      {/* Prescription table — BLUE side */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1.5 px-1">
          <div className="w-2 h-2 rounded-full bg-blue-400" />
          <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider">
            Programme
          </span>
        </div>
        <div className="ring-1 ring-blue-100 rounded-lg overflow-hidden">
          <FitnessTable<PrescriptionRow>
            columns={PRESCRIPTION_COLUMNS}
            data={prescriptionRows}
            editable={false}
            emptyMessage="No exercises in this day yet."
          />
        </div>
      </div>

      {/* Log table — AMBER side */}
      <div>
        <div className="flex items-center justify-between mb-1.5 px-1">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider">
              Your log
            </span>
            {totalLogCount > 0 && (
              <span className="text-[10px] text-gray-400">({totalLogCount} entries)</span>
            )}
          </div>
          <button
            type="button"
            onClick={() => onLogClick(day)}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-lg transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Log workout
          </button>
        </div>
        <div className="ring-1 ring-amber-100 rounded-lg overflow-hidden">
          <FitnessTable<DayLogRow>
            columns={LOG_COLUMNS}
            data={logRows}
            editable={false}
            emptyMessage="No entries yet — tap 'Log workout' after your session."
          />
        </div>
      </div>
    </div>
  );
}

function WeekSection({
  week,
  defaultOpen,
  onLogClick,
}: {
  week: ProgramWeekResponse;
  defaultOpen: boolean;
  onLogClick: (day: ProgramDayResponse) => void;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const totalLogs = week.days.reduce(
    (sum, d) => sum + d.prescriptions.reduce((s, p) => s + p.logs.length, 0),
    0,
  );

  return (
    <div className="mb-4 rounded-xl border border-gray-200 overflow-hidden">
      {/* Week header — clickable to expand/collapse */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-gray-800 text-white hover:bg-gray-700 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-widest w-6 text-center">
            W{week.week_number}
          </span>
          <span className="text-sm font-semibold">{week.label}</span>
          {week.notes && (
            <span className="text-xs text-gray-400 font-normal">— {week.notes}</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {totalLogs > 0 && (
            <span className="text-xs text-gray-400">{totalLogs} logged</span>
          )}
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded week content */}
      {isOpen && (
        <div className="divide-y divide-gray-100">
          {week.days.map((day) => (
            <div key={day.id} className="px-5 py-5">
              <DaySection day={day} onLogClick={onLogClick} />
            </div>
          ))}
          {week.days.length === 0 && (
            <p className="px-5 py-6 text-sm text-gray-400 text-center italic">
              No training days in this week.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function WorkoutSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
      <div className="h-7 w-64 bg-gray-200 rounded animate-pulse" />
      <div className="h-4 w-96 bg-gray-100 rounded animate-pulse" />
      {[1, 2].map((i) => (
        <div key={i} className="rounded-xl border border-gray-200 overflow-hidden">
          <div className="h-12 bg-gray-200 animate-pulse" />
          <div className="p-5 space-y-4">
            {[1, 2].map((j) => (
              <div key={j} className="space-y-2">
                <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
                <div className="h-24 bg-gray-50 rounded-lg animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function NoAssignedProgramme() {
  return (
    <div className="max-w-lg mx-auto px-4 py-16 text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-900 mb-2">No programme assigned yet</h2>
      <p className="text-sm text-gray-500 mb-6">
        Your coach hasn't assigned a programme to you yet. In the meantime, you can manage your own training.
      </p>
      <Link
        to="/personal/workout"
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
      >
        Go to personal workout
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </Link>
    </div>
  );
}

// ── Main view ─────────────────────────────────────────────────────────────────

export function WorkoutView() {
  const { data: programme, isLoading, isError } = useClientWorkout();
  const [logModalDay, setLogModalDay] = useState<ProgramDayResponse | null>(null);

  if (isLoading) return <WorkoutSkeleton />;

  if (isError) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-sm text-red-600">Failed to load your workout programme. Please refresh the page.</p>
      </div>
    );
  }

  if (!programme) return <NoAssignedProgramme />;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <ProgrammeHeader programme={programme} />

      {programme.weeks.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-12 italic">
          Your programme has no weeks yet. Your coach will add them soon.
        </p>
      ) : (
        programme.weeks.map((week, idx) => (
          <WeekSection
            key={week.id}
            week={week}
            defaultOpen={idx === 0}  // First week open; all others collapsed
            onLogClick={setLogModalDay}
          />
        ))
      )}

      {/* Log entry modal — scoped to a specific day */}
      {logModalDay && (
        <LogEntryModal
          day={logModalDay}
          onClose={() => setLogModalDay(null)}
        />
      )}
    </div>
  );
}

export default WorkoutView;
