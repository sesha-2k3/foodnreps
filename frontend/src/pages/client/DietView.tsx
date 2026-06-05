/**
 * DietView — renders the client's assigned diet plan.
 *
 * Design choice — totals computed client-side:
 *   The macro totals (total calories, protein, fat, carbs) are summed from
 *   the entry array on the frontend, not returned by the backend as a
 *   separate field. This is correct: the totals are a derived, display-only
 *   value. The backend stores each entry's macros; summing them for display
 *   is a presentation concern that belongs at this layer.
 *
 *   The sumMacros() utility uses parseFloat() on the Decimal-as-string values.
 *   The totals are rounded for display but the underlying per-entry values
 *   retain their full precision.
 *
 * Design choice — calories stored separately from macro-derived estimate:
 *   Each DietEntry has a calories field set explicitly by the nutritionist.
 *   The macro-derived estimate (protein×4 + fat×9 + carbs×4) may differ
 *   from the stored value due to fibre, alcohol, and label rounding.
 *   The DietView shows the stored calories — the nutritionist's explicit
 *   intent — not the algebraic estimate. This matches the schema's D3
 *   design decision for the diet_entries table.
 *
 * Design choice — read-only for clients:
 *   Clients can only read their assigned diet plan. The nutritionist writes
 *   it (Sprint 8). FitnessTable receives editable={false}; no action column.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { FitnessTable } from '../../components/table/FitnessTable';
import type { FitnessColumnDef } from '../../components/table/FitnessTable';
import { useClientDiet } from '../../hooks/useClientDiet';
import { sumMacros } from '../../utils/format';
import type { DietPlanResponse, DietEntryResponse } from '../../types/api';

// ── View-model row type ───────────────────────────────────────────────────────

interface DietEntryRow extends Record<string, unknown> {
  id: string;
  food_name: string;
  calories: string;     // Decimal string: "480.00"
  protein_g: string;    // "35.00"
  fat_g: string;        // "12.00"
  carbs_g: string;      // "55.00"
}

// ── Column definitions ────────────────────────────────────────────────────────

const DIET_COLUMNS: FitnessColumnDef<DietEntryRow>[] = [
  {
    key: 'food_name',
    header: 'Food',
    editable: false,
  },
  {
    key: 'calories',
    header: 'Calories',
    width: 100,
    editable: false,
    render: (val) => (
      <span className="text-sm tabular-nums">
        {val ? Math.round(parseFloat(val as string)).toLocaleString() : '—'}
      </span>
    ),
  },
  {
    key: 'protein_g',
    header: 'Protein',
    width: 88,
    editable: false,
    render: (val) => (
      <span className="text-sm tabular-nums text-blue-700">
        {val ? `${parseFloat(val as string).toFixed(1)}g` : '—'}
      </span>
    ),
  },
  {
    key: 'fat_g',
    header: 'Fat',
    width: 80,
    editable: false,
    render: (val) => (
      <span className="text-sm tabular-nums text-amber-700">
        {val ? `${parseFloat(val as string).toFixed(1)}g` : '—'}
      </span>
    ),
  },
  {
    key: 'carbs_g',
    header: 'Carbs',
    width: 88,
    editable: false,
    render: (val) => (
      <span className="text-sm tabular-nums text-green-700">
        {val ? `${parseFloat(val as string).toFixed(1)}g` : '—'}
      </span>
    ),
  },
];

function toDietEntryRow(entry: DietEntryResponse): DietEntryRow {
  return {
    id: entry.id,
    food_name: entry.food_name,
    calories: entry.calories,
    protein_g: entry.protein_g,
    fat_g: entry.fat_g,
    carbs_g: entry.carbs_g,
  };
}

// ── Macro totals strip ────────────────────────────────────────────────────────

function MacroTotals({ entries }: { entries: DietEntryResponse[] }) {
  if (entries.length === 0) return null;
  const totals = sumMacros(entries);

  return (
    <div className="mt-3 grid grid-cols-4 gap-3">
      <MacroCard label="Calories" value={Math.round(totals.calories).toLocaleString()} unit="" accent="text-gray-900" bg="bg-gray-50" />
      <MacroCard label="Protein"  value={totals.protein_g.toFixed(1)} unit="g" accent="text-blue-700"  bg="bg-blue-50"  />
      <MacroCard label="Fat"      value={totals.fat_g.toFixed(1)}     unit="g" accent="text-amber-700" bg="bg-amber-50" />
      <MacroCard label="Carbs"    value={totals.carbs_g.toFixed(1)}   unit="g" accent="text-green-700" bg="bg-green-50" />
    </div>
  );
}

function MacroCard({
  label, value, unit, accent, bg,
}: {
  label: string; value: string; unit: string; accent: string; bg: string;
}) {
  return (
    <div className={`${bg} rounded-xl px-4 py-3 text-center`}>
      <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-lg font-bold tabular-nums ${accent}`}>
        {value}<span className="text-xs font-medium ml-0.5">{unit}</span>
      </p>
    </div>
  );
}

function DietSkeleton() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-4">
      <div className="h-7 w-48 bg-gray-200 rounded animate-pulse" />
      <div className="h-48 bg-gray-100 rounded-lg animate-pulse" />
      <div className="grid grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    </div>
  );
}

function NoDietPlan() {
  return (
    <div className="max-w-lg mx-auto px-4 py-16 text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-900 mb-2">No diet plan assigned</h2>
      <p className="text-sm text-gray-500 mb-6">
        Your nutritionist hasn't set up a plan yet. You can manage your own nutrition in the meantime.
      </p>
      <Link
        to="/personal/diet"
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
      >
        Go to personal diet
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </Link>
    </div>
  );
}

// ── Main view ─────────────────────────────────────────────────────────────────

export function DietView() {
  const { data: plan, isLoading, isError } = useClientDiet();

  if (isLoading) return <DietSkeleton />;

  if (isError) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-sm text-red-600">Failed to load your diet plan. Please refresh.</p>
      </div>
    );
  }

  if (!plan) return <NoDietPlan />;

  const rows = plan.entries.map(toDietEntryRow);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Plan header */}
      <div className="mb-5">
        <h1 className="text-xl font-bold text-gray-900">{plan.name}</h1>
        {plan.coach_notes && (
          <p className="mt-1.5 text-sm text-gray-600 bg-gray-50 rounded-lg px-4 py-3 border-l-4 border-green-300">
            {plan.coach_notes}
          </p>
        )}
      </div>

      {/* Food entries table */}
      <FitnessTable<DietEntryRow>
        columns={DIET_COLUMNS}
        data={rows}
        editable={false}
        emptyMessage="No food entries in this plan yet."
      />

      {/* Macro totals */}
      <MacroTotals entries={plan.entries} />
    </div>
  );
}

export default DietView;
