/**
 * useInvites — invite code hooks for coaching staff (generate/list/revoke)
 * and clients (connect, get current coaches).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { CoachingRole } from './useAssignedClients';

// ── Response types ────────────────────────────────────────────────────────────

export interface InviteResponse {
  id: string;
  code: string;
  expires_at: string;
  used_at: string | null;
  created_at: string;
}

export interface CoachInfo {
  id: string;
  full_name: string;
  email: string;
  role: string;
  assigned_at: string;
}

export interface ClientCoachesResponse {
  trainer:      CoachInfo | null;
  nutritionist: CoachInfo | null;
  coach:        CoachInfo | null;
}

// ── Query keys ────────────────────────────────────────────────────────────────

export const activeInvitesKey = (role: CoachingRole) =>
  [role, 'invites', 'active'] as const;

export const clientCoachesKey = ['client', 'coaches'] as const;

// ── Staff hooks ───────────────────────────────────────────────────────────────

/** Fetch all active (unused, unexpired) invites for the current staff member. */
export function useActiveInvites(role: CoachingRole) {
  return useQuery<InviteResponse[]>({
    queryKey: activeInvitesKey(role),
    queryFn: () =>
      api.get<InviteResponse[]>(`/${role}/invites`).then((r) => r.data),
    staleTime: 1000 * 30, // invites change frequently — short stale time
  });
}

/** Generate a new invite code. */
export function useGenerateInvite(role: CoachingRole) {
  const queryClient = useQueryClient();
  return useMutation<InviteResponse, Error>({
    mutationFn: () =>
      api.post<InviteResponse>(`/${role}/invites`).then((r) => r.data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: activeInvitesKey(role) }),
  });
}

/** Revoke (delete) an active invite code. */
export function useRevokeInvite(role: CoachingRole) {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (inviteId) =>
      api.delete(`/${role}/invites/${inviteId}`).then(() => undefined),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: activeInvitesKey(role) }),
  });
}

// ── Client hooks ──────────────────────────────────────────────────────────────

/** Get the client's current coaching assignments. */
export function useClientCoaches() {
  return useQuery<ClientCoachesResponse>({
    queryKey: clientCoachesKey,
    queryFn: () =>
      api.get<ClientCoachesResponse>('/client/coaches').then((r) => r.data),
    staleTime: 1000 * 60, // refresh every minute
  });
}

/** Accept an invite code to connect with a coach. */
export function useConnectWithCoach() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (code) =>
      api.post('/client/connect', { code }).then(() => undefined),
    onSuccess: () => {
      // Refresh the client's coaches list immediately
      void queryClient.invalidateQueries({ queryKey: clientCoachesKey });
    },
  });
}
