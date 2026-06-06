/**
 * useUpdateWorkoutLog — mutation hook for PATCH /client/workout-logs/:id
 *
 * Used by LogEntryModal when the client already has a log for today's
 * prescription and is correcting/updating it instead of creating a new one.
 *
 * Add this to src/hooks/useLogWorkout.ts alongside useLogWorkout,
 * OR create as a separate file at src/hooks/useUpdateWorkoutLog.ts
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { CLIENT_WORKOUT_KEY, PERSONAL_WORKOUT_KEY } from './useClientWorkout';

export interface UpdateWorkoutLogRequest {
  actual_sets?:        number;
  actual_reps?:        number;
  actual_load_kg?:     number | null;
  actual_rpe?:         number | null;
  readiness?:          number | null;
  time_taken_seconds?: number | null;
  client_notes?:       string | null;
  logged_at?:          string;
}

export function useUpdateWorkoutLog() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { logId: string; data: UpdateWorkoutLogRequest }>({
    mutationFn: ({ logId, data }) =>
      api.patch(`/client/workout-logs/${logId}`, data).then(() => undefined),

    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: CLIENT_WORKOUT_KEY });
      void queryClient.invalidateQueries({ queryKey: PERSONAL_WORKOUT_KEY });
    },
  });
}
