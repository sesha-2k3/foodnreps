/**
 * PersonalDiet — self-managed diet plan view.
 *
 * Clients managing their own nutrition can add, edit, and remove food
 * entries from their personal diet plan. Unlike the assigned DietView
 * (read-only), this view has editable=true and exposes the Add entry button.
 *
 * Design choice — full CRUD stubbed for Sprint 8:
 *   The FitnessTable receives editable=true and onRowEdit/onRowDelete props.
 *   The mutation hooks (useDietEntryUpdate, useDietEntryDelete, useDietEntryCreate)
 *   are wired in Sprint 8. For Sprint 7, they are console.warn stubs — the
 *   table renders correctly in editable mode but save/delete are no-ops.
 *   This approach lets us validate that the column definitions, row mapping,
 *   and table layout are correct before adding mutation complexity.
 *
 * Design choice — same macro totals as DietView:
 *   The MacroTotals component is duplicated here rather than extracted to a
 *   shared component. Two uses is not enough to justify premature extraction.
 *   Sprint 8, which builds the nutritionist's diet editor, will have three
 *   uses at that point — the correct time to extract.
 */

import React from 'react';
import { FitnessTable } from '../../components/table/FitnessTable';
import type { FitnessColumnDef } from '../../components/table/FitnessTable';
import { usePersonalDiet } from '../../hooks/useClientDiet';
import { sumMacros } from '../../utils/format';
import type { DietEntryResponse } from '../../types/api';

// ── View-model row type ───────────────────────────────────────────────────────

interface PersonalDietRow extends Record<string, unknown> {
  id: string;
  food_name: string;
  calories: string;
  protein_g: string;
  fat_g: string;
  carbs_g: string;
}

// ── Column definitions — editable ─────────────────────────────────────────────

const PERSONAL_DIET_COLUMNS: FitnessColumnDef<PersonalDietRow>[] = [
  { key: 'food_name',  header: 'Food',     type: 'text',    },
  { key: 'calories',   header: 'Calories', type: 'number', width: 100 },
  { key: 'protein_g',  header: 'Protein',  type: 'decimal', width: 88,
    render: (val) => <span className="text-sm tabular-nums text-blue-700">{val ? `${parseFloat(val as string).toFixed(1)}g` : '—'}</span>,
  },
  { key: 'fat_g',      header: 'Fat',      type: 'decimal', width: 80,
    render: (val) => <span className="text-sm tabular-nums text-amber-700">{val ? `${parseFloat(val as string).toFixed(1)}g` : '—'}</span>,
  },
  { key: 'carbs_g',    header: 'Carbs',    type: 'decimal', width: 88,
    render: (val) => <span className="text-sm tabular-nums text-green-700">{val ? `${parseFloat(val as string).toFixed(1)}g` : '—'}</span>,
  },
];

function toDietRow(entry: DietEntryResponse): PersonalDietRow {
  return {
    id: entry.id,
    food_name: entry.food_name,
    calories: entry.calories,
    protein_g: entry.protein_g,
    fat_g: entry.fat_g,
    carbs_g: entry.carbs_g,
  };
}

function MacroTotals({ entries }: { entries: DietEntryResponse[] }) {
  if (entries.length === 0) return null;
  const t = sumMacros(entries);
  return (
    <div className="mt-3 grid grid-cols-4 gap-3">
      {[
        { label: 'Calories', value: Math.round(t.calories).toLocaleString(), unit: '',  accent: 'text-gray-900', bg: 'bg-gray-50'   },
        { label: 'Protein',  value: t.protein_g.toFixed(1),                  unit: 'g', accent: 'text-blue-700',  bg: 'bg-blue-50'   },
        { label: 'Fat',      value: t.fat_g.toFixed(1),                      unit: 'g', accent: 'text-amber-700', bg: 'bg-amber-50'  },
        { label: 'Carbs',    value: t.carbs_g.toFixed(1),                    unit: 'g', accent: 'text-green-700', bg: 'bg-green-50'  },
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

function NoDietPlan() {
  return (
    <div className="max-w-lg mx-auto px-4 py-16 text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-900 mb-2">No personal diet plan yet</h2>
      <p className="text-sm text-gray-500 mb-6">
        Create a personal plan to start tracking your nutrition.
      </p>
      {/* TODO Sprint 8: wire to useCreatePersonalDiet mutation */}
      <button
        type="button"
        disabled
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-200 text-gray-400 text-sm font-medium rounded-lg cursor-not-allowed"
      >
        Create diet plan (coming soon)
      </button>
    </div>
  );
}

export function PersonalDiet() {
  const { data: plan, isLoading } = usePersonalDiet();

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-4">
        <div className="h-7 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="h-48 bg-gray-100 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!plan) return <NoDietPlan />;

  const rows = plan.entries.map(toDietRow);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-5">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            Personal
          </span>
        </div>
        <h1 className="text-xl font-bold text-gray-900">{plan.name}</h1>
      </div>

      <FitnessTable<PersonalDietRow>
        columns={PERSONAL_DIET_COLUMNS}
        data={rows}
        editable={true}
        onRowEdit={async (_row) => {
          // TODO Sprint 8: wire to useDietEntryUpdate mutation
          console.warn('Diet entry update not yet wired. Sprint 8 will implement this.');
        }}
        onRowDelete={async (_id) => {
          // TODO Sprint 8: wire to useDietEntryDelete mutation
          console.warn('Diet entry delete not yet wired. Sprint 8 will implement this.');
        }}
        onAddRow={() => {
          // TODO Sprint 8: wire to open add-entry form
          console.warn('Add diet entry not yet wired. Sprint 8 will implement this.');
        }}
        emptyMessage="No food entries yet — add your first item."
      />

      <MacroTotals entries={plan.entries} />
    </div>
  );
}

export default PersonalDiet;
