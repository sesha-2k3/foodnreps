/**
 * ProgrammeBuilder — the workout programme hierarchy editor.
 *
 * Renders the full programme → weeks → days → prescriptions tree
 * with inline creation for weeks/days and a modal for prescriptions.
 *
 * Design choice — inline forms for weeks and days:
 *   When a coach clicks "+ Add week", a small text input appears inline
 *   at the bottom of the weeks list. They type the label ("Deload Week",
 *   "Week 1"), press Enter, and the week appears. No modal, no context
 *   switch. This communicates: "you are naming a container in this list."
 *
 *   Prescription creation uses a modal because a prescription has twelve
 *   fields across four conceptual groups. An inline form for twelve fields
 *   would break the table layout and force the coach to context-switch
 *   between the form and the surrounding prescriptions.
 *
 * Design choice — coach prescription columns show raw values:
 *   The client view shows reps_display ("6–8") and load_display ("70 kg")
 *   — pre-computed backend fields. The coach edit view shows reps_min,
 *   reps_max, prescribed_load_kg — raw values — because the coach needs
 *   to change 6–8 to 5–7 by editing individual numbers, not a display
 *   string. The FitnessTable receives a different column definition set
 *   depending on the view role.
 *
 * Design choice — optimistic prescription rows use placeholder labels:
 *   When a prescription is optimistically inserted into the cache, its
 *   exercise_label is computed client-side (order_index → "A", "B", "C").
 *   The server may compute slightly different labels if concurrent saves
 *   reorder the index. onSettled always invalidates and replaces the
 *   cache with authoritative server values.
 */

/**
 * ProgrammeBuilder — the workout programme hierarchy editor.
 *
 * Change from previous version:
 *   rolePrefix prop now accepts 'admin' in addition to CoachingRole | 'personal'.
 *   No other changes — useProgrammeMutations handles the URL/key difference.
 */

import React, { useState } from 'react';
import { FitnessTable } from '../../components/table/FitnessTable';
import type { FitnessColumnDef } from '../../components/table/FitnessTable';
import { AddPrescriptionModal } from './AddPrescriptionModal';
import type { PrescriptionFormData } from './AddPrescriptionModal';
import { useProgrammeMutations } from '../../hooks/useProgrammeMutations';
import { formatRpe, formatRest } from '../../utils/format';
import type {
  WorkoutProgramResponse,
  ProgramWeekResponse,
  ProgramDayResponse,
  WorkoutPrescriptionResponse,
  UpdatePrescriptionRequest,
} from '../../types/api';
import type { CoachingRole } from '../../hooks/useAssignedClients';

interface ProgrammeBuilderProps {
  clientId: string;
  clientName: string;
  rolePrefix: CoachingRole | 'personal' | 'admin'; // ← added 'admin'
  programme: WorkoutProgramResponse | null;
}

// ── Coach prescription row type ───────────────────────────────────────────────

interface CoachPrescriptionRow extends Record<string, unknown> {
  id: string;
  exercise_label: string;
  exercise_name: string;
  working_sets: string;
  reps_display: string;
  load_display: string;
  prescribed_rpe: string;
  rest_display: string;
  instructions: string;
}

const COACH_PRESCRIPTION_COLUMNS: FitnessColumnDef<CoachPrescriptionRow>[] = [
  { key: 'exercise_label', header: '',         width: 36,  editable: false },
  { key: 'exercise_name',  header: 'Exercise',              type: 'text'   },
  { key: 'working_sets',   header: 'Sets',     width: 64,  type: 'number' },
  { key: 'reps_display',   header: 'Reps',     width: 100, editable: false },
  { key: 'load_display',   header: 'Load',     width: 100, editable: false },
  { key: 'prescribed_rpe', header: 'RPE',      width: 72,  type: 'decimal' },
  { key: 'rest_display',   header: 'Rest',     width: 80,  editable: false },
  { key: 'instructions',   header: 'Notes',               type: 'text'   },
];

function toPrescriptionRow(p: WorkoutPrescriptionResponse): CoachPrescriptionRow {
  return {
    id: p.id,
    exercise_label: p.exercise_label,
    exercise_name: p.exercise_name,
    working_sets: p.working_sets != null ? String(p.working_sets) : '',
    reps_display: p.reps_display || '—',
    load_display: p.load_display || 'BW',
    prescribed_rpe: p.prescribed_rpe != null ? String(p.prescribed_rpe) : '',
    rest_display: formatRest(p.rest_seconds),
    instructions: p.instructions ?? '',
  };
}

function rowToUpdateRequest(row: CoachPrescriptionRow): UpdatePrescriptionRequest {
  return {
    exercise_name: (row.exercise_name as string) || undefined,
    working_sets: row.working_sets ? parseInt(row.working_sets as string) : null,
    prescribed_rpe: row.prescribed_rpe ? parseFloat(row.prescribed_rpe as string) : null,
    instructions: (row.instructions as string) || null,
  };
}

// ── Inline text input for week / day creation ─────────────────────────────────

function InlineAddForm({
  placeholder,
  onConfirm,
  onCancel,
  loading,
}: {
  placeholder: string;
  onConfirm: (label: string) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [value, setValue] = useState('');
  return (
    <div className="flex items-center gap-2 px-1">
      <input
        autoFocus
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && value.trim()) onConfirm(value.trim());
          if (e.key === 'Escape') onCancel();
        }}
        className="flex-1 px-3 py-2 text-sm border border-blue-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        disabled={loading}
      />
      <button
        type="button"
        onClick={() => value.trim() && onConfirm(value.trim())}
        disabled={!value.trim() || loading}
        className="px-3 py-2 text-xs font-medium bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-40"
      >
        {loading ? '…' : '✓'}
      </button>
      <button type="button" onClick={onCancel} disabled={loading}
        className="px-3 py-2 text-xs text-gray-500 hover:text-gray-700">
        ✕
      </button>
    </div>
  );
}

// ── Day section ───────────────────────────────────────────────────────────────

function DaySection({
  day,
  mutations,
}: {
  day: ProgramDayResponse;
  mutations: ReturnType<typeof useProgrammeMutations>;
}) {
  const [addingExercise, setAddingExercise] = useState(false);
  const rows = day.prescriptions.map(toPrescriptionRow);

  return (
    <div className="mb-5 last:mb-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center">
            <span className="text-[11px] font-bold text-gray-500">{day.day_number}</span>
          </div>
          <span className="text-sm font-semibold text-gray-800">{day.label}</span>
        </div>
        <button
          type="button"
          onClick={() => setAddingExercise(true)}
          className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add exercise
        </button>
      </div>

      <div className="ring-1 ring-blue-100 rounded-lg overflow-hidden">
        <FitnessTable<CoachPrescriptionRow>
          columns={COACH_PRESCRIPTION_COLUMNS}
          data={rows}
          editable={true}
          onRowEdit={async (row) => {
            await mutations.updatePrescription.mutateAsync({
              prescriptionId: row.id as string,
              data: rowToUpdateRequest(row),
            });
          }}
          onRowDelete={async (id) => {
            await mutations.deletePrescription.mutateAsync(id);
          }}
          emptyMessage="No exercises yet — click 'Add exercise' to build this day."
        />
      </div>

      {addingExercise && (
        <AddPrescriptionModal
          dayLabel={day.label}
          existingCount={day.prescriptions.length}
          onAdd={async (data) => {
            await mutations.addPrescription.mutateAsync({ dayId: day.id, data });
          }}
          onClose={() => setAddingExercise(false)}
        />
      )}
    </div>
  );
}

// ── Week section ──────────────────────────────────────────────────────────────

function WeekSection({
  week,
  defaultOpen,
  mutations,
}: {
  week: ProgramWeekResponse;
  defaultOpen: boolean;
  mutations: ReturnType<typeof useProgrammeMutations>;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [addingDay, setAddingDay] = useState(false);

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
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="divide-y divide-gray-100">
          {week.days.map((day) => (
            <div key={day.id} className="px-5 py-4">
              <DaySection day={day} mutations={mutations} />
            </div>
          ))}

          {week.days.length === 0 && !addingDay && (
            <p className="px-5 py-5 text-sm text-gray-400 italic text-center">No days yet.</p>
          )}

          <div className="px-5 py-3">
            {addingDay ? (
              <InlineAddForm
                placeholder="Day label, e.g. Upper Body"
                loading={mutations.addDay.isPending}
                onConfirm={async (label) => {
                  await mutations.addDay.mutateAsync({
                    weekId: week.id,
                    data: { day_number: week.days.length + 1, label },
                  });
                  setAddingDay(false);
                }}
                onCancel={() => setAddingDay(false)}
              />
            ) : (
              <button
                type="button"
                onClick={() => setAddingDay(true)}
                className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add day
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Create programme form ─────────────────────────────────────────────────────

function CreateProgrammeForm({
  clientName,
  onCreate,
  isPending,
}: {
  clientName: string;
  onCreate: (name: string) => Promise<void>;
  isPending: boolean;
}) {
  const [name, setName] = useState('');

  return (
    <div className="max-w-md mx-auto text-center py-16">
      <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
        </svg>
      </div>
      <h3 className="text-base font-semibold text-gray-900 mb-1">No programme for {clientName}</h3>
      <p className="text-sm text-gray-500 mb-6">Create one to get started.</p>
      <div className="flex gap-2 max-w-sm mx-auto">
        <input
          type="text"
          placeholder="Programme name, e.g. 12-Week Strength Block"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && name.trim()) void onCreate(name.trim()); }}
          className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="button"
          disabled={!name.trim() || isPending}
          onClick={() => void onCreate(name.trim())}
          className="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-40"
        >
          {isPending ? '…' : 'Create'}
        </button>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function ProgrammeBuilder({
  clientId,
  clientName,
  rolePrefix,
  programme,
}: ProgrammeBuilderProps) {
  const mutations = useProgrammeMutations(clientId, rolePrefix);
  const [addingWeek, setAddingWeek] = useState(false);

  if (!programme) {
    return (
      <CreateProgrammeForm
        clientName={clientName}
        onCreate={async (name) => { await mutations.createProgramme.mutateAsync({ name }); }}
        isPending={mutations.createProgramme.isPending}
      />
    );
  }

  return (
    <div>
      <div className="mb-5 pb-4 border-b border-gray-100">
        <h2 className="text-lg font-bold text-gray-900">{programme.name}</h2>
        {programme.coach_notes && (
          <p className="mt-1 text-sm text-gray-600">{programme.coach_notes}</p>
        )}
      </div>

      {programme.weeks.length === 0 && !addingWeek && (
        <p className="text-sm text-gray-400 italic text-center py-10">
          No weeks yet — add the first one below.
        </p>
      )}

      {programme.weeks.map((week, idx) => (
        <WeekSection key={week.id} week={week} defaultOpen={idx === 0} mutations={mutations} />
      ))}

      <div className="mt-3">
        {addingWeek ? (
          <div className="p-4 rounded-xl border-2 border-dashed border-gray-200">
            <InlineAddForm
              placeholder="Week label, e.g. Week 1 or Deload Week"
              loading={mutations.addWeek.isPending}
              onConfirm={async (label) => {
                await mutations.addWeek.mutateAsync({
                  week_number: programme.weeks.length + 1,
                  label,
                });
                setAddingWeek(false);
              }}
              onCancel={() => setAddingWeek(false)}
            />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setAddingWeek(true)}
            className="w-full py-3 flex items-center justify-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-700 border-2 border-dashed border-gray-200 hover:border-gray-300 rounded-xl transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add week
          </button>
        )}
      </div>
    </div>
  );
}