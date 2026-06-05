/**
 * _tanstack.tsx — TanStack Table v8 implementation.
 *
 * PRIVATE. Never import this file from outside src/components/table/.
 * The underscore prefix signals: internal implementation detail.
 * Import FitnessTable from FitnessTable.tsx instead.
 *
 * Design choice — edit state lives here, not in TanStack:
 *   TanStack Table v8 has no built-in cell editing. Edit state is managed
 *   with useState here and closed over in column definitions via useMemo.
 *   When the user clicks Edit, editingRowId is set and editingValues is
 *   populated with a copy of the row. Cells for that row render inputs
 *   instead of display values. Save/Cancel clear the edit state.
 *
 * Design choice — columns rebuilt with useMemo on edit state change:
 *   The column definitions close over editingRowId, editingValues, and
 *   the action handlers. useMemo re-runs when these change, which triggers
 *   TanStack to re-render the affected cells. This is the correct pattern
 *   for dynamic cell rendering in TanStack v8.
 *
 * Design choice — action column appended only when editable=true:
 *   No action column is rendered in read-only mode. This keeps the table
 *   clean for clients viewing their assigned plans.
 *
 * Design choice — group-hover on rows reveals action buttons:
 *   Edit/Delete buttons are opacity-0 by default and opacity-100 on row
 *   hover. This reduces visual noise in dense tables while keeping actions
 *   accessible. During edit mode, the active row's buttons are always
 *   visible (Save/Cancel).
 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
  type CellContext,
} from '@tanstack/react-table';
import type { FitnessColumnDef, FitnessTableProps } from './types';

// ── Internal helpers ──────────────────────────────────────────────────────────

function getRowIdFromData(row: Record<string, unknown>): string {
  return String(row['id'] ?? '');
}

function inputTypeFor(colType: FitnessColumnDef<Record<string, unknown>>['type']): string {
  return colType === 'number' || colType === 'decimal' ? 'number' : 'text';
}

function stepFor(colType: FitnessColumnDef<Record<string, unknown>>['type']): string | undefined {
  if (colType === 'decimal') return '0.1';
  if (colType === 'number') return '1';
  return undefined;
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function LoadingSkeleton({
  columnCount,
  rowCount = 3,
}: {
  columnCount: number;
  rowCount?: number;
}) {
  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-50 border-b border-gray-200 px-3 py-2.5 flex gap-4">
        {Array.from({ length: columnCount }).map((_, i) => (
          <div
            key={i}
            className="h-2.5 bg-gray-200 rounded animate-pulse"
            style={{ width: `${60 + (i % 3) * 30}px` }}
          />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rowCount }).map((_, rowIdx) => (
        <div
          key={rowIdx}
          className={`px-3 py-3 flex gap-4 border-b border-gray-100 last:border-0 ${
            rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'
          }`}
        >
          {Array.from({ length: columnCount }).map((_, colIdx) => (
            <div
              key={colIdx}
              className="h-4 bg-gray-100 rounded animate-pulse"
              style={{ width: `${50 + ((rowIdx + colIdx) % 4) * 20}px` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Cell input ────────────────────────────────────────────────────────────────

function CellInput({
  value,
  colType,
  onChange,
}: {
  value: string;
  colType: FitnessColumnDef<Record<string, unknown>>['type'];
  onChange: (val: string) => void;
}) {
  return (
    <input
      type={inputTypeFor(colType)}
      step={stepFor(colType)}
      min={colType === 'number' || colType === 'decimal' ? '0' : undefined}
      value={value}
      onChange={e => onChange(e.target.value)}
      className="
        w-full min-w-[56px]
        px-1.5 py-0.5
        text-sm text-gray-900
        bg-white
        border border-blue-400 rounded
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
        placeholder-gray-300
      "
    />
  );
}

// ── Action buttons ────────────────────────────────────────────────────────────

function EditActions({
  onSave,
  onCancel,
  saving,
}: {
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}) {
  return (
    <div className="flex items-center gap-1 whitespace-nowrap">
      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="
          px-2.5 py-1 text-xs font-medium rounded
          bg-green-600 text-white
          hover:bg-green-700 active:bg-green-800
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors
        "
      >
        {saving ? '…' : 'Save'}
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={saving}
        className="
          px-2.5 py-1 text-xs font-medium rounded
          bg-gray-100 text-gray-600
          hover:bg-gray-200 active:bg-gray-300
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors
        "
      >
        Cancel
      </button>
    </div>
  );
}

function RowActions({
  onEdit,
  onDelete,
  canInteract,
  hasDelete,
}: {
  onEdit: () => void;
  onDelete: (() => void) | undefined;
  canInteract: boolean;
  hasDelete: boolean;
}) {
  return (
    <div
      className={`
        flex items-center gap-1 whitespace-nowrap
        transition-opacity
        ${canInteract ? 'opacity-0 group-hover:opacity-100' : 'opacity-0 pointer-events-none'}
      `}
    >
      <button
        type="button"
        onClick={onEdit}
        disabled={!canInteract}
        className="
          px-2.5 py-1 text-xs font-medium rounded
          bg-blue-50 text-blue-700
          hover:bg-blue-100 active:bg-blue-200
          transition-colors
        "
      >
        Edit
      </button>
      {hasDelete && onDelete && (
        <button
          type="button"
          onClick={onDelete}
          disabled={!canInteract}
          className="
            px-2.5 py-1 text-xs font-medium rounded
            bg-red-50 text-red-600
            hover:bg-red-100 active:bg-red-200
            transition-colors
          "
        >
          Del
        </button>
      )}
    </div>
  );
}

// ── Main implementation ───────────────────────────────────────────────────────

export function FitnessTableImpl<T extends Record<string, unknown>>({
  columns: columnDefs,
  data,
  onRowEdit,
  onRowDelete,
  onAddRow,
  editable = false,
  loading = false,
  emptyMessage = 'No entries yet.',
}: FitnessTableProps<T>) {
  // ── Edit state ──────────────────────────────────────────────────────────────
  const [editingRowId, setEditingRowId] = useState<string | null>(null);
  const [editingValues, setEditingValues] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);

  const startEdit = useCallback((row: T) => {
    setEditingRowId(getRowIdFromData(row as Record<string, unknown>));
    setEditingValues({ ...(row as Record<string, unknown>) });
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingRowId(null);
    setEditingValues({});
  }, []);

  const saveEdit = useCallback(async () => {
    if (!onRowEdit) return;
    setSaving(true);
    try {
      await onRowEdit(editingValues as T);
      setEditingRowId(null);
      setEditingValues({});
    } finally {
      setSaving(false);
    }
  }, [onRowEdit, editingValues]);

  const updateField = useCallback((key: string, value: string) => {
    setEditingValues(prev => ({ ...prev, [key]: value }));
  }, []);

  const handleDelete = useCallback(async (id: string) => {
    if (!onRowDelete) return;
    await onRowDelete(id);
  }, [onRowDelete]);

  // ── Column definitions ──────────────────────────────────────────────────────
  // useMemo: rebuild column defs when edit state changes so cell renderers
  // close over fresh values. TanStack handles the diff internally.
  const columns = useMemo<ColumnDef<T, unknown>[]>(() => {
    // Data columns
    const dataCols: ColumnDef<T, unknown>[] = columnDefs.map(
      (col): ColumnDef<T, unknown> => ({
        id: String(col.key),
        accessorKey: col.key as string,
        header: col.header,
        ...(col.width != null ? { size: col.width } : {}),
        cell: (ctx: CellContext<T, unknown>): React.ReactNode => {
          const rawValue = ctx.getValue();
          const row = ctx.row.original;
          const rowId = getRowIdFromData(row as Record<string, unknown>);
          const isEditingThisRow = editingRowId === rowId;
          // col.editable defaults to true — only false opts out
          const colIsEditable = col.editable !== false;

          // ── Edit mode: show input ─────────────────────────────────────────
          if (isEditingThisRow && editable && colIsEditable) {
            const fieldKey = String(col.key);
            const currentVal = editingValues[fieldKey];
            return (
              <CellInput
                value={currentVal != null ? String(currentVal) : ''}
                colType={col.type}
                onChange={val => updateField(fieldKey, val)}
              />
            );
          }

          // ── Display mode: custom render ───────────────────────────────────
          if (col.render) {
            return col.render(rawValue as T[keyof T], row);
          }

          // ── Display mode: default ─────────────────────────────────────────
          if (rawValue == null || rawValue === '') {
            return <span className="text-gray-300 text-sm select-none">—</span>;
          }
          return <span className="text-sm text-gray-800">{String(rawValue)}</span>;
        },
      }),
    );

    // Action column — only in editable mode
    if (!editable) return dataCols;

    const actionCol: ColumnDef<T, unknown> = {
      id: '__actions__',
      // Empty header; the column has no label
      header: () => null,
      size: 120,
      cell: (ctx: CellContext<T, unknown>): React.ReactNode => {
        const row = ctx.row.original;
        const rowId = getRowIdFromData(row as Record<string, unknown>);
        const isEditingThis = editingRowId === rowId;
        const anotherRowIsEditing = editingRowId !== null && !isEditingThis;

        if (isEditingThis) {
          return (
            <EditActions
              onSave={saveEdit}
              onCancel={cancelEdit}
              saving={saving}
            />
          );
        }

        return (
          <RowActions
            onEdit={() => startEdit(row)}
            onDelete={onRowDelete ? () => handleDelete(rowId) : undefined}
            canInteract={!anotherRowIsEditing && !!onRowEdit}
            hasDelete={!!onRowDelete}
          />
        );
      },
    };

    return [...dataCols, actionCol];
  }, [
    columnDefs,
    editingRowId,
    editingValues,
    editable,
    saving,
    startEdit,
    cancelEdit,
    saveEdit,
    updateField,
    handleDelete,
    onRowEdit,
    onRowDelete,
  ]);

  // ── TanStack table instance ─────────────────────────────────────────────────
  const table = useReactTable<T>({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (originalRow) => getRowIdFromData(originalRow as Record<string, unknown>),
  });

  // ── Render: loading ─────────────────────────────────────────────────────────
  if (loading) {
    return <LoadingSkeleton columnCount={columnDefs.length + (editable ? 1 : 0)} />;
  }

  // ── Render: table ───────────────────────────────────────────────────────────
  const totalColumns = table.getAllColumns().length;

  return (
    <div className="w-full space-y-2">
      {/* Table wrapper */}
      <div className="rounded-lg border border-gray-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            {/* Header */}
            <thead>
              {table.getHeaderGroups().map(headerGroup => (
                <tr
                  key={headerGroup.id}
                  className="bg-gray-50 border-b border-gray-200"
                >
                  {headerGroup.headers.map(header => {
                    const hasWidth = header.column.columnDef.size != null;
                    return (
                      <th
                        key={header.id}
                        style={hasWidth ? { width: `${header.column.getSize()}px` } : undefined}
                        className="
                          px-3 py-2.5
                          text-left text-[11px] font-semibold
                          text-gray-500 uppercase tracking-wider
                          whitespace-nowrap
                        "
                      >
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>

            {/* Body */}
            <tbody>
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={totalColumns}
                    className="px-3 py-10 text-center text-sm text-gray-400 italic"
                  >
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row, idx) => {
                  const isEditingThis = editingRowId === row.id;
                  return (
                    <tr
                      key={row.id}
                      className={[
                        'group border-b border-gray-100 last:border-0 transition-colors duration-75',
                        isEditingThis
                          ? 'bg-blue-50/50 ring-1 ring-inset ring-blue-200'
                          : idx % 2 === 0
                          ? 'bg-white hover:bg-gray-50/70'
                          : 'bg-gray-50/40 hover:bg-gray-100/60',
                      ].join(' ')}
                    >
                      {row.getVisibleCells().map(cell => (
                        <td
                          key={cell.id}
                          className="px-3 py-2 align-middle"
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add entry button — only shown when editable and onAddRow provided */}
      {editable && onAddRow && (
        <button
          type="button"
          onClick={onAddRow}
          disabled={editingRowId !== null}
          className="
            flex items-center gap-1.5
            px-3 py-1.5
            text-sm font-medium
            text-blue-600
            hover:text-blue-700 hover:bg-blue-50
            rounded-md
            transition-colors
            disabled:opacity-40 disabled:cursor-not-allowed
          "
        >
          {/* Plus icon — inline SVG avoids any icon library dep */}
          <svg
            className="w-4 h-4 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          Add entry
        </button>
      )}
    </div>
  );
}
