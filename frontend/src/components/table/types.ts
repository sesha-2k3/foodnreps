/**
 * FitnessTable — Public API contract.
 *
 * This is the ONLY file from this directory that the rest of the app should
 * import. It contains zero TanStack references. The TanStack implementation
 * lives in _tanstack.tsx (private — never import directly).
 *
 * Design choice — FitnessColumnDef vs TanStack's ColumnDef:
 *   TanStack's ColumnDef exposes configuration the rest of the app should
 *   never need to know about. FitnessColumnDef is the application's own
 *   vocabulary: key, header, type, editable. It is simpler and stable —
 *   the TanStack-specific mapping happens inside _tanstack.tsx.
 *
 * Design choice — editable is a table-level boolean, not per-column:
 *   Role-based editability is decided at the route level, not inside column
 *   definitions. Passing editable={isTrainer} to the table means you cannot
 *   accidentally expose edit controls to a role that should not have them
 *   by misconfiguring a column. Individual columns can opt out of editing
 *   via col.editable = false (e.g. derived display-only fields like
 *   exercise_label), but the master switch is always at the table level.
 *
 * Design choice — id field convention:
 *   All domain entities sent to FitnessTable must carry an `id: string`
 *   field. The table uses this for edit-state tracking. This matches every
 *   entity in the backend schema (UUID primary keys serialised as strings).
 */

import type React from 'react';

export interface FitnessColumnDef<T> {
  /** Key of T to read from each row. Used as accessorKey in TanStack. */
  key: keyof T;

  /** Column header label. */
  header: string;

  /**
   * Input type used in edit mode.
   * - 'text'    → <input type="text">
   * - 'number'  → <input type="number" step="1">
   * - 'decimal' → <input type="number" step="0.1">
   * Defaults to 'text' when omitted.
   */
  type?: 'text' | 'number' | 'decimal';

  /**
   * Per-column edit opt-out. Defaults to true.
   * Set to false for derived or read-only fields (e.g. exercise_label,
   * tonnage_kg) that should never be editable even when the table is in
   * edit mode.
   */
  editable?: boolean;

  /** Fixed pixel width for the column. Passed to TanStack as size. */
  width?: number;

  /**
   * Custom display renderer for read-only mode.
   * Use this when the raw value needs formatting: reps_display,
   * load_display, exercise_label (A/B/C), etc.
   * Ignored in edit mode — the input always shows the raw value.
   */
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

export interface FitnessTableProps<T extends Record<string, unknown>> {
  /** Column definitions. Order determines display order. */
  columns: FitnessColumnDef<T>[];

  /** Row data. Every item must have an `id: string` field. */
  data: T[];

  /**
   * Called with the complete updated row when the user saves an inline edit.
   * The table stays in edit mode until this promise resolves.
   * If omitted, the Edit button is not shown even when editable=true.
   */
  onRowEdit?: (row: T) => Promise<void>;

  /**
   * Called with the row's id string when the user clicks Delete.
   * If omitted, the Delete button is not shown.
   */
  onRowDelete?: (id: string) => Promise<void>;

  /**
   * Called when the user clicks "Add entry".
   * The parent handles the actual creation (modal, inline blank row, etc.).
   * If omitted, the Add button is not shown.
   */
  onAddRow?: () => void;

  /**
   * Master edit switch. When false, all cells are read-only and no
   * action controls are rendered. Defaults to false.
   * Set at the route level based on the current user's role.
   */
  editable?: boolean;

  /** Show a loading skeleton instead of data. Defaults to false. */
  loading?: boolean;

  /** Empty state message. Defaults to "No entries yet." */
  emptyMessage?: string;
}
