/**
 * PersonalWorkout — self-managed workout programme view.
 *
 * Shown when a client has no assigned coach, or when any authenticated
 * user visits /personal/workout. The client acts as their own coach:
 * they can edit their own prescription entries (sets, reps, load targets).
 *
 * Design choice — editable=true for prescriptions in personal mode:
 *   The only difference between WorkoutView (assigned) and PersonalWorkout
 *   is editability of prescription rows. In assigned mode, the coach owns
 *   the prescription — the client reads it. In personal mode, the client
 *   IS the coach — they write their own prescription and log against it.
 *   A single FitnessTable prop change (editable) unlocks this.
 *
 * Design choice — Programme Builder deferred to Sprint 8:
 *   Creating the week/day structure (adding weeks, naming days, structuring
 *   the hierarchy) is the Programme Builder — the most complex UI in the
 *   app. That is Sprint 8's scope. Sprint 7 handles the read + log + edit
 *   existing entries use cases. If no personal programme exists, the view
 *   shows an empty state with a clear explanation.
 *
 * Design choice — same hooks, different endpoint:
 *   usePersonalWorkout() fetches GET /personal/workout and
 *   usePersonalDiet() fetches GET /personal/diet. The mutation
 *   useLogWorkout invalidates both CLIENT_WORKOUT_KEY and PERSONAL_WORKOUT_KEY
 *   so this view refreshes correctly after a log submission.
 */

import React, { useState } from 'react';
import { FitnessTable } from '../../components/table/FitnessTable';
import type { FitnessColumnDef } from '../../components/table/FitnessTable';
import { LogEntryModal } from '../../components/workout/LogEntryModal';
import { usePersonalWorkout } from '../../hooks/useClientWorkout';
import {
  formatLoad,
  formatRest,
  formatTonnage,
  formatDate,
  formatRpe,
} from '../../utils/format';
import type {
  WorkoutProgramResponse,
  ProgramWeekResponse,
  ProgramDayResponse,
  WorkoutPrescriptionResponse,
} from '../../types/api';

// ── View-model types ──────────────────────────────────────────────────────────

interface PersonalPrescriptionRow extends Record<string, unknown> {
  id: string;
  exercise_label: string;
  exercise_name: string;
  working_sets: string;
  reps_display: string;
  load_display: string;
  rest_display: string;
  instructions: string;
}

interface DayLogRow extends Record<string, unknown> {
  id: string;
  exercise_label: string;
  exercise_name: string;
  logged_at_display: string;
  actual_sets: number;
  actual_reps: number;
  load_display: string;
  rpe_display: string;
  tonnage_display: string;
}

// ── Column definitions ────────────────────────────────────────────────────────
// editable: true allows inline editing of prescription targets (sets, reps, load)

const PERSONAL_PRESCRIPTION_COLUMNS: FitnessColumnDef<PersonalPrescriptionRow>[] = [
  { key: 'exercise_label', header: '',           width: 36,  editable: false },
  { key: 'exercise_name',  header: 'Exercise',              type: 'text'   },
  { key: 'working_sets',   header: 'Sets',       width: 60,  type: 'number' },
  { key: 'reps_display',   header: 'Reps',       width: 90,  type: 'text'   },
  { key: 'load_display',   header: 'Load',       width: 100, type: 'text'   },
  { key: 'rest_display',   header: 'Rest',       width: 80,  editable: false },
  { key: 'instructions',   header: 'Notes',                  type: 'text'   },
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

// ── Mapping functions ─────────────────────────────────────────────────────────

function toPrescriptionRow(p: WorkoutPrescriptionResponse): PersonalPrescriptionRow {
  return {
    id: p.id,
    exercise_label: p.exercise_label,
    exercise_name: p.exercise_name,
    working_sets: p.working_sets != null ? String(p.working_sets) : '',
    reps_display: p.reps_display,
    load_display: p.load_display,
    rest_display: formatRest(p.rest_seconds),
    instructions: p.instructions ?? '',
  };
}

function toDayLogRows(day: ProgramDayResponse): DayLogRow[] {
  return day.prescriptions
    .flatMap((p) =>
      p.logs.map((log) => ({
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

function PersonalDaySection({
  day,
  onLogClick,
  onPrescriptionEdit,
}: {
  day: ProgramDayResponse;
  onLogClick: (day: ProgramDayResponse) => void;
  onPrescriptionEdit: (row: PersonalPrescriptionRow) => Promise<void>;
}) {
  const prescriptionRows = day.prescriptions.map(toPrescriptionRow);
  const logRows = toDayLogRows(day);

  return (
    <div className="mb-6 last:mb-0">
      <div className="flex items-center gap-3 mb-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
          <span className="text-xs font-bold text-gray-500">{day.day_number}</span>
        </div>
        <h3 className="text-sm font-semibold text-gray-800">{day.label}</h3>
      </div>

      {/* Prescription table — editable in personal mode */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1.5 px-1">
          <div className="w-2 h-2 rounded-full bg-blue-400" />
          <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider">
            Your programme
          </span>
          <span className="text-[10px] text-gray-400">(tap Edit to update targets)</span>
        </div>
        <div className="ring-1 ring-blue-100 rounded-lg overflow-hidden">
          <FitnessTable<PersonalPrescriptionRow>
            columns={PERSONAL_PRESCRIPTION_COLUMNS}
            data={prescriptionRows}
            editable={true}
            onRowEdit={onPrescriptionEdit}
            emptyMessage="No exercises yet. Use the programme builder to add them."
          />
        </div>
      </div>

      {/* Log table */}
      <div>
        <div className="flex items-center justify-between mb-1.5 px-1">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider">
              Your log
            </span>
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
            emptyMessage="No entries yet."
          />
        </div>
      </div>
    </div>
  );
}

function PersonalWeekSection({
  week,
  defaultOpen,
  onLogClick,
  onPrescriptionEdit,
}: {
  week: ProgramWeekResponse;
  defaultOpen: boolean;
  onLogClick: (day: ProgramDayResponse) => void;
  onPrescriptionEdit: (row: PersonalPrescriptionRow) => Promise<void>;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="mb-4 rounded-xl border border-gray-200 overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((p) => !p)}
        className="w-full flex items-center justify-between px-5 py-3.5 bg-gray-800 text-white hover:bg-gray-700 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-widest w-6 text-center">
            W{week.week_number}
          </span>
          <span className="text-sm font-semibold">{week.label}</span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="divide-y divide-gray-100">
          {week.days.map((day) => (
            <div key={day.id} className="px-5 py-5">
              <PersonalDaySection
                day={day}
                onLogClick={onLogClick}
                onPrescriptionEdit={onPrescriptionEdit}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NoPersonalProgramme() {
  return (
    <div className="max-w-lg mx-auto px-4 py-16 text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-900 mb-2">No personal programme yet</h2>
      <p className="text-sm text-gray-500 mb-2">
        Create your own workout programme to start training independently.
      </p>
      <p className="text-xs text-gray-400 mb-6">
        The programme builder is coming soon. It will let you structure weeks, days, and exercises exactly how you want.
      </p>
      {/* Placeholder — Create programme button wired in Sprint 8 */}
      <button
        type="button"
        disabled
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-200 text-gray-400 text-sm font-medium rounded-lg cursor-not-allowed"
      >
        Create programme (coming soon)
      </button>
    </div>
  );
}

// ── Main view ─────────────────────────────────────────────────────────────────

export function PersonalWorkout() {
  const { data: programme, isLoading } = usePersonalWorkout();
  const [logModalDay, setLogModalDay] = useState<ProgramDayResponse | null>(null);

  // Prescription edit handler — calls PATCH /personal/workout/prescriptions/:id
  // Wired fully in Sprint 8 when the prescription mutation hook is built.
  const handlePrescriptionEdit = async (_row: PersonalPrescriptionRow): Promise<void> => {
    // TODO Sprint 8: wire to usePrescriptionUpdate mutation
    console.warn('Prescription update not yet wired. Sprint 8 will implement this.');
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-4">
        <div className="h-7 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="h-48 bg-gray-100 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!programme) return <NoPersonalProgramme />;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            Personal
          </span>
        </div>
        <h1 className="text-xl font-bold text-gray-900">{programme.name}</h1>
        {programme.coach_notes && (
          <p className="mt-1 text-sm text-gray-600 bg-gray-50 rounded-lg px-4 py-3 border-l-4 border-gray-300">
            {programme.coach_notes}
          </p>
        )}
      </div>

      {programme.weeks.map((week, idx) => (
        <PersonalWeekSection
          key={week.id}
          week={week}
          defaultOpen={idx === 0}
          onLogClick={setLogModalDay}
          onPrescriptionEdit={handlePrescriptionEdit}
        />
      ))}

      {logModalDay && (
        <LogEntryModal
          day={logModalDay}
          onClose={() => setLogModalDay(null)}
        />
      )}
    </div>
  );
}

export default PersonalWorkout;
