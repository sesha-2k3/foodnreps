/**
 * FitnessTable — Facade component for the spreadsheet-style data table.
 *
 * PUBLIC API: This is the only file from src/components/table/ that the
 * rest of the application should import.
 *
 * Usage:
 *   import { FitnessTable } from '@/components/table/FitnessTable';
 *   import type { FitnessColumnDef } from '@/components/table/FitnessTable';
 *
 * Design choice — why this thin wrapper exists:
 *   The implementation lives in _tanstack.tsx. If TanStack Table is ever
 *   replaced (with AG Grid, a hand-rolled table, or anything else),
 *   _tanstack.tsx is rewritten. FitnessTable.tsx is unchanged. Every
 *   page that renders a table continues working with zero import changes.
 *
 *   If the Facade and implementation were the same file, every refactor
 *   to the TanStack internals would touch the component that the entire
 *   app imports from — a blast radius that grows with the codebase.
 *
 * Column definitions example (workout prescription — blue side):
 *
 *   type PrescriptionRow = {
 *     id: string;
 *     exercise_label: string;   // "A", "B", "C"
 *     exercise_name: string;
 *     working_sets: number | null;
 *     reps_display: string;     // "6–8", "5", "max reps"
 *     load_display: string;     // "70 kg", "BW"
 *     rest_seconds: number | null;
 *   };
 *
 *   const prescriptionColumns: FitnessColumnDef<PrescriptionRow>[] = [
 *     { key: 'exercise_label', header: '',       width: 36, editable: false },
 *     { key: 'exercise_name', header: 'Exercise', type: 'text' },
 *     { key: 'working_sets',  header: 'Sets',    type: 'number', width: 60 },
 *     { key: 'reps_display',  header: 'Reps',    width: 80, editable: false },
 *     { key: 'load_display',  header: 'Load',    width: 100, editable: false },
 *     { key: 'rest_seconds',  header: 'Rest (s)', type: 'number', width: 80 },
 *   ];
 *
 *   // Client view: read-only
 *   <FitnessTable columns={prescriptionColumns} data={entries} editable={false} />
 *
 *   // Trainer view: editable
 *   <FitnessTable
 *     columns={prescriptionColumns}
 *     data={entries}
 *     editable={isTrainer}
 *     onRowEdit={handlePrescriptionUpdate}
 *     onRowDelete={handlePrescriptionDelete}
 *     onAddRow={handleAddPrescription}
 *   />
 */

import React from 'react';
import { FitnessTableImpl } from './_tanstack';
import type { FitnessColumnDef, FitnessTableProps } from './types';

// Re-export types so callers only need one import
export type { FitnessColumnDef, FitnessTableProps };

/**
 * Spreadsheet-style data table for workout prescriptions, workout logs,
 * and diet entries.
 *
 * @param columns  Column definitions using FitnessColumnDef (not TanStack's ColumnDef).
 * @param data     Row data. Every row must carry an `id: string` field.
 * @param editable Master edit switch. Defaults to false (read-only).
 */
export function FitnessTable<T extends Record<string, unknown>>(
  props: FitnessTableProps<T>,
): React.ReactElement {
  return <FitnessTableImpl<T> {...props} />;
}
