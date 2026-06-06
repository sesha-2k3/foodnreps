import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface UserListResponse {
  users: AdminUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateUserPayload {
  email: string;
  password: string;
  full_name: string;
  role: string;
}

export function useAdminUsers(params: {
  role?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}) {
  return useQuery<UserListResponse>({
    queryKey: ["admin", "users", params],
    queryFn: async () => {
      const { data } = await api.get("/admin/users", { params });
      return data;
    },
  });
}

export function useAdminUser(userId: string | undefined) {
  return useQuery<AdminUser>({
    queryKey: ["admin", "users", userId],
    queryFn: async () => {
      const { data } = await api.get(`/admin/users/${userId}`);
      return data;
    },
    enabled: !!userId,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateUserPayload) => {
      const { data } = await api.post("/admin/users", payload);
      return data as AdminUser;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/admin/users/${userId}/deactivate`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}
