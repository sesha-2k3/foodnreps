/**
 * Trainer client workout view.
 *
 * "Workout" tab: full ProgrammeBuilder (trainer owns this domain).
 * "Diet" tab: read-only diet view (trainer can see but not edit).
 *
 * Role-conditional rendering lives here in the page composition layer,
 * not inside ProgrammeBuilder. The builder is unaware of the tab structure
 * or that a read-only diet view exists alongside it.
 */

import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { ProgrammeBuilder } from '../../components/programme/ProgrammeBuilder';
import { FitnessTable } from '../../components/table/FitnessTable';
import type { FitnessColumnDef } from '../../components/table/FitnessTable';
import { useCoachProgramme, useCoachDiet } from '../../hooks/useCoachProgramme';

interface ReadDietRow extends Record<string, unknown> {
  id: string;
  food_name: string;
  calories: string;
  protein_g: string;
  fat_g: string;
  carbs_g: string;
}

const DIET_RO_COLS: FitnessColumnDef<ReadDietRow>[] = [
  { key: 'food_name', header: 'Food', editable: false },
  {
    key: 'calories', header: 'Calories', width: 100, editable: false,
    render: (v) => <span className="text-sm tabular-nums">{v ? Math.round(parseFloat(v as string)).toLocaleString() : '—'}</span>,
  },
  {
    key: 'protein_g', header: 'Protein', width: 88, editable: false,
    render: (v) => <span className="text-sm tabular-nums text-blue-700">{v ? `${parseFloat(v as string).toFixed(1)}g` : '—'}</span>,
  },
  {
    key: 'fat_g', header: 'Fat', width: 80, editable: false,
    render: (v) => <span className="text-sm tabular-nums text-amber-700">{v ? `${parseFloat(v as string).toFixed(1)}g` : '—'}</span>,
  },
  {
    key: 'carbs_g', header: 'Carbs', width: 88, editable: false,
    render: (v) => <span className="text-sm tabular-nums text-green-700">{v ? `${parseFloat(v as string).toFixed(1)}g` : '—'}</span>,
  },
];

type Tab = 'workout' | 'diet';

function TabBar({ active, onChange }: { active: Tab; onChange: (t: Tab) => void }) {
  return (
    <div className="flex gap-1 mb-6 p-1 bg-gray-100 rounded-xl w-fit">
      {(['workout', 'diet'] as Tab[]).map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => onChange(tab)}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors capitalize ${
            active === tab
              ? 'bg-white shadow-sm text-gray-900'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          {tab}
          {tab === 'diet' && (
            <span className="ml-1.5 text-[10px] font-normal text-gray-400">(read-only)</span>
          )}
        </button>
      ))}
    </div>
  );
}

export function TrainerClientWorkout() {
  const { id: clientId = '' } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('workout');
  const { data: programme, isLoading: wLoading } = useCoachProgramme('trainer', clientId);
  const { data: diet, isLoading: dLoading } = useCoachDiet('trainer', clientId);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <TabBar active={activeTab} onChange={setActiveTab} />

      {activeTab === 'workout' && (
        wLoading
          ? <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
          : <ProgrammeBuilder
              clientId={clientId}
              clientName="Client"
              rolePrefix="trainer"
              programme={programme ?? null}
            />
      )}

      {activeTab === 'diet' && (
        dLoading
          ? <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
          : !diet
          ? (
            <p className="text-sm text-gray-400 italic text-center py-12">
              No diet plan assigned — a nutritionist has not set one up yet.
            </p>
          )
          : (
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-4">{diet.name}</h2>
              {diet.coach_notes && (
                <p className="mb-4 text-sm text-gray-600 bg-green-50 rounded-lg px-4 py-3 border-l-4 border-green-300">
                  {diet.coach_notes}
                </p>
              )}
              <FitnessTable<ReadDietRow>
                columns={DIET_RO_COLS}
                data={diet.entries.map((e) => ({
                  id: e.id,
                  food_name: e.food_name,
                  calories: e.calories,
                  protein_g: e.protein_g,
                  fat_g: e.fat_g,
                  carbs_g: e.carbs_g,
                }))}
                editable={false}
                emptyMessage="No diet entries yet."
              />
            </div>
          )
      )}
    </div>
  );
}

export default TrainerClientWorkout;
