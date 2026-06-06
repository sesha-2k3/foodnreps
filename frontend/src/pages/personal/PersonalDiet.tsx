/**
 * PersonalDiet — self-managed diet plan view.
 *
 * Sprint 8 change from Sprint 7 stub:
 *   The three console.warn stubs (onRowEdit, onRowDelete, onAddRow) are
 *   replaced by delegating entirely to DietBuilder with rolePrefix="personal".
 *
 * Design choice — DietBuilder instead of manual mutation wiring:
 *   DietBuilder already encapsulates the full CRUD lifecycle for diet entries:
 *   create plan, add entry (modal), inline edit, inline delete, and macro
 *   totals. For personal diet, it is called with clientId="" and
 *   rolePrefix="personal", which routes all mutations to the /personal/diet/*
 *   endpoints via useDietMutations.
 *
 *   The alternative (wiring three mutations manually here) would duplicate
 *   logic already tested in the nutritionist and coach views. The DietBuilder
 *   component was designed to be role-agnostic from the start — this is
 *   the payoff.
 *
 *   The "Personal" badge that was on the Sprint 7 version is preserved here
 *   above the DietBuilder so the client always knows they are looking at
 *   their self-managed plan, not an assigned one.
 */

import React from 'react';
import { DietBuilder } from '../../components/diet/DietBuilder';
import { usePersonalDiet } from '../../hooks/useClientDiet';

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

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Personal badge — distinguishes self-managed from assigned plan */}
      <div className="flex items-center gap-2 mb-5">
        <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
          Personal
        </span>
      </div>

      {/*
        DietBuilder handles:
          - "No plan yet" → create plan form (POST /personal/diet)
          - Entry table with inline edit (PATCH /personal/diet/entries/:id)
          - Delete per row (DELETE /personal/diet/entries/:id)
          - Add entry modal (POST /personal/diet/entries)
          - Macro totals strip
      */}
      <DietBuilder
        clientId=""
        clientName="your personal"
        rolePrefix="personal"
        plan={plan ?? null}
      />
    </div>
  );
}

export default PersonalDiet;