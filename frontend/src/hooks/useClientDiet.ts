/**
 * useClientDiet / usePersonalDiet — fetches diet plans.
 * Mirrors useClientWorkout exactly — same 404-as-null pattern,
 * same exported key constants for mutation invalidation.
 */

import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { api } from '../services/api';
import type { DietPlanResponse } from '../types/api';

export const CLIENT_DIET_KEY = ['client', 'diet'] as const;
export const PERSONAL_DIET_KEY = ['personal', 'diet'] as const;

/** Fetch the client's assigned diet plan. Returns null when none assigned. */
export function useClientDiet() {
  return useQuery<DietPlanResponse | null>({
    queryKey: CLIENT_DIET_KEY,
    queryFn: async () => {
      try {
        const res = await api.get<DietPlanResponse>('/client/diet');
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

/** Fetch the client's personal (self-managed) diet plan. */
export function usePersonalDiet() {
  return useQuery<DietPlanResponse | null>({
    queryKey: PERSONAL_DIET_KEY,
    queryFn: async () => {
      try {
        const res = await api.get<DietPlanResponse>('/personal/diet');
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
