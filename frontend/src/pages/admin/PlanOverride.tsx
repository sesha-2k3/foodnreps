import { useState } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../services/api";
import {
  useOverrideWorkout,
  PrescriptionPatch,
} from "../../hooks/useAdminAssignments";

type PlanMode = "workout" | "diet";

// ── Types mirroring the API response ────────────────────────────────────────

interface PrescriptionRow {
  id: string;
  exercise_label: string;
  exercise_name: string;
  working_sets: number | null;
  reps_min: number | null;
  reps_max: number | null;
  reps_note: string | null;
  reps_display: string;
  prescribed_load_kg: number | null;
  prescribed_load_text: string | null;
  load_display: string | null;
  rest_seconds: number | null;
}

interface DayRow {
  id: string;
  day_number: number;
  label: string;
  prescriptions: PrescriptionRow[];
}

interface WeekRow {
  id: string;
  week_number: number;
  label: string;
  days: DayRow[];
}

interface WorkoutPlan {
  id: string;
  name: string;
  override_reason: string | null;
  weeks: WeekRow[];
}

// ── Read-only workout display ────────────────────────────────────────────────

export function WorkoutReadOnly({ data }: { data: WorkoutPlan }) {
  if (data.weeks.length === 0) {
    return <p className="text-gray-400 italic text-sm">No weeks in this programme.</p>;
  }
  return (
    <div className="space-y-6">
      {data.weeks.map((week) => (
        <div key={week.id}>
          <h3 className="font-semibold text-gray-800 mb-2">
            Week {week.week_number}: {week.label}
          </h3>
          {week.days.map((day) => (
            <div key={day.id} className="ml-4 mb-4">
              <h4 className="text-sm font-medium text-gray-600 mb-1">
                Day {day.day_number}: {day.label}
              </h4>
              <table className="min-w-full text-xs border border-gray-200 rounded">
                <thead className="bg-gray-50">
                  <tr>
                    {["", "Exercise", "Sets", "Reps", "Load", "Rest"].map((h) => (
                      <th key={h} className="px-3 py-1.5 text-left text-gray-500 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {day.prescriptions.map((p) => (
                    <tr key={p.id} className="border-t border-gray-100">
                      <td className="px-3 py-1.5 text-gray-400 font-medium">{p.exercise_label}</td>
                      <td className="px-3 py-1.5">{p.exercise_name}</td>
                      <td className="px-3 py-1.5">{p.working_sets ?? "—"}</td>
                      <td className="px-3 py-1.5">{p.reps_display}</td>
                      <td className="px-3 py-1.5">{p.load_display ?? "—"}</td>
                      <td className="px-3 py-1.5">{p.rest_seconds ? `${p.rest_seconds}s` : "—"}</td>
                    </tr>
                  ))}
                  {day.prescriptions.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-3 py-2 text-gray-400 italic">No exercises.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Editable workout table (override mode) ────────────────────────────────────

interface EditableField {
  label: string;
  field: keyof PrescriptionPatch;
  type: "number" | "text";
  width: string;
}

const EDITABLE_FIELDS: EditableField[] = [
  { label: "Sets",     field: "working_sets",      type: "number", width: "w-16" },
  { label: "Reps min", field: "reps_min",           type: "number", width: "w-16" },
  { label: "Reps max", field: "reps_max",           type: "number", width: "w-16" },
  { label: "Load (kg)", field: "prescribed_load_kg", type: "number", width: "w-20" },
  { label: "Rest (s)", field: "rest_seconds",       type: "number", width: "w-16" },
];

function EditableWorkout({
  data,
  changes,
  onChange,
}: {
  data: WorkoutPlan;
  changes: Record<string, PrescriptionPatch>;
  onChange: (id: string, field: keyof PrescriptionPatch, value: number | null) => void;
}) {
  return (
    <div className="space-y-6">
      {data.weeks.map((week) => (
        <div key={week.id}>
          <h3 className="font-semibold text-gray-800 mb-2">
            Week {week.week_number}: {week.label}
          </h3>
          {week.days.map((day) => (
            <div key={day.id} className="ml-4 mb-4">
              <h4 className="text-sm font-medium text-gray-600 mb-1">
                Day {day.day_number}: {day.label}
              </h4>
              <table className="min-w-full text-xs border border-gray-200 rounded">
                <thead className="bg-amber-50">
                  <tr>
                    <th className="px-3 py-1.5 text-left text-gray-500 font-medium"></th>
                    <th className="px-3 py-1.5 text-left text-gray-500 font-medium">Exercise</th>
                    {EDITABLE_FIELDS.map((f) => (
                      <th key={f.field} className="px-3 py-1.5 text-left text-amber-700 font-medium">
                        {f.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {day.prescriptions.map((p) => {
                    const rowChanges = changes[p.id] ?? {};
                    const isChanged = !!changes[p.id];
                    return (
                      <tr
                        key={p.id}
                        className={`border-t border-gray-100 ${isChanged ? "bg-amber-50" : ""}`}
                      >
                        <td className="px-3 py-1.5 text-gray-400 font-medium">{p.exercise_label}</td>
                        <td className="px-3 py-1.5 font-medium">{p.exercise_name}</td>
                        {EDITABLE_FIELDS.map((f) => {
                          const currentVal =
                            f.field in rowChanges
                              ? (rowChanges[f.field] as number | null)
                              : (p[f.field as keyof PrescriptionRow] as number | null);
                          return (
                            <td key={f.field} className="px-2 py-1">
                              <input
                                type={f.type}
                                value={currentVal ?? ""}
                                onChange={(e) => {
                                  const raw = e.target.value;
                                  onChange(
                                    p.id,
                                    f.field,
                                    raw === "" ? null : Number(raw),
                                  );
                                }}
                                className={`${f.width} border rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-amber-400 ${
                                  f.field in rowChanges ? "border-amber-400 bg-amber-50" : "border-gray-300"
                                }`}
                              />
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Diet read-only ────────────────────────────────────────────────────────────

export function DietReadOnly({ data }: { data: Record<string, unknown> }) {
  const entries = (data.entries ?? []) as Record<string, unknown>[];
  if (entries.length === 0) {
    return <p className="text-gray-400 italic text-sm">No diet entries.</p>;
  }
  return (
    <table className="min-w-full text-sm border border-gray-200 rounded">
      <thead className="bg-gray-50">
        <tr>
          {["Food", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)"].map((h) => (
            <th key={h} className="px-4 py-2 text-left text-gray-500 font-medium text-xs">{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {entries.map((e) => (
          <tr key={e.id as string} className="border-t border-gray-100">
            <td className="px-4 py-2">{e.food_name as string}</td>
            <td className="px-4 py-2">{e.calories as number}</td>
            <td className="px-4 py-2">{e.protein_g as number}</td>
            <td className="px-4 py-2">{e.carbs_g as number}</td>
            <td className="px-4 py-2">{e.fat_g as number}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PlanOverride() {
  const { id: clientId } = useParams<{ id: string }>();
  const location = useLocation();
  const mode: PlanMode = location.pathname.endsWith("/diet") ? "diet" : "workout";

  // Override state
  const [overrideMode, setOverrideMode] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [changes, setChanges] = useState<Record<string, PrescriptionPatch>>({});
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const { data: planData, isLoading, error } = useQuery({
    queryKey: ["admin", "clients", clientId, mode],
    queryFn: async () => {
      const { data } = await api.get(`/admin/clients/${clientId}/${mode}`);
      return data;
    },
    enabled: !!clientId,
  });

  const overrideMutation = useOverrideWorkout(clientId!);

  function handleFieldChange(
    prescriptionId: string,
    field: keyof PrescriptionPatch,
    value: number | null,
  ) {
    setChanges((prev) => ({
      ...prev,
      [prescriptionId]: {
        ...prev[prescriptionId],
        prescription_id: prescriptionId,
        [field]: value,
      },
    }));
  }

  function handleCancelOverride() {
    setOverrideMode(false);
    setOverrideReason("");
    setChanges({});
    setReasonError(null);
  }

  async function handleOverrideSave() {
    if (!overrideReason.trim()) {
      setReasonError("A reason for the override is required.");
      return;
    }
    setReasonError(null);

    const changesPayload = Object.values(changes).filter((c) => {
      // Only send prescriptions that have at least one changed field beyond the id
      const { prescription_id: _id, ...rest } = c;
      return Object.values(rest).some((v) => v !== undefined);
    });

    try {
      const result = await overrideMutation.mutateAsync({
        override_reason: overrideReason,
        changes: changesPayload,
      });
      setSuccessMsg(
        `Override saved. ${result.changes_applied} prescription${result.changes_applied !== 1 ? "s" : ""} updated.`,
      );
      setOverrideMode(false);
      setOverrideReason("");
      setChanges({});
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Override failed.";
      setReasonError(msg);
    }
  }

  const changesCount = Object.keys(changes).length;

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <Link to={`/admin/users/${clientId}`} className="text-indigo-600 text-sm hover:underline">
            ← Back to user
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">
            {mode === "workout" ? "Workout Programme" : "Diet Plan"} — Admin View
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {overrideMode
              ? "Edit mode — changes are staged locally and submitted atomically with your reason."
              : "Read-only. Click Override to edit and attach a mandatory audit reason."}
          </p>
        </div>
        <div className="flex gap-2 mt-6">
          <Link
            to={`/admin/clients/${clientId}/workout`}
            className={`px-3 py-1.5 text-sm rounded ${mode === "workout" ? "bg-indigo-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}
          >
            Workout
          </Link>
          <Link
            to={`/admin/clients/${clientId}/diet`}
            className={`px-3 py-1.5 text-sm rounded ${mode === "diet" ? "bg-indigo-600 text-white" : "border text-gray-600 hover:bg-gray-50"}`}
          />
        </div>
      </div>

      {successMsg && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded mb-4 text-sm flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-green-600 hover:text-green-800 ml-4">✕</button>
        </div>
      )}

      {isLoading && <div className="text-gray-500 py-8">Loading…</div>}

      {error && (
        <div className="text-red-500 text-sm py-4">
          {mode === "workout" ? "No active workout programme for this client." : "No active diet plan for this client."}
        </div>
      )}

      {planData && (
        <>
          {/* Plan card */}
          <div className="bg-white shadow rounded-lg p-6 mb-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold text-gray-800 text-lg">{planData.name}</h2>
                {planData.override_reason && (
                  <p className="text-xs text-amber-700 mt-0.5">
                    Last override reason: {planData.override_reason}
                  </p>
                )}
              </div>
              {mode === "workout" && !overrideMode && (
                <button
                  onClick={() => setOverrideMode(true)}
                  className="px-4 py-2 border border-amber-400 text-amber-700 rounded-md text-sm font-medium hover:bg-amber-50"
                >
                  Override
                </button>
              )}
              {overrideMode && (
                <div className="flex items-center gap-3">
                  {changesCount > 0 && (
                    <span className="text-xs text-amber-700 font-medium bg-amber-100 px-2 py-0.5 rounded">
                      {changesCount} prescription{changesCount !== 1 ? "s" : ""} edited
                    </span>
                  )}
                  <button
                    onClick={handleCancelOverride}
                    className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>

            {mode === "workout" ? (
              overrideMode ? (
                <EditableWorkout
                  data={planData as WorkoutPlan}
                  changes={changes}
                  onChange={handleFieldChange}
                />
              ) : (
                <WorkoutReadOnly data={planData as WorkoutPlan} />
              )
            ) : (
              <DietReadOnly data={planData as Record<string, unknown>} />
            )}
          </div>

          {/* Override reason + submit — shown only in edit mode */}
          {overrideMode && (
            <div className="bg-amber-50 border border-amber-300 rounded-lg p-5">
              <h3 className="font-semibold text-amber-900 mb-1">Reason for override</h3>
              <p className="text-sm text-amber-700 mb-3">
                Required. Stored permanently in version history alongside all changes above.
              </p>
              <textarea
                rows={3}
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="E.g. Client recovering from knee injury — reduced load on squats."
                className="w-full border border-amber-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              />
              {reasonError && (
                <p className="text-red-600 text-xs mt-1">{reasonError}</p>
              )}
              <div className="flex gap-3 mt-3">
                <button
                  onClick={handleOverrideSave}
                  disabled={overrideMutation.isPending}
                  className="px-4 py-2 bg-amber-600 text-white rounded-md text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
                >
                  {overrideMutation.isPending
                    ? "Saving…"
                    : changesCount > 0
                      ? `Save override (${changesCount} change${changesCount !== 1 ? "s" : ""})`
                      : "Save override (reason only)"}
                </button>
                <button
                  onClick={handleCancelOverride}
                  className="px-4 py-2 border rounded-md text-sm text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}