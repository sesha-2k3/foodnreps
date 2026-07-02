import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";

export interface CommentAuthor {
  id: string;
  full_name: string;
  role: string;
}

export interface CommentResponse {
  id: string;
  plan_type: string;
  plan_id: string;
  author: CommentAuthor;
  body: string;
  is_deleted: boolean;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
}

export type PlanType = "workout" | "diet";

function commentKey(planType: PlanType, planId: string) {
  return ["comments", planType, planId] as const;
}

export function usePlanComments(planType: PlanType, planId: string) {
  return useQuery<CommentResponse[]>({
    queryKey: commentKey(planType, planId),
    queryFn: async () => {
      const { data } = await api.get(`/plans/${planType}/${planId}/comments`);
      return data;
    },
    enabled: !!planId,
  });
}

export function useAddComment(planType: PlanType, planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: string) => {
      const { data } = await api.post(`/plans/${planType}/${planId}/comments`, { body });
      return data as CommentResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: commentKey(planType, planId) }),
  });
}

export function useDeleteComment(planType: PlanType, planId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (commentId: string) => {
      await api.delete(`/plans/${planType}/${planId}/comments/${commentId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: commentKey(planType, planId) }),
  });
}
