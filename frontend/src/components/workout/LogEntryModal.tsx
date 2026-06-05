/**
 * LogEntryModal — form for recording actual workout performance.
 *
 * Design choice — modal over inline form:
 *   The log form needs access to all prescriptions in the current day
 *   (for the exercise selector) and appears only when the user triggers it.
 *   A modal keeps the workout view clean: the day's prescription and log
 *   tables are always visible without being broken up by an inline form.
 *   It also allows the user to reference the blue prescription table while
 *   filling in the red log form without losing context.
 *
 * Design choice — prescription selector shows exercise labels:
 *   The select dropdown shows "A — Bench Press", "B — Romanian Deadlift",
 *   matching the A/B/C labels visible in the blue prescription table above.
 *   The client never needs to remember prescription IDs — they use the same
 *   letter-based labels the coach assigned.
 *
 * Design choice — live tonnage preview:
 *   tonnage = sets × reps × load, recomputed on every keystroke in those
 *   fields. This mirrors the database GENERATED ALWAYS AS column, giving
 *   the client immediate feedback on training volume before saving.
 *   The preview is ephemeral and purely for display — the authoritative
 *   tonnage_kg value comes from the DB response after the log is saved.
 *
 * Design choice — readiness as button row, RPE as number input:
 *   Readiness (1–10, whole number) is selected via 10 tap buttons because
 *   the most important thing is a quick tap, not precision entry.
 *   RPE (1.0–10.0 with 0.5 increments) uses a number input because
 *   half-point precision matters in strength sports (7.5 is meaningfully
 *   different from 8.0) and a 20-button row would be unwieldy.
 *
 * Design choice — time input as "minutes" string, not seconds:
 *   Coaches and clients think in minutes ("took 20 minutes"). The schema
 *   stores seconds (time_taken_seconds) for precision. minutesToSeconds()
 *   handles both "20" (→ 1200s) and "1:30" (→ 90s) formats.
 */

import React, { useState, useEffect } from 'react';
import { useLogWorkout } from '../../hooks/useLogWorkout';
import { computeTonnage, formatLiveTonnage, todayIso, minutesToSeconds } from '../../utils/format';
import type { ProgramDayResponse, WorkoutPrescriptionResponse } from '../../types/api';

interface LogEntryModalProps {
  day: ProgramDayResponse;
  /** If provided, pre-selects this prescription in the dropdown. */
  defaultPrescriptionId?: string;
  onClose: () => void;
}

interface FormState {
  prescriptionId: string;
  isOrphanEntry: boolean;
  orphanExerciseName: string;
  loggedAt: string;
  actualSets: string;
  actualReps: string;
  actualLoadKg: string;
  actualRpe: string;
  readiness: number | null;
  timeMinutes: string;
  clientNotes: string;
}

const INITIAL_FORM: FormState = {
  prescriptionId: '',
  isOrphanEntry: false,
  orphanExerciseName: '',
  loggedAt: todayIso(),
  actualSets: '',
  actualReps: '',
  actualLoadKg: '',
  actualRpe: '',
  readiness: null,
  timeMinutes: '',
  clientNotes: '',
};

export function LogEntryModal({ day, defaultPrescriptionId, onClose }: LogEntryModalProps) {
  const { mutateAsync, isPending, isError, error } = useLogWorkout();
  const [form, setForm] = useState<FormState>({
    ...INITIAL_FORM,
    prescriptionId: defaultPrescriptionId ?? (day.prescriptions[0]?.id ?? ''),
    loggedAt: todayIso(),
  });

  // Live tonnage preview
  const liveTonnage = computeTonnage(form.actualSets, form.actualReps, form.actualLoadKg || null);

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  function update(field: keyof FormState, value: FormState[keyof FormState]) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function validate(): string | null {
    if (!form.isOrphanEntry && !form.prescriptionId) return 'Select an exercise.';
    if (form.isOrphanEntry && !form.orphanExerciseName.trim()) return 'Enter an exercise name.';
    const sets = parseInt(form.actualSets);
    const reps = parseInt(form.actualReps);
    if (!form.actualSets || sets < 1) return 'Sets must be at least 1.';
    if (!form.actualReps || reps < 1) return 'Reps must be at least 1.';
    if (form.actualRpe) {
      const rpe = parseFloat(form.actualRpe);
      if (isNaN(rpe) || rpe < 1 || rpe > 10) return 'RPE must be between 1 and 10.';
    }
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) { alert(validationError); return; }

    const selectedPrescription: WorkoutPrescriptionResponse | undefined = day.prescriptions.find(
      (p) => p.id === form.prescriptionId,
    );

    await mutateAsync({
      prescription_id: form.isOrphanEntry ? null : form.prescriptionId,
      exercise_name: form.isOrphanEntry
        ? form.orphanExerciseName.trim()
        : (selectedPrescription?.exercise_name ?? null),
      logged_at: form.loggedAt,
      actual_sets: parseInt(form.actualSets),
      actual_reps: parseInt(form.actualReps),
      actual_load_kg: form.actualLoadKg ? parseFloat(form.actualLoadKg) : null,
      actual_rpe: form.actualRpe ? parseFloat(form.actualRpe) : null,
      readiness: form.readiness,
      time_taken_seconds: minutesToSeconds(form.timeMinutes),
      client_notes: form.clientNotes.trim() || null,
    });

    onClose();
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Dimmed overlay */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />

      {/* Modal panel */}
      <div className="relative z-10 w-full sm:max-w-lg bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Log workout</h2>
            <p className="text-xs text-gray-500 mt-0.5">{day.label}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable form body */}
        <form onSubmit={handleSubmit} className="overflow-y-auto flex-1 px-5 py-4 space-y-5">

          {/* Exercise selector */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
              Exercise
            </label>
            {!form.isOrphanEntry ? (
              <select
                value={form.prescriptionId}
                onChange={(e) => update('prescriptionId', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                required
              >
                {day.prescriptions.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.exercise_label} — {p.exercise_name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                placeholder="Exercise name"
                value={form.orphanExerciseName}
                onChange={(e) => update('orphanExerciseName', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            )}
            <button
              type="button"
              onClick={() => update('isOrphanEntry', !form.isOrphanEntry)}
              className="mt-1.5 text-xs text-blue-600 hover:text-blue-700 underline-offset-2 hover:underline"
            >
              {form.isOrphanEntry ? '← Select from programme' : 'Not in my programme?'}
            </button>
          </div>

          {/* Date */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
              Date
            </label>
            <input
              type="date"
              value={form.loggedAt}
              onChange={(e) => update('loggedAt', e.target.value)}
              max={todayIso()}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {/* Sets × Reps × Load — three column layout */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
                Sets
              </label>
              <input
                type="number"
                min="1"
                max="20"
                step="1"
                placeholder="4"
                value={form.actualSets}
                onChange={(e) => update('actualSets', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-center"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
                Reps
              </label>
              <input
                type="number"
                min="1"
                max="100"
                step="1"
                placeholder="6"
                value={form.actualReps}
                onChange={(e) => update('actualReps', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-center"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
                Load (kg)
              </label>
              <input
                type="number"
                min="0"
                step="0.5"
                placeholder="BW"
                value={form.actualLoadKg}
                onChange={(e) => update('actualLoadKg', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-center"
              />
            </div>
          </div>

          {/* Live tonnage preview */}
          <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg">
            <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span className="text-xs text-gray-500">Volume:</span>
            <span className={`text-sm font-semibold tabular-nums ${liveTonnage ? 'text-gray-900' : 'text-gray-300'}`}>
              {formatLiveTonnage(liveTonnage)}
            </span>
          </div>

          {/* RPE + Readiness row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
                RPE <span className="text-gray-400 font-normal normal-case">(1–10)</span>
              </label>
              <input
                type="number"
                min="1"
                max="10"
                step="0.5"
                placeholder="8.0"
                value={form.actualRpe}
                onChange={(e) => update('actualRpe', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
                Readiness
              </label>
              <div className="flex gap-0.5">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => update('readiness', form.readiness === n ? null : n)}
                    className={`
                      flex-1 py-1.5 text-xs font-medium rounded transition-colors
                      ${form.readiness === n
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                      }
                    `}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Time + Notes */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
                Time <span className="text-gray-400 font-normal normal-case">(mins)</span>
              </label>
              <input
                type="text"
                placeholder="20"
                value={form.timeMinutes}
                onChange={(e) => update('timeMinutes', e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="col-span-1">
              <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">
                Notes
              </label>
              <textarea
                placeholder="Felt strong, paused every rep"
                value={form.clientNotes}
                onChange={(e) => update('clientNotes', e.target.value)}
                rows={1}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>
          </div>

          {/* Error message */}
          {isError && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
              {error?.message ?? 'Failed to save log. Please try again.'}
            </p>
          )}
        </form>

        {/* Footer actions */}
        <div className="px-5 py-4 border-t border-gray-100 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isPending}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="log-entry-form"
            disabled={isPending}
            onClick={handleSubmit as unknown as React.MouseEventHandler}
            className="px-5 py-2 text-sm font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? 'Saving…' : 'Save entry'}
          </button>
        </div>
      </div>
    </div>
  );
}
