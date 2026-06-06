import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAdminUser, useCreateUser } from "../../hooks/useAdminUsers";
import { useDeactivateUser } from "../../hooks/useAdminUsers";

const ROLES = [
  { value: "client", label: "Client" },
  { value: "fitness_trainer", label: "Fitness Trainer" },
  { value: "nutritionist", label: "Nutritionist" },
  { value: "master_coach", label: "Master Coach" },
  { value: "super_admin", label: "Super Admin" },
];

const ROLE_COLOURS: Record<string, string> = {
  client: "bg-blue-100 text-blue-800",
  fitness_trainer: "bg-green-100 text-green-800",
  nutritionist: "bg-purple-100 text-purple-800",
  master_coach: "bg-orange-100 text-orange-800",
  super_admin: "bg-red-100 text-red-800",
};

// ── Create form (shown when id === "new") ─────────────────────────────────────

function CreateUserForm() {
  const navigate = useNavigate();
  const createUser = useCreateUser();
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "client" });
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);
    try {
      const user = await createUser.mutateAsync(form);
      navigate(`/admin/users/${user.id}`);
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to create user.";
      setError(msg);
    }
  }

  return (
    <div className="max-w-lg mx-auto p-6">
      <div className="mb-6">
        <Link to="/admin/users" className="text-indigo-600 text-sm hover:underline">
          ← Back to users
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mt-2">Create User</h1>
        <p className="text-sm text-gray-500 mt-1">
          Role cannot be changed after creation. Deactivate and create a new account to change role.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white shadow rounded-lg p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Full name</label>
          <input
            type="text"
            value={form.full_name}
            onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
          <select
            value={form.role}
            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>
        <div className="pt-2">
          <button
            onClick={handleSubmit}
            disabled={createUser.isPending || !form.email || !form.password || !form.full_name}
            className="w-full bg-indigo-600 text-white py-2 rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            {createUser.isPending ? "Creating…" : "Create user"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Detail view (existing user) ───────────────────────────────────────────────

export default function UserDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  if (id === "new") return <CreateUserForm />;

  const { data: user, isLoading } = useAdminUser(id);
  const deactivate = useDeactivateUser();
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDeactivate() {
    setError(null);
    try {
      await deactivate.mutateAsync(id!);
      setConfirmDeactivate(false);
    } catch {
      setError("Failed to deactivate user.");
    }
  }

  if (isLoading) {
    return <div className="p-6 text-gray-500">Loading…</div>;
  }

  if (!user) {
    return <div className="p-6 text-red-500">User not found.</div>;
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-6">
        <Link to="/admin/users" className="text-indigo-600 text-sm hover:underline">
          ← Back to users
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mt-2">{user.full_name}</h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white shadow rounded-lg p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Email</p>
            <p className="text-sm text-gray-900 mt-0.5">{user.email}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Role</p>
            <span className={`inline-flex mt-0.5 px-2 py-0.5 rounded text-xs font-semibold ${ROLE_COLOURS[user.role] ?? "bg-gray-100 text-gray-800"}`}>
              {ROLES.find((r) => r.value === user.role)?.label ?? user.role}
            </span>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Status</p>
            <span className={`inline-flex mt-0.5 px-2 py-0.5 rounded text-xs font-semibold ${user.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-500"}`}>
              {user.is_active ? "Active" : "Inactive"}
            </span>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Created</p>
            <p className="text-sm text-gray-900 mt-0.5">
              {new Date(user.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-4 flex gap-3">
        {user.role === "client" && (
          <>
            <Link
              to={`/admin/users/${user.id}/assignments`}
              className="px-4 py-2 border border-purple-300 text-purple-700 rounded-md text-sm hover:bg-purple-50"
            >
              Manage assignments
            </Link>
            <Link
              to={`/admin/clients/${user.id}/workout`}
              className="px-4 py-2 border border-indigo-300 text-indigo-700 rounded-md text-sm hover:bg-indigo-50"
            >
              View workout
            </Link>
            <Link
              to={`/admin/clients/${user.id}/diet`}
              className="px-4 py-2 border border-green-300 text-green-700 rounded-md text-sm hover:bg-green-50"
            >
              View diet
            </Link>
          </>
        )}
        {user.is_active && (
          <button
            onClick={() => setConfirmDeactivate(true)}
            className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700"
          >
            Deactivate account
          </button>
        )}
      </div>

      {/* Deactivate confirmation */}
      {confirmDeactivate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full shadow-xl">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Deactivate account?</h2>
            <p className="text-sm text-gray-600 mb-4">
              All refresh tokens will be revoked immediately. To restore access, deactivate and
              create a new account.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeactivate(false)}
                className="px-4 py-2 text-sm border rounded text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeactivate}
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
