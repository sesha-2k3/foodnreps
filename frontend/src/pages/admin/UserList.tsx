import { useState } from "react";
import { Link } from "react-router-dom";
import { useAdminUsers, useDeactivateUser, AdminUser } from "../../hooks/useAdminUsers";

const ROLES = ["client", "fitness_trainer", "nutritionist", "master_coach", "super_admin"];

const ROLE_LABELS: Record<string, string> = {
  client: "Client",
  fitness_trainer: "Fitness Trainer",
  nutritionist: "Nutritionist",
  master_coach: "Master Coach",
  super_admin: "Super Admin",
};

const ROLE_COLOURS: Record<string, string> = {
  client: "bg-blue-100 text-blue-800",
  fitness_trainer: "bg-green-100 text-green-800",
  nutritionist: "bg-purple-100 text-purple-800",
  master_coach: "bg-orange-100 text-orange-800",
  super_admin: "bg-red-100 text-red-800",
};

const LIMIT = 20;

export default function UserList() {
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [activeFilter, setActiveFilter] = useState<string>("");
  const [offset, setOffset] = useState(0);
  const [confirmDeactivate, setConfirmDeactivate] = useState<AdminUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  const params: Record<string, unknown> = { limit: LIMIT, offset };
  if (roleFilter) params.role = roleFilter;
  if (activeFilter !== "") params.is_active = activeFilter === "active";

  const { data, isLoading } = useAdminUsers(params as Parameters<typeof useAdminUsers>[0]);
  const deactivate = useDeactivateUser();

  const totalPages = data ? Math.ceil(data.total / LIMIT) : 0;
  const currentPage = Math.floor(offset / LIMIT) + 1;

  async function handleDeactivate(user: AdminUser) {
    setError(null);
    try {
      await deactivate.mutateAsync(user.id);
      setConfirmDeactivate(null);
    } catch {
      setError("Failed to deactivate user.");
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
        <Link
          to="/admin/users/new"
          className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
        >
          + New User
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-4">
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setOffset(0); }}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="">All roles</option>
          {ROLES.map((r) => (
            <option key={r} value={r}>{ROLE_LABELS[r]}</option>
          ))}
        </select>
        <select
          value={activeFilter}
          onChange={(e) => { setActiveFilter(e.target.value); setOffset(0); }}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="text-gray-500 py-8 text-center">Loading users…</div>
      ) : (
        <>
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {["Name", "Email", "Role", "Status", "Created", "Actions"].map((h) => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data?.users.map((user) => (
                  <tr key={user.id} className={!user.is_active ? "opacity-50" : ""}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{user.full_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{user.email}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${ROLE_COLOURS[user.role] ?? "bg-gray-100 text-gray-800"}`}>
                        {ROLE_LABELS[user.role] ?? user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${user.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-500"}`}>
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-sm space-x-3">
                      <Link
                        to={`/admin/users/${user.id}`}
                        className="text-indigo-600 hover:text-indigo-800 font-medium"
                      >
                        View
                      </Link>
                      {user.role === "client" && (
                        <Link
                          to={`/admin/users/${user.id}/assignments`}
                          className="text-purple-600 hover:text-purple-800 font-medium"
                        >
                          Assignments
                        </Link>
                      )}
                      {user.is_active && (
                        <button
                          onClick={() => setConfirmDeactivate(user)}
                          className="text-red-600 hover:text-red-800 font-medium"
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {data?.users.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-gray-400">
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
              <span>
                Showing {offset + 1}–{Math.min(offset + LIMIT, data?.total ?? 0)} of {data?.total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setOffset((p) => p - LIMIT)}
                  className="px-3 py-1 border rounded disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={currentPage >= totalPages}
                  onClick={() => setOffset((p) => p + LIMIT)}
                  className="px-3 py-1 border rounded disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Deactivate confirmation modal */}
      {confirmDeactivate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full shadow-xl">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Deactivate user?</h2>
            <p className="text-sm text-gray-600 mb-4">
              <strong>{confirmDeactivate.full_name}</strong> will be deactivated and all their
              refresh tokens revoked immediately. This cannot be undone — create a new account to
              restore access.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeactivate(null)}
                className="px-4 py-2 text-sm border rounded text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeactivate(confirmDeactivate)}
                disabled={deactivate.isPending}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {deactivate.isPending ? "Deactivating…" : "Deactivate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
