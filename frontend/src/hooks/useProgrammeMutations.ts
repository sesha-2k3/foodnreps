/**
 * useProgrammeMutations — all workout hierarchy write operations for
 * coaching staff (trainer, coach) and personal plan self-management.
 *
 * Design choice — single hook returns all mutations:
 *   The programme builder component needs create/week/day/prescription
 *   operations available simultaneously. Returning them all from one hook
 *   call avoids threading six separate hooks through component props.
 *   Each mutation is still individually typed and independently usable.
 *
 * Design choice — optimistic update on addPrescription only:
 *   Structural mutations (create programme, add week, add day) are
 *   infrequent and low-latency in the context of building a programme.
 *   A coach adds a week once, names it, then moves on. The 200ms
 *   round-trip is imperceptible.
 *
 *   addPrescription is different: a coach filling in a programme may
 *   add 6–8 exercises to a single day in rapid succession. Each save
 *   should feel instant. The optimistic update adds the prescription
 *   to the cache immediately with a temporary ID and placeholder display
 *   values. onSettled always invalidates to replace placeholders with
 *   the real server-computed exercise_label, reps_display, load_display.
 *
 * Design choice — updatePrescription is not optimistic:
 *   Inline FitnessTable edits are deliberate, one-at-a-time actions.
 *   The coach clicks Save, sees the spinner, and the row updates. This
 *   is less frequent than addPrescription and the rollback complexity of
 *   optimistic updates on partial-field updates is not justified.
 *
 * Design choice — rolePrefix drives URL, not service:
 *   /trainer/clients/:id/workout/... and /coach/clients/:id/workout/...
 *   both hit the same backend service logic (WorkoutService). The URL
 *   prefix is the only difference. Parameterising by prefix rather than
 *   role enum keeps the hook decoupled from the role model.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { coachProgrammeKey } from './useCoachProgramme';
import type { CoachingRole } from './useAssignedClients';
import type {
  WorkoutProgramResponse,
  ProgramWeekResponse,
  ProgramDayResponse,
  WorkoutPrescriptionResponse,
  CreateProgrammeRequest,
  AddWeekRequest,
  AddDayRequest,
  AddPrescriptionRequest,
  UpdatePrescriptionRequest,
} from '../types/api';

// Re-export for personal plan wiring
export const PERSONAL_PROGRAMME_KEY = ['personal', 'workout'] as const;

export function useProgrammeMutations(
  clientId: string,
  rolePrefix: CoachingRole | 'personal',
) {
  const queryClient = useQueryClient();

  // Query key differs for personal vs coached plans
  const queryKey =
    rolePrefix === 'personal'
      ? PERSONAL_PROGRAMME_KEY
      : coachProgrammeKey(rolePrefix as CoachingRole, clientId);

  // Base URL differs between personal and coached plans
  const baseUrl =
    rolePrefix === 'personal'
      ? '/personal/workout'
      : `/${rolePrefix}/clients/${clientId}/workout`;

  // ── Create programme ────────────────────────────────────────────────────────
  const createProgramme = useMutation<
    WorkoutProgramResponse,
    Error,
    CreateProgrammeRequest
  >({
    mutationFn: (data) =>
      api.post<WorkoutProgramResponse>(baseUrl, data).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  // ── Add week ────────────────────────────────────────────────────────────────
  const addWeek = useMutation<ProgramWeekResponse, Error, AddWeekRequest>({
    mutationFn: (data) =>
      api.post<ProgramWeekResponse>(`${baseUrl}/weeks`, data).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  // ── Add day ─────────────────────────────────────────────────────────────────
  const addDay = useMutation<
    ProgramDayResponse,
    Error,
    { weekId: string; data: AddDayRequest }
  >({
    mutationFn: ({ weekId, data }) =>
      api
        .post<ProgramDayResponse>(`${baseUrl}/weeks/${weekId}/days`, data)
        .then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  // ── Add prescription (OPTIMISTIC) ───────────────────────────────────────────
  const addPrescription = useMutation<
    WorkoutPrescriptionResponse,
    Error,
    { dayId: string; data: AddPrescriptionRequest },
    { previous: WorkoutProgramResponse | null | undefined }
  >({
    mutationFn: ({ dayId, data }) =>
      api
        .post<WorkoutPrescriptionResponse>(
          `${baseUrl}/days/${dayId}/prescriptions`,
          data,
        )
        .then((r) => r.data),

    onMutate: async ({ dayId, data }) => {
      // Cancel any in-flight refetch to avoid overwriting the optimistic update
      await queryClient.cancelQueries({ queryKey });

      // Snapshot current cache for rollback
      const previous = queryClient.getQueryData<WorkoutProgramResponse | null>(
        queryKey as unknown as readonly unknown[],
      );

      // Optimistically insert a placeholder prescription
      queryClient.setQueryData(
        queryKey as unknown as readonly unknown[],
        (old: WorkoutProgramResponse | null | undefined) => {
          if (!old) return old;
          const tempPrescription: WorkoutPrescriptionResponse = {
            id: `temp-${Date.now()}`,
            order_index: data.order_index,
            exercise_label: String.fromCharCode(64 + data.order_index),
            exercise_name: data.exercise_name,
            warmup_sets: data.warmup_sets ?? null,
            working_sets: data.working_sets ?? null,
            reps_min: data.reps_min ?? null,
            reps_max: data.reps_max ?? null,
            reps_note: data.reps_note ?? null,
            reps_display: data.reps_min
              ? data.reps_max && data.reps_max !== data.reps_min
                ? `${data.reps_min}–${data.reps_max}`
                : String(data.reps_min)
              : (data.reps_note ?? ''),
            prescribed_load_kg: data.prescribed_load_kg
              ? String(data.prescribed_load_kg)
              : null,
            prescribed_load_text: data.prescribed_load_text ?? null,
            load_display: data.prescribed_load_kg
              ? `${data.prescribed_load_kg} kg`
              : (data.prescribed_load_text ?? 'BW'),
            prescribed_rpe: data.prescribed_rpe
              ? String(data.prescribed_rpe)
              : null,
            prescribed_rir: data.prescribed_rir ?? null,
            rest_seconds: data.rest_seconds ?? null,
            instructions: data.instructions ?? null,
            logs: [],
          };
          return {
            ...old,
            weeks: old.weeks.map((w) => ({
              ...w,
              days: w.days.map((d) =>
                d.id === dayId
                  ? { ...d, prescriptions: [...d.prescriptions, tempPrescription] }
                  : d,
              ),
            })),
          };
        },
      );

      return { previous };
    },

    onError: (_err, _vars, context) => {
      // Roll back to the snapshot
      if (context?.previous !== undefined) {
        queryClient.setQueryData(queryKey as unknown as readonly unknown[], context.previous);
      }
    },

    // Always sync with server to replace temp ID + placeholder display fields
    onSettled: () => queryClient.invalidateQueries({ queryKey }),
  });

  // ── Update prescription ──────────────────────────────────────────────────────
  const updatePrescription = useMutation<
    WorkoutPrescriptionResponse,
    Error,
    { prescriptionId: string; data: UpdatePrescriptionRequest }
  >({
    mutationFn: ({ prescriptionId, data }) =>
      api
        .patch<WorkoutPrescriptionResponse>(
          `${baseUrl}/prescriptions/${prescriptionId}`,
          data,
        )
        .then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  // ── Delete prescription ──────────────────────────────────────────────────────
  const deletePrescription = useMutation<void, Error, string>({
    mutationFn: (prescriptionId) =>
      api
        .delete(`${baseUrl}/prescriptions/${prescriptionId}`)
        .then(() => undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  return {
    createProgramme,
    addWeek,
    addDay,
    addPrescription,
    updatePrescription,
    deletePrescription,
  };
}
