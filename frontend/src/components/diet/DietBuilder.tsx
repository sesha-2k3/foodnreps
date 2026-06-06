/**
 * DietBuilder — diet plan entry editor for nutritionist and coach.
 *
 * Simpler than ProgrammeBuilder: a flat list of food entries, no hierarchy.
 * The FitnessTable with editable=true handles inline editing of existing
 * entries. Adding new entries uses a compact modal form.
 *
 * Design choice — macro totals update on every cache invalidation:
 *   The sumMacros utility is called on the current entries array and
 *   the totals re-render whenever TanStack Query's cache updates. This
 *   means the nutritionist sees updated totals immediately after adding,
 *   editing, or deleting an entry — no separate totals fetch needed.
 *
 * Design choice — calories stored separate from macro-derived estimate:
 *   The AddDietEntryModal has a "Calories" field and separate macro fields.
 *   The macro-derived estimate (protein×4 + fat×9 + carbs×4) is shown as a
 *   hint below the calories input. The nutritionist can override it with
 *   the label value. This directly maps to schema Design Decision D3.
 */

import React, { useState } from 'react';
import { FitnessTable } from '../../components/table/FitnessTable';
import type { FitnessColumnDef } from '../../components/table/FitnessTable';
import { useDietMutations } from '../../hooks/useDietMutations';
import { sumMacros } from '../../utils/format';
import type {
  DietPlanResponse,
  DietEntryResponse,
  AddDietEntryRequest,
} from '../../types/api';
import type { CoachingRole } from '../../hooks/useAssignedClients';

// ── Row type ──────────────────────────────────────────────────────────────────

interface DietEntryRow extends Record<string, unknown> {
  id: string;
  food_name: string;
  calories: string;
  protein_g: string;
  fat_g: string;
  carbs_g: string;
}

const EDITABLE_DIET_COLUMNS: FitnessColumnDef<DietEntryRow>[] = [
  { key: 'food_name',  header: 'Food',     type: 'text'    },
  { key: 'calories',   header: 'Calories', type: 'number', width: 100 },
  { key: 'protein_g',  header: 'Protein',  type: 'decimal', width: 88,
    render: (v) => <span className="text-sm tabular-nums text-blue-700">{v ? `${parseFloat(v as string).toFixed(1)}g` : '—'}</span>,
  },
  { key: 'fat_g',      header: 'Fat',      type: 'decimal', width: 80,
    render: (v) => <span className="text-sm tabular-nums text-amber-700">{v ? `${parseFloat(v as string).toFixed(1)}g` : '—'}</span>,
  },
  { key: 'carbs_g',    header: 'Carbs',    type: 'decimal', width: 88,
    render: (v) => <span className="text-sm tabular-nums text-green-700">{v ? `${parseFloat(v as string).toFixed(1)}g` : '—'}</span>,
  },
];

function toDietRow(e: DietEntryResponse): DietEntryRow {
  return { id: e.id, food_name: e.food_name, calories: e.calories, protein_g: e.protein_g, fat_g: e.fat_g, carbs_g: e.carbs_g };
}

// ── Macro totals strip ────────────────────────────────────────────────────────

function MacroTotals({ entries }: { entries: DietEntryResponse[] }) {
  if (entries.length === 0) return null;
  const t = sumMacros(entries);
  return (
    <div className="mt-3 grid grid-cols-4 gap-3">
      {[
        { label: 'Calories', value: Math.round(t.calories).toLocaleString(), unit: '',  accent: 'text-gray-900', bg: 'bg-gray-50'   },
        { label: 'Protein',  value: t.protein_g.toFixed(1), unit: 'g', accent: 'text-blue-700',  bg: 'bg-blue-50'   },
        { label: 'Fat',      value: t.fat_g.toFixed(1),     unit: 'g', accent: 'text-amber-700', bg: 'bg-amber-50'  },
        { label: 'Carbs',    value: t.carbs_g.toFixed(1),   unit: 'g', accent: 'text-green-700', bg: 'bg-green-50'  },
      ].map(({ label, value, unit, accent, bg }) => (
        <div key={label} className={`${bg} rounded-xl px-4 py-3 text-center`}>
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">{label}</p>
          <p className={`text-lg font-bold tabular-nums ${accent}`}>
            {value}<span className="text-xs font-medium ml-0.5">{unit}</span>
          </p>
        </div>
      ))}
    </div>
  );
}

// ── Add entry modal ───────────────────────────────────────────────────────────

function AddDietEntryModal({
  existingCount,
  onAdd,
  onClose,
}: {
  existingCount: number;
  onAdd: (data: AddDietEntryRequest) => Promise<void>;
  onClose: () => void;
}) {
  const [form, setForm] = useState({ foodName: '', calories: '', protein: '', fat: '', carbs: '' });
  const [saving, setSaving] = useState(false);

  // Macro-derived calorie estimate (hint only — not what gets saved)
  const derivedCalories =
    form.protein && form.fat && form.carbs
      ? Math.round(
          parseFloat(form.protein || '0') * 4 +
          parseFloat(form.fat || '0') * 9 +
          parseFloat(form.carbs || '0') * 4,
        )
      : null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.foodName.trim() || !form.calories) return;
    setSaving(true);
    try {
      await onAdd({
        food_name: form.foodName.trim(),
        calories: parseFloat(form.calories),
        protein_g: parseFloat(form.protein || '0'),
        fat_g: parseFloat(form.fat || '0'),
        carbs_g: parseFloat(form.carbs || '0'),
        order_index: existingCount + 1,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />
      <div className="relative z-10 w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Add food entry</h2>
          <button type="button" onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="px-5 py-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Food name</label>
            <input type="text" placeholder="e.g. Chicken breast (100g)" value={form.foodName}
              onChange={(e) => setForm(p => ({ ...p, foodName: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus required />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Calories
              {derivedCalories != null && (
                <span className="ml-2 font-normal text-gray-400 normal-case">
                  (macro-derived: {derivedCalories} kcal)
                </span>
              )}
            </label>
            <input type="number" min="0" step="1" placeholder="480" value={form.calories}
              onChange={(e) => setForm(p => ({ ...p, calories: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required />
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { field: 'protein', label: 'Protein (g)', color: 'text-blue-600' },
              { field: 'fat',     label: 'Fat (g)',     color: 'text-amber-600' },
              { field: 'carbs',   label: 'Carbs (g)',   color: 'text-green-600' },
            ].map(({ field, label, color }) => (
              <div key={field}>
                <label className={`block text-xs font-semibold uppercase tracking-wider mb-1.5 ${color}`}>{label}</label>
                <input type="number" min="0" step="0.1" placeholder="0"
                  value={(form as Record<string, string>)[field]}
                  onChange={(e) => setForm(p => ({ ...p, [field]: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-center" />
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
            <button type="submit" disabled={saving || !form.foodName.trim() || !form.calories}
              className="px-5 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-40">
              {saving ? 'Adding…' : 'Add entry'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Create plan form ──────────────────────────────────────────────────────────

function CreatePlanForm({ clientName, onCreate, isPending }: { clientName: string; onCreate: (name: string) => Promise<void>; isPending: boolean }) {
  const [name, setName] = useState('');
  return (
    <div className="max-w-md mx-auto text-center py-16">
      <h3 className="text-base font-semibold text-gray-900 mb-1">No diet plan for {clientName}</h3>
      <p className="text-sm text-gray-500 mb-6">Create one to start adding entries.</p>
      <div className="flex gap-2 max-w-sm mx-auto">
        <input type="text" placeholder="Plan name, e.g. Cutting Phase" value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && name.trim()) void onCreate(name.trim()); }}
          className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        <button type="button" disabled={!name.trim() || isPending} onClick={() => void onCreate(name.trim())}
          className="px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg disabled:opacity-40">
          {isPending ? '…' : 'Create'}
        </button>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface DietBuilderProps {
  clientId: string;
  clientName: string;
  rolePrefix: CoachingRole | 'personal';
  plan: DietPlanResponse | null;
}

export function DietBuilder({ clientId, clientName, rolePrefix, plan }: DietBuilderProps) {
  const mutations = useDietMutations(clientId, rolePrefix);
  const [addingEntry, setAddingEntry] = useState(false);

  if (!plan) {
    return (
      <CreatePlanForm
        clientName={clientName}
        onCreate={async (name) => { await mutations.createPlan.mutateAsync({ name }); }}
        isPending={mutations.createPlan.isPending}
      />
    );
  }

  const rows = plan.entries.map(toDietRow);

  return (
    <div>
      <div className="mb-5 pb-4 border-b border-gray-100">
        <h2 className="text-lg font-bold text-gray-900">{plan.name}</h2>
        {plan.coach_notes && (
          <p className="mt-1 text-sm text-gray-600">{plan.coach_notes}</p>
        )}
      </div>

      <FitnessTable<DietEntryRow>
        columns={EDITABLE_DIET_COLUMNS}
        data={rows}
        editable={true}
        onRowEdit={async (row) => {
          await mutations.updateEntry.mutateAsync({
            entryId: row.id as string,
            data: {
              food_name: row.food_name as string,
              calories: parseFloat(row.calories as string),
              protein_g: parseFloat(row.protein_g as string),
              fat_g: parseFloat(row.fat_g as string),
              carbs_g: parseFloat(row.carbs_g as string),
            },
          });
        }}
        onRowDelete={async (id) => { await mutations.deleteEntry.mutateAsync(id); }}
        onAddRow={() => setAddingEntry(true)}
        emptyMessage="No food entries yet — click 'Add entry' to start."
      />

      <MacroTotals entries={plan.entries} />

      {addingEntry && (
        <AddDietEntryModal
          existingCount={plan.entries.length}
          onAdd={async (data) => { await mutations.addEntry.mutateAsync(data); }}
          onClose={() => setAddingEntry(false)}
        />
      )}
    </div>
  );
}
