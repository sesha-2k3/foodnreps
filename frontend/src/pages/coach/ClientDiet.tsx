import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { DietBuilder } from '../../components/diet/DietBuilder';
import { useCoachDiet } from '../../hooks/useCoachProgramme';

export function CoachClientDiet() {
  const { id: clientId = '' } = useParams<{ id: string }>();
  const { data: diet, isLoading } = useCoachDiet('coach', clientId);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <Link
          to="/coach/clients"
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Clients
        </Link>
        <Link
          to={`/coach/clients/${clientId}/workout`}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors"
        >
          Switch to Workout
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>

      {isLoading
        ? <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
        : <DietBuilder
            clientId={clientId}
            clientName="Client"
            rolePrefix="coach"
            plan={diet ?? null}
          />
      }
    </div>
  );
}

export default CoachClientDiet;
