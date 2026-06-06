import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useAdminUsers, AdminUser } from "../../hooks/useAdminUsers";
import {
  useClientAssignments,
  useAssignStaff,
  useEndAssignment,
  AssignmentResponse,
} from "../../hooks/useAdminAssignments";

type SlotRole = "fitness_trainer" | "nutritionist" | "master_coach";

const SLOT_CONFIG: { role: SlotRole; label: string; staffRole: string }[] = [
  { role: "fitness_trainer", label: "Fitness Trainer", staffRole: "fitness_trainer" },
  { role: "nutritionist", label: "Nutritionist", staffRole: "nutritionist" },
  { role: "master_coach", label: "Master Coach", staffRole: "master_coach" },
];

interface StaffSelectorProps {
  role: SlotRole;
  current: AssignmentResponse | null;
  disabled: boolean;
  clientId: string;
}

export function StaffSlot({ role, current, disabled, clientId }: StaffSelectorProps) {
  const [selecting, setSelecting] = useState(false);
  const [selectedStaffId, setSelectedStaffId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: staffList } = useAdminUsers({
    role,
    is_active: true,
    limit: 100,
    offset: 0,
  });
  const assign = useAssignStaff(clientId);
  const endAssignment = useEndAssignment(clientId);

  const label = SLOT_CONFIG.find((s) => s.role === role)!.label;

  async function handleAssign() {
    if (!selectedStaffId) return;
    setError(null);
    try {
      await assign.mutateAsync({ staff_id: selectedStaffId, staff_role: role });
      setSelecting(false);
      setSelectedStaffId("");
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Assignment failed.";
      // Surface the conflict message verbatim (it's the prescribed error text)
      setError(msg);
    }
  }

  async function handleRemove() {
    if (!current) return;
    setError(null);
    try {
      await endAssignment.mutateAsync({
        assignmentId: current.id,
        reason: "Removed by super admin",
      });
    } catch {
      setError("Failed to remove assignment.");
    }
  }

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        {current ? (
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-900">
              Staff ID: <code className="text-xs bg-gray-100 px-1 rounded">{current.staff_id.slice(0, 8)}…</code>
            </span>
            {!disabled && (
              <>
                <button
                  onClick={() => setSelecting((v) => !v)}
                  className="text-sm text-indigo-600 hover:underline"
                >
                  Change
                </button>
                <button
                  onClick={handleRemove}
                  disabled={endAssignment.isPending}
                  className="text-sm text-red-600 hover:underline"
                >
                  Remove
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400 italic">unassigned</span>
            {!disabled && (
              <button
                onClick={() => setSelecting((v) => !v)}
                className="text-sm text-indigo-600 hover:underline"
              >
                Assign
              </button>
            )}
          </div>
        )}
      </div>

      {disabled && !current && (
        <p className="text-xs text-amber-600 mt-1">
          {role === "master_coach"
            ? "Remove the existing trainer/nutritionist before assigning a master coach."
            : "Remove the master coach before assigning a trainer or nutritionist."}
        </p>
      )}

      {selecting && (
        <div className="mt-3 space-y-2">
          <select
            value={selectedStaffId}
            onChange={(e) => setSelectedStaffId(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="">Select staff member…</option>
            {staffList?.users.map((s: AdminUser) => (
              <option key={s.id} value={s.id}>
                {s.full_name} — {s.email}
              </option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              onClick={handleAssign}
              disabled={!selectedStaffId || assign.isPending}
              className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm disabled:opacity-50"
            >
              {assign.isPending ? "Assigning…" : "Confirm"}
            </button>
            <button
              onClick={() => { setSelecting(false); setSelectedStaffId(""); setError(null); }}
              className="px-3 py-1.5 border rounded text-sm text-gray-600 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-600 mt-2">{error}</p>
      )}
    </div>
  );
}

export default function AssignmentManager() {
  const { id: clientId } = useParams<{ id: string }>();
  const { data: assignments, isLoading } = useClientAssignments(clientId);

  // Conflict rule: master_coach conflicts with trainer + nutritionist
  const hasMasterCoach = !!assignments?.master_coach;
  const hasTrainerOrNutritionist =
    !!assignments?.fitness_trainer || !!assignments?.nutritionist;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-6">
        <Link to={`/admin/users/${clientId}`} className="text-indigo-600 text-sm hover:underline">
          ← Back to user
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mt-2">Assignment Manager</h1>
        <p className="text-sm text-gray-500 mt-1">
          Client: <code className="text-xs bg-gray-100 px-1 rounded">{clientId}</code>
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-6 text-sm text-amber-800">
        A master coach handles both workout and diet — they cannot be combined with a fitness
        trainer or nutritionist on the same client.
      </div>

      {isLoading ? (
        <div className="text-gray-500">Loading assignments…</div>
      ) : (
        <div className="space-y-4">
          {SLOT_CONFIG.map(({ role }) => (
            <StaffSlot
              key={role}
              role={role}
              current={assignments?.[role] ?? null}
              disabled={
                role === "master_coach"
                  ? hasTrainerOrNutritionist
                  : hasMasterCoach
              }
              clientId={clientId!}
            />
          ))}
        </div>
      )}
    </div>
  );
}
