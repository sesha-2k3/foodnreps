/**
 * useClientWorkout — fetches the client's assigned workout programme.
 *
 * Design choice — 404 treated as null, not as an error:
 *   When a client has no assigned programme, the backend returns HTTP 404.
 *   This is not an application error — it is a valid business state called
 *   "orphan mode" (a client with no coaching staff). Treating it as an error
 *   would force the WorkoutView to render an error state instead of the
 *   "no programme" empty state. The hook catches 404 and returns null data
 *   with isError=false so the view can branch correctly.
 *
 * Design choice — query key exported as a named constant:
 *   useLogWorkout's mutation imports CLIENT_WORKOUT_KEY to invalidate this
 *   query on success. Exporting the key from the hook that owns the query
 *   means there is one source of truth for the key string — no magic
 *   strings duplicated across files. When Sprint 8 adds prescription
 *   mutations, they import this same key.
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { api } from '../services/api';
import type { WorkoutProgramResponse } from '../types/api';

export const CLIENT_WORKOUT_KEY = ['client', 'workout'] as const;
export const PERSONAL_WORKOUT_KEY = ['personal', 'workout'] as const;

/** Fetch the client's assigned workout programme. Returns null when none assigned (orphan mode). */
export function useClientWorkout() {
  return useQuery<WorkoutProgramResponse | null>({
    queryKey: CLIENT_WORKOUT_KEY,
    queryFn: async () => {
      try {
        const res = await api.get<WorkoutProgramResponse>('/client/workout');
        return res.data;
      } catch (err) {
        // 404 = no assigned programme → orphan mode, not an error
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          return null;
        }
        throw err;
      }
    },
    // Do not retry 404s — they are deterministic, not transient
    retry: (failureCount, err) => {
      if (axios.isAxiosError(err) && err.response?.status === 404) return false;
      return failureCount < 3;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes — programme data changes infrequently
  });
}

/** Fetch the client's personal (self-managed) workout programme. */
export function usePersonalWorkout() {
  return useQuery<WorkoutProgramResponse | null>({
    queryKey: PERSONAL_WORKOUT_KEY,
    queryFn: async () => {
      try {
        const res = await api.get<WorkoutProgramResponse>('/personal/workout');
        return res.data;
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          return null;
        }
        throw err;
      }
    },
    retry: (failureCount, err) => {
      if (axios.isAxiosError(err) && err.response?.status === 404) return false;
      return failureCount < 3;
    },
    staleTime: 1000 * 60 * 5,
  });
}
