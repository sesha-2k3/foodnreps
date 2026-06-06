import { useState } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../services/api";
import { useOverrideWorkout } from "../../hooks/useAdminAssignments";

type PlanMode = "workout" | "diet";

// ── Minimal plan display ──────────────────────────────────────────────────────
// Renders weeks→days→prescriptions in read-only mode using plain HTML table.
// FitnessTable is intentionally NOT used here — PlanOverride is an admin-only
// read+audit view, not a client-facing view, so the full FitnessTable facade
// is unnecessary overhead.

function WorkoutReadOnly({ data }: { data: Record<string, unknown> }) {
  const weeks = (data.weeks ?? []) as Record<string, unknown>[];
  if (weeks.length === 0) {
    return <p className="text-gray-400 italic text-sm">No weeks in this programme.</p>;
  }
  return (
    <div className="space-y-6">
      {weeks.map((week: Record<string, unknown>) => (
        <div key={week.id as string}>
          <h3 className="font-semibold text-gray-800 mb-2">
            Week {week.week_number as number}: {week.label as string}
          </h3>
          {((week.days ?? []) as Record<string, unknown>[]).map((day) => (
            <div key={day.id as string} className="ml-4 mb-4">
              <h4 className="text-sm font-medium text-gray-600 mb-1">
                Day {day.day_number as number}: {day.label as string}
              </h4>
              <table className="min-w-full text-xs border border-gray-200 rounded">
                <thead className="bg-gray-50">
                  <tr>
                    {["Exercise", "Sets", "Reps", "Load", "Rest"].map((h) => (
                      <th key={h} className="px-3 py-1.5 text-left text-gray-500 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {((day.prescriptions ?? []) as Record<string, unknown>[]).map((p) => (
                    <tr key={p.id as string} className="border-t border-gray-100">
                      <td className="px-3 py-1.5">{p.exercise_name as string}</td>
                      <td className="px-3 py-1.5">{p.working_sets as number}</td>
                      <td className="px-3 py-1.5">{p.reps_display as string ?? "—"}</td>
                      <td className="px-3 py-1.5">{p.load_display as string ?? "—"}</td>
                      <td className="px-3 py-1.5">{p.rest_seconds as number ? `${p.rest_seconds}s` : "—"}</td>
                    </tr>
                  ))}
                  {((day.prescriptions ?? []) as unknown[]).length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-3 py-2 text-gray-400 italic">No exercises.</td>
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

function DietReadOnly({ data }: { data: Record<string, unknown> }) {
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

  const [overrideMode, setOverrideMode] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const { data: planData, isLoading, error } = useQuery({
    queryKey: ["admin", "clients", clientId, mode],
    queryFn: async () => {
      const { data } = await api.get(`/admin/clients/${clientId}/${mode}`);
      return data as Record<string, unknown>;
    },
    enabled: !!clientId,
  });

  const overrideMutation = useOverrideWorkout(clientId!);

  async function handleOverrideSave() {
    if (!overrideReason.trim()) {
      setReasonError("A reason for the override is required.");
      return;
    }
    setReasonError(null);
    try {
      await overrideMutation.mutateAsync(overrideReason);
      setSuccessMsg("Override recorded successfully.");
      setOverrideMode(false);
      setOverrideReason("");
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Override failed.";
      setReasonError(msg);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <Link to={`/admin/users/${clientId}`} className="text-indigo-600 text-sm hover:underline">
            ← Back to user
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">
            {mode === "workout" ? "Workout Programme" : "Diet Plan"} — Admin View
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Read-only. Use Override to attach a mandatory audit reason.
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
          >
            Diet
          </Link>
        </div>
      </div>

      {successMsg && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-2 rounded mb-4 text-sm">
          {successMsg}
        </div>
      )}

      {isLoading && <div className="text-gray-500">Loading…</div>}

      {error && (
        <div className="text-red-500 text-sm">
          {mode === "workout" ? "No active workout programme." : "No active diet plan."}
        </div>
      )}

      {planData && (
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-800">{planData.name as string}</h2>
            {mode === "workout" && (
              <button
                onClick={() => setOverrideMode((v) => !v)}
                className="px-4 py-2 border border-amber-400 text-amber-700 rounded-md text-sm hover:bg-amber-50"
              >
                {overrideMode ? "Cancel" : "Override"}
              </button>
            )}
          </div>

          {mode === "workout"
            ? <WorkoutReadOnly data={planData} />
            : <DietReadOnly data={planData} />
          }
        </div>
      )}

      {/* Override reason panel */}
      {overrideMode && (
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-5">
          <h3 className="font-semibold text-amber-900 mb-1">Record override</h3>
          <p className="text-sm text-amber-700 mb-3">
            Providing a reason marks this programme as admin-overridden and writes an immutable
            audit record to version history.
          </p>
          <textarea
            rows={3}
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            placeholder="Reason for override (required)…"
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
              {overrideMutation.isPending ? "Saving…" : "Save override"}
            </button>
            <button
              onClick={() => { setOverrideMode(false); setOverrideReason(""); setReasonError(null); }}
              className="px-4 py-2 border rounded-md text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
