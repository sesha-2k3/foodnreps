/**
 * useDietMutations — write operations on diet plans for coaching staff
 * (nutritionist, coach) and personal self-management.
 *
 * Design choice — no optimistic updates for diet entries:
 *   Diet entries are simpler than prescriptions (flat list, 5 fields).
 *   Nutritionists typically add one entry at a time, review the macro
 *   totals, then add the next. The refetch after each save is fast and
 *   the updated totals (which require the server's Decimal precision)
 *   are more important than shaving 200ms off each entry add.
 *
 *   Contrast with prescription adds: a trainer building a full programme
 *   day adds 6–8 exercises in a row. The accumulation of round-trips
 *   justifies optimism there. A nutritionist adds 5–8 food items per
 *   meal plan, usually reviewing macros after each one.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { coachDietKey } from './useCoachProgramme';
import type { CoachingRole } from './useAssignedClients';
import type {
  DietPlanResponse,
  DietEntryResponse,
  CreateDietPlanRequest,
  AddDietEntryRequest,
  UpdateDietEntryRequest,
} from '../types/api';

export const PERSONAL_DIET_KEY = ['personal', 'diet'] as const;

export function useDietMutations(
  clientId: string,
  rolePrefix: CoachingRole | 'personal',
) {
  const queryClient = useQueryClient();

  const queryKey =
    rolePrefix === 'personal'
      ? PERSONAL_DIET_KEY
      : coachDietKey(rolePrefix as CoachingRole, clientId);

  const baseUrl =
    rolePrefix === 'personal'
      ? '/personal/diet'
      : `/${rolePrefix}/clients/${clientId}/diet`;

  const createPlan = useMutation<DietPlanResponse, Error, CreateDietPlanRequest>({
    mutationFn: (data) =>
      api.post<DietPlanResponse>(baseUrl, data).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  const addEntry = useMutation<DietEntryResponse, Error, AddDietEntryRequest>({
    mutationFn: (data) =>
      api.post<DietEntryResponse>(`${baseUrl}/entries`, data).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  const updateEntry = useMutation<
    DietEntryResponse,
    Error,
    { entryId: string; data: UpdateDietEntryRequest }
  >({
    mutationFn: ({ entryId, data }) =>
      api
        .patch<DietEntryResponse>(`${baseUrl}/entries/${entryId}`, data)
        .then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  const deleteEntry = useMutation<void, Error, string>({
    mutationFn: (entryId) =>
      api.delete(`${baseUrl}/entries/${entryId}`).then(() => undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  return { createPlan, addEntry, updateEntry, deleteEntry };
}
