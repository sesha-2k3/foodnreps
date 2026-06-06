/**
 * useAssignedClients — fetches the list of clients assigned to the current
 * coaching staff member.
 *
 * Design choice — single hook parameterised by role prefix:
 *   The three coaching roles (trainer, nutritionist, coach) all have a
 *   GET /:role/clients endpoint that returns the same response shape.
 *   One parameterised hook avoids three nearly-identical hook files.
 *   The rolePrefix drives both the URL and the query key, so each role's
 *   client list is independently cached and independently invalidated.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import type { ClientSummaryResponse } from '../types/api';

export type CoachingRole = 'trainer' | 'nutritionist' | 'coach';

export function clientListKey(role: CoachingRole) {
  return [role, 'clients'] as const;
}

export function useAssignedClients(role: CoachingRole) {
  return useQuery<ClientSummaryResponse[]>({
    queryKey: clientListKey(role),
    queryFn: () =>
      api.get<ClientSummaryResponse[]>(`/${role}/clients`).then((r) => r.data),
    staleTime: 1000 * 60 * 2, // 2 minutes — client lists change less often than plans
  });
}
