/**
 * useLogWorkout — mutation hook for POST /client/workout-logs.
 *
 * Design choice — invalidation not optimistic update:
 *   After a successful log submission, this mutation invalidates the
 *   CLIENT_WORKOUT_KEY and PERSONAL_WORKOUT_KEY queries. TanStack Query
 *   refetches the full workout response, which now includes the new log
 *   nested under its prescription. The user sees the updated log table
 *   after one network round-trip.
 *
 *   Optimistic updates (update the cache before the server confirms) are
 *   deferred to a future sprint. The reason: log submission is a low-frequency
 *   action (once per exercise per session) where a ~200ms round-trip is
 *   imperceptible. The complexity of optimistic rollback (what if the log
 *   validation fails?) is not justified for this use case.
 *
 *   Sprint 8's prescription mutations (high-frequency, inside a form) will
 *   warrant optimistic updates. The pattern will be established there.
 *
 * Design choice — single mutation for both assigned and personal logs:
 *   Both /client/workout-logs and /personal/workout-logs hit the same
 *   backend service (ClientService.log_workout). The mutation invalidates
 *   both the CLIENT_WORKOUT_KEY and PERSONAL_WORKOUT_KEY so whichever
 *   view is active gets its data refreshed.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { CLIENT_WORKOUT_KEY, PERSONAL_WORKOUT_KEY } from './useClientWorkout';
import type { WorkoutLogCreateRequest, WorkoutLogResponse } from '../types/api';

export function useLogWorkout() {
  const queryClient = useQueryClient();

  return useMutation<WorkoutLogResponse, Error, WorkoutLogCreateRequest>({
    mutationFn: (data) =>
      api.post<WorkoutLogResponse>('/client/workout-logs', data).then((r) => r.data),

    onSuccess: () => {
      // Invalidate both assigned and personal workout queries.
      // The refetch brings back the full hierarchy including the new log.
      void queryClient.invalidateQueries({ queryKey: CLIENT_WORKOUT_KEY });
      void queryClient.invalidateQueries({ queryKey: PERSONAL_WORKOUT_KEY });
    },
  });
}
