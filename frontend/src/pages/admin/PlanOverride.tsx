import { useState } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../services/api";
import { useAdminUser } from "../../hooks/useAdminUsers";
import { useOverrideWorkout } from "../../hooks/useAdminAssignments";
import { ProgrammeBuilder } from "../../components/programme/ProgrammeBuilder";
import { CommentThread } from "../../components/comments/CommentThread";
import type { WorkoutProgramResponse } from "../../types/api";

type PlanMode = "workout" | "diet";

// ── Diet read-only ────────────────────────────────────────────────────────────

export function DietReadOnly({ data }: { data: Record<string, unknown> }) {
  const entries = (data.entries ?? []) as Record<string, unknown>[];
  if (entries.length === 0)
    return <p className="text-gray-400 italic text-sm">No diet entries.</p>;
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

// ── Workout read-only (used when override mode is off) ────────────────────────

export function WorkoutReadOnly({ data }: { data: WorkoutProgramResponse }) {
  if (!data.weeks || data.weeks.length === 0)
    return <p className="text-gray-400 italic text-sm">No weeks in this programme.</p>;
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
      return data as WorkoutProgramResponse;
    },
    enabled: !!clientId,
  });

  const { data: clientUser } = useAdminUser(clientId);
  const overrideMutation = useOverrideWorkout(clientId!);

  async function handleRecordReason() {
    if (!overrideReason.trim()) {
      setReasonError("A reason is required before recording the override.");
      return;
    }
    setReasonError(null);
    try {
      await overrideMutation.mutateAsync({ override_reason: overrideReason, changes: [] });
      setSuccessMsg("Override reason recorded in version history.");
      setOverrideReason("");
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to record override reason.";
      setReasonError(msg);
    }
  }

  function handleExitOverride() {
    setOverrideMode(false);
    setOverrideReason("");
    setReasonError(null);
  }

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
              ? "Override mode — changes take effect immediately. Record your reason when done."
              : "Read-only. Click Override to add/remove weeks, days, and exercises."}
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
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded mb-4 text-sm flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="ml-4 text-green-600 hover:text-green-800">✕</button>
        </div>
      )}

      {/* Override reason banner */}
      {overrideMode && mode === "workout" && (
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 mb-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <p className="text-sm font-semibold text-amber-900 mb-1">Override mode active</p>
              <p className="text-xs text-amber-700 mb-2">
                Changes are saved immediately to the database. When finished, enter a reason and
                click "Record reason" — this writes an immutable audit entry to version history.
              </p>
              <div className="flex gap-2 items-start">
                <textarea
                  rows={2}
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Reason for override, e.g. Client has knee injury — reduced squat volume."
                  className="flex-1 border border-amber-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
                />
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    onClick={handleRecordReason}
                    disabled={overrideMutation.isPending}
                    className="px-3 py-2 bg-amber-600 text-white rounded-md text-sm font-medium hover:bg-amber-700 disabled:opacity-50 whitespace-nowrap"
                  >
                    {overrideMutation.isPending ? "Saving…" : "Record reason"}
                  </button>
                  <button
                    onClick={handleExitOverride}
                    className="px-3 py-2 border rounded-md text-sm text-gray-600 hover:bg-gray-50 whitespace-nowrap"
                  >
                    Exit override
                  </button>
                </div>
              </div>
              {reasonError && <p className="text-red-600 text-xs mt-1">{reasonError}</p>}
            </div>
          </div>
        </div>
      )}

      {isLoading && <div className="text-gray-500 py-8">Loading…</div>}

      {error && !overrideMode && (
        <div className="text-red-500 text-sm py-4">
          {mode === "workout"
            ? "No active workout programme for this client."
            : "No active diet plan for this client."}
        </div>
      )}

      {/* Workout — switches between read-only and ProgrammeBuilder */}
      {mode === "workout" && (
        <div className="bg-white shadow rounded-lg p-6">
          {overrideMode ? (
            <ProgrammeBuilder
              clientId={clientId!}
              clientName={clientUser?.full_name ?? "Client"}
              rolePrefix="admin"
              programme={planData ?? null}
            />
          ) : (
            planData && (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="font-semibold text-gray-800 text-lg">{planData.name}</h2>
                    {planData.override_reason && (
                      <p className="text-xs text-amber-700 mt-0.5">
                        Last override: {planData.override_reason}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => setOverrideMode(true)}
                    className="px-4 py-2 border border-amber-400 text-amber-700 rounded-md text-sm font-medium hover:bg-amber-50"
                  >
                    Override
                  </button>
                </div>
                <WorkoutReadOnly data={planData} />
              </>
            )
          )}
          {planData && (
            <CommentThread planType="workout" planId={planData.id} />
          )}
        </div>
      )}

      {/* Diet — read-only */}
      {mode === "diet" && planData && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="font-semibold text-gray-800 text-lg mb-4">{planData.name}</h2>
          <DietReadOnly data={planData as unknown as Record<string, unknown>} />
          <CommentThread planType="diet" planId={planData.id} />
        </div>
      )}
    </div>
  );
}