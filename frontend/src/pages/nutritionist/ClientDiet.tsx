/**
 * Nutritionist client diet view.
 *
 * "Diet" tab: full DietBuilder (nutritionist owns this domain).
 * "Workout" tab: read-only workout view (nutritionist sees but cannot edit).
 *
 * Cross-domain visibility: the nutritionist sees the trainer's prescribed
 * exercises to calibrate calorie and macro targets appropriately. A client
 * doing 5×5 heavy strength work needs different macros than one doing
 * light circuit training.
 */

import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { DietBuilder } from '../../components/diet/DietBuilder';
import { FitnessTable } from '../../components/table/FitnessTable';
import type { FitnessColumnDef } from '../../components/table/FitnessTable';
import { useCoachProgramme, useCoachDiet } from '../../hooks/useCoachProgramme';

interface ReadPrescRow extends Record<string, unknown> {
  id: string;
  exercise_label: string;
  exercise_name: string;
  working_sets: string;
  reps_display: string;
  load_display: string;
}

const PRESC_RO_COLS: FitnessColumnDef<ReadPrescRow>[] = [
  { key: 'exercise_label', header: '', width: 36, editable: false },
  { key: 'exercise_name', header: 'Exercise', editable: false },
  { key: 'working_sets', header: 'Sets', width: 60, editable: false },
  { key: 'reps_display', header: 'Reps', width: 90, editable: false },
  { key: 'load_display', header: 'Load', width: 100, editable: false },
];

type Tab = 'diet' | 'workout';

export function NutritionistClientDiet() {
  const { id: clientId = '' } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('diet');
  const { data: diet, isLoading: dLoading } = useCoachDiet('nutritionist', clientId);
  const { data: programme, isLoading: wLoading } = useCoachProgramme('nutritionist', clientId);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 p-1 bg-gray-100 rounded-xl w-fit">
        {(['diet', 'workout'] as Tab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors capitalize ${
              activeTab === tab
                ? 'bg-white shadow-sm text-gray-900'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
            {tab === 'workout' && (
              <span className="ml-1.5 text-[10px] font-normal text-gray-400">(read-only)</span>
            )}
          </button>
        ))}
      </div>

      {/* Diet tab — full editor */}
      {activeTab === 'diet' && (
        dLoading
          ? <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
          : <DietBuilder
              clientId={clientId}
              clientName="Client"
              rolePrefix="nutritionist"
              plan={diet ?? null}
            />
      )}

      {/* Workout tab — read-only cross-domain view */}
      {activeTab === 'workout' && (
        wLoading
          ? <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
          : !programme
          ? (
            <p className="text-sm text-gray-400 italic text-center py-12">
              No workout programme assigned — a trainer has not set one up yet.
            </p>
          )
          : (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-gray-900">{programme.name}</h2>
              {programme.weeks.map((week) =>
                week.days.map((day) => (
                  <div key={day.id}>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      {week.label} — {day.label}
                    </p>
                    <div className="ring-1 ring-blue-100 rounded-lg overflow-hidden">
                      <FitnessTable<ReadPrescRow>
                        columns={PRESC_RO_COLS}
                        data={day.prescriptions.map((p) => ({
                          id: p.id,
                          exercise_label: p.exercise_label,
                          exercise_name: p.exercise_name,
                          working_sets: p.working_sets != null ? String(p.working_sets) : '—',
                          reps_display: p.reps_display,
                          load_display: p.load_display,
                        }))}
                        editable={false}
                        emptyMessage="No exercises in this day."
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          )
      )}
    </div>
  );
}

export default NutritionistClientDiet;
