/**
 * AddPrescriptionModal — exercise prescription creation form.
 *
 * Design choice — field-type toggles for reps and load:
 *   Reps can be Fixed (single number), Range (min–max), or Open-ended
 *   (free text: "max reps", "AMRAP"). Showing all three sets of inputs
 *   at once would be confusing. A segmented toggle reveals only the
 *   relevant inputs for the chosen reps type.
 *
 *   Load can be Bodyweight (no input), Kilograms (decimal), or Descriptor
 *   (text: "BW+20", "Strict", "Band"). Same logic applies.
 *
 *   These toggles directly reflect the schema's value-object design for
 *   reps (reps_min + reps_max + reps_note) and load (prescribed_load_kg +
 *   prescribed_load_text) — each combination maps cleanly to a distinct
 *   toggle state.
 *
 * Design choice — order_index computed by caller, not user:
 *   The caller passes the current number of prescriptions in the day.
 *   The new prescription gets order_index = count + 1. The coach never
 *   sees or sets the order_index directly; they reorder via drag-and-drop
 *   (Phase 2 feature). This matches the schema design: order_index is an
 *   integer sort key, not a user-facing field.
 *
 * Design choice — form validation mirrors the DB CHECK constraint:
 *   The schema has CHECK (reps_min IS NOT NULL OR reps_note IS NOT NULL).
 *   The modal enforces this before submission: Fixed and Range modes
 *   require reps_min; Open-ended mode requires reps_note. No invalid
 *   prescription can be submitted.
 */

import React, { useState } from 'react';

interface AddPrescriptionModalProps {
  dayLabel: string;
  /** Current prescription count in this day — used to compute order_index. */
  existingCount: number;
  onAdd: (data: PrescriptionFormData) => Promise<void>;
  onClose: () => void;
}

export interface PrescriptionFormData {
  exercise_name: string;
  order_index: number;
  warmup_sets: number | null;
  working_sets: number | null;
  reps_min: number | null;
  reps_max: number | null;
  reps_note: string | null;
  prescribed_load_kg: number | null;
  prescribed_load_text: string | null;
  prescribed_rpe: number | null;
  prescribed_rir: number | null;
  rest_seconds: number | null;
  instructions: string | null;
}

type RepsType = 'fixed' | 'range' | 'open';
type LoadType = 'bodyweight' | 'kg' | 'descriptor';

const INITIAL_STATE = {
  exerciseName: '',
  warmupSets: '',
  workingSets: '',
  repsType: 'fixed' as RepsType,
  repsFixed: '',
  repsMin: '',
  repsMax: '',
  repsNote: '',
  loadType: 'kg' as LoadType,
  loadKg: '',
  loadText: '',
  rpe: '',
  rir: '',
  restSeconds: '',
  instructions: '',
};

function SegmentedToggle<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex rounded-lg border border-gray-200 overflow-hidden divide-x divide-gray-200">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`flex-1 px-3 py-1.5 text-xs font-medium transition-colors ${
            value === opt.value
              ? 'bg-gray-800 text-white'
              : 'bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      {children}
    </div>
  );
}

function NumberInput({
  placeholder,
  value,
  onChange,
  min = '0',
  step = '1',
}: {
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  min?: string;
  step?: string;
}) {
  return (
    <input
      type="number"
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      min={min}
      step={step}
      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
    />
  );
}

export function AddPrescriptionModal({
  dayLabel,
  existingCount,
  onAdd,
  onClose,
}: AddPrescriptionModalProps) {
  const [form, setForm] = useState(INITIAL_STATE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(field: keyof typeof INITIAL_STATE, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function validate(): string | null {
    if (!form.exerciseName.trim()) return 'Exercise name is required.';
    if (!form.workingSets || parseInt(form.workingSets) < 1)
      return 'Working sets must be at least 1.';
    if (form.repsType === 'fixed' && !form.repsFixed)
      return 'Enter the number of reps.';
    if (form.repsType === 'range' && (!form.repsMin || !form.repsMax))
      return 'Enter both min and max reps.';
    if (form.repsType === 'open' && !form.repsNote.trim())
      return 'Describe the rep scheme (e.g. "max reps").';
    if (form.loadType === 'kg' && form.loadKg && parseFloat(form.loadKg) < 0)
      return 'Load cannot be negative.';
    if (form.rpe && (parseFloat(form.rpe) < 1 || parseFloat(form.rpe) > 10))
      return 'RPE must be between 1 and 10.';
    return null;
  }

  function buildPayload(): PrescriptionFormData {
    const repsMin =
      form.repsType === 'fixed'
        ? parseInt(form.repsFixed) || null
        : form.repsType === 'range'
        ? parseInt(form.repsMin) || null
        : null;

    const repsMax =
      form.repsType === 'fixed'
        ? parseInt(form.repsFixed) || null
        : form.repsType === 'range'
        ? parseInt(form.repsMax) || null
        : null;

    return {
      exercise_name: form.exerciseName.trim(),
      order_index: existingCount + 1,
      warmup_sets: form.warmupSets ? parseInt(form.warmupSets) : null,
      working_sets: parseInt(form.workingSets),
      reps_min: repsMin,
      reps_max: repsMax,
      reps_note: form.repsType === 'open' ? form.repsNote.trim() || null : null,
      prescribed_load_kg:
        form.loadType === 'kg' && form.loadKg ? parseFloat(form.loadKg) : null,
      prescribed_load_text:
        form.loadType === 'descriptor' ? form.loadText.trim() || null : null,
      prescribed_rpe: form.rpe ? parseFloat(form.rpe) : null,
      prescribed_rir: form.rir ? parseInt(form.rir) : null,
      rest_seconds: form.restSeconds ? parseInt(form.restSeconds) : null,
      instructions: form.instructions.trim() || null,
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const validationError = validate();
    if (validationError) { setError(validationError); return; }
    setSaving(true);
    try {
      await onAdd(buildPayload());
      onClose();
    } catch {
      setError('Failed to save exercise. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />
      <div className="relative z-10 w-full sm:max-w-xl bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl max-h-[92vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Add exercise</h2>
            <p className="text-xs text-gray-400 mt-0.5">{dayLabel}</p>
          </div>
          <button type="button" onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <form onSubmit={handleSubmit} className="overflow-y-auto flex-1 px-5 py-5 space-y-5">

          {/* Exercise name */}
          <FieldRow label="Exercise">
            <input
              type="text"
              placeholder="e.g. Bench Press, Romanian Deadlift"
              value={form.exerciseName}
              onChange={(e) => set('exerciseName', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
              required
            />
          </FieldRow>

          {/* Sets row */}
          <div className="grid grid-cols-2 gap-3">
            <FieldRow label="Working sets">
              <NumberInput placeholder="4" value={form.workingSets} onChange={(v) => set('workingSets', v)} min="1" />
            </FieldRow>
            <FieldRow label="Warm-up sets (opt)">
              <NumberInput placeholder="2" value={form.warmupSets} onChange={(v) => set('warmupSets', v)} />
            </FieldRow>
          </div>

          {/* Reps */}
          <FieldRow label="Reps">
            <div className="space-y-2">
              <SegmentedToggle
                options={[
                  { value: 'fixed' as RepsType, label: 'Fixed' },
                  { value: 'range' as RepsType, label: 'Range' },
                  { value: 'open' as RepsType, label: 'Open-ended' },
                ]}
                value={form.repsType}
                onChange={(v) => set('repsType', v)}
              />
              {form.repsType === 'fixed' && (
                <NumberInput placeholder="5" value={form.repsFixed} onChange={(v) => set('repsFixed', v)} min="1" />
              )}
              {form.repsType === 'range' && (
                <div className="grid grid-cols-2 gap-2">
                  <NumberInput placeholder="Min (6)" value={form.repsMin} onChange={(v) => set('repsMin', v)} min="1" />
                  <NumberInput placeholder="Max (8)" value={form.repsMax} onChange={(v) => set('repsMax', v)} min="1" />
                </div>
              )}
              {form.repsType === 'open' && (
                <input type="text" placeholder="e.g. max reps, AMRAP, stop 2 reps short of failure"
                  value={form.repsNote} onChange={(e) => set('repsNote', e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              )}
            </div>
          </FieldRow>

          {/* Load */}
          <FieldRow label="Load">
            <div className="space-y-2">
              <SegmentedToggle
                options={[
                  { value: 'bodyweight' as LoadType, label: 'Bodyweight' },
                  { value: 'kg' as LoadType, label: 'Kg' },
                  { value: 'descriptor' as LoadType, label: 'Descriptor' },
                ]}
                value={form.loadType}
                onChange={(v) => set('loadType', v)}
              />
              {form.loadType === 'kg' && (
                <NumberInput placeholder="70" value={form.loadKg} onChange={(v) => set('loadKg', v)} step="0.5" />
              )}
              {form.loadType === 'descriptor' && (
                <input type="text" placeholder="e.g. BW+20, Strict, Band"
                  value={form.loadText} onChange={(e) => set('loadText', e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              )}
            </div>
          </FieldRow>

          {/* Intensity + rest */}
          <div className="grid grid-cols-3 gap-3">
            <FieldRow label="RPE target">
              <NumberInput placeholder="8.0" value={form.rpe} onChange={(v) => set('rpe', v)} min="1" step="0.5" />
            </FieldRow>
            <FieldRow label="RIR target">
              <NumberInput placeholder="2" value={form.rir} onChange={(v) => set('rir', v)} />
            </FieldRow>
            <FieldRow label="Rest (s)">
              <NumberInput placeholder="180" value={form.restSeconds} onChange={(v) => set('restSeconds', v)} />
            </FieldRow>
          </div>

          {/* Instructions */}
          <FieldRow label="Instructions (optional)">
            <textarea
              placeholder="e.g. Pause 1s at bottom, control the eccentric"
              value={form.instructions}
              onChange={(e) => set('instructions', e.target.value)}
              rows={2}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </FieldRow>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
          )}
        </form>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-100 flex justify-end gap-3">
          <button type="button" onClick={onClose} disabled={saving}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            Cancel
          </button>
          <button type="submit" disabled={saving} onClick={handleSubmit as unknown as React.MouseEventHandler}
            className="px-5 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors">
            {saving ? 'Adding…' : 'Add exercise'}
          </button>
        </div>
      </div>
    </div>
  );
}
