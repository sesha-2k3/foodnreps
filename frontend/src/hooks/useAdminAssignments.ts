import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";

export interface AssignmentResponse {
  id: string;
  client_id: string;
  staff_id: string;
  staff_role: string;
  assigned_at: string;
  ended_at: string | null;
  assigned_by: string;
}

export interface ClientAssignmentsResponse {
  fitness_trainer: AssignmentResponse | null;
  nutritionist: AssignmentResponse | null;
  master_coach: AssignmentResponse | null;
}

export function useClientAssignments(clientId: string | undefined) {
  return useQuery<ClientAssignmentsResponse>({
    queryKey: ["admin", "assignments", clientId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/users/${clientId}/assignments`);
      return data;
    },
    enabled: !!clientId,
  });
}

export function useAssignStaff(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { staff_id: string; staff_role: string }) => {
      const { data } = await api.post(`/admin/users/${clientId}/assignments`, payload);
      return data as AssignmentResponse;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "assignments", clientId] });
    },
  });
}

export function useEndAssignment(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ assignmentId, reason }: { assignmentId: string; reason: string }) => {
      await api.delete(`/admin/assignments/${assignmentId}`, {
        data: { ended_reason: reason },
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "assignments", clientId] });
    },
  });
}

export function useOverrideWorkout(clientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (overrideReason: string) => {
      const { data } = await api.post(`/admin/clients/${clientId}/workout/override`, {
        override_reason: overrideReason,
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "clients", clientId, "workout"] });
    },
  });
}
