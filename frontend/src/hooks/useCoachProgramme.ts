/**
 * useCoachProgramme / useCoachDiet — fetch a specific client's workout
 * programme or diet plan through the coaching staff lens.
 *
 * Design choice — separate query keys from the client's own view:
 *   ['client', 'workout'] is the key for GET /client/workout (the client's
 *   own view). ['trainer', 'client', clientId, 'workout'] is the key for
 *   GET /trainer/clients/:id/workout (the trainer's view of the same data).
 *
 *   These use different endpoints with different permission checks. Sharing
 *   a query key would mean a trainer editing a prescription would invalidate
 *   every client's cached workout view simultaneously — incorrect behaviour.
 *   Separate keys give independent cache lifetimes and targeted invalidation.
 *
 * Design choice — 404 as null (same as Sprint 7 client hooks):
 *   A client with no assigned programme returns 404 from the backend, not
 *   an empty programme object. null signals "build a new programme" state.
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { api } from '../services/api';
import type { WorkoutProgramResponse, DietPlanResponse } from '../types/api';
import type { CoachingRole } from './useAssignedClients';

export function coachProgrammeKey(role: CoachingRole, clientId: string) {
  return [role, 'client', clientId, 'workout'] as const;
}

export function coachDietKey(role: CoachingRole, clientId: string) {
  return [role, 'client', clientId, 'diet'] as const;
}

export function useCoachProgramme(role: CoachingRole, clientId: string) {
  return useQuery<WorkoutProgramResponse | null>({
    queryKey: coachProgrammeKey(role, clientId),
    queryFn: async () => {
      try {
        const res = await api.get<WorkoutProgramResponse>(
          `/${role}/clients/${clientId}/workout`,
        );
        return res.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) return null;
        throw err;
      }
    },
    retry: (count, err) => {
      if (axios.isAxiosError(err) && err.response?.status === 404) return false;
      return count < 3;
    },
    enabled: !!clientId,
    staleTime: 1000 * 60 * 5,
  });
}

export function useCoachDiet(role: CoachingRole, clientId: string) {
  return useQuery<DietPlanResponse | null>({
    queryKey: coachDietKey(role, clientId),
    queryFn: async () => {
      try {
        const res = await api.get<DietPlanResponse>(
          `/${role}/clients/${clientId}/diet`,
        );
        return res.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) return null;
        throw err;
      }
    },
    retry: (count, err) => {
      if (axios.isAxiosError(err) && err.response?.status === 404) return false;
      return count < 3;
    },
    enabled: !!clientId,
    staleTime: 1000 * 60 * 5,
  });
}
