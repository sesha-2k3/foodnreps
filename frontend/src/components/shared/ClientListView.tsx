/**
 * ClientListView — shared client list component.
 *
 * Used by trainer/ClientList, nutritionist/ClientList, and coach/ClientList.
 * The role determines which action links appear per client row.
 *
 * Design choice — role-specific action links, not a shared "View" button:
 *   A trainer's "View" links to /trainer/clients/:id/workout.
 *   A nutritionist's links to /nutritionist/clients/:id/diet.
 *   A coach's row has two links: workout + diet.
 *   The action column is the only thing that differs by role. Everything
 *   else (client name, email, status badges) is identical.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import type { ClientSummaryResponse } from '../../types/api';
import type { CoachingRole } from '../../hooks/useAssignedClients';

interface ClientListViewProps {
  clients: ClientSummaryResponse[];
  role: CoachingRole;
  isLoading: boolean;
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
        active
          ? 'bg-green-50 text-green-700'
          : 'bg-gray-100 text-gray-500'
      }`}
    >
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

function PlanBadge({ label, hasData }: { label: string; hasData: boolean }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${
        hasData
          ? 'bg-blue-50 text-blue-700'
          : 'bg-gray-50 text-gray-400'
      }`}
    >
      {label}
    </span>
  );
}

function ActionLinks({
  client,
  role,
}: {
  client: ClientSummaryResponse;
  role: CoachingRole;
}) {
  if (role === 'trainer') {
    return (
      <Link
        to={`/trainer/clients/${client.id}/workout`}
        className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
      >
        Workout
      </Link>
    );
  }

  if (role === 'nutritionist') {
    return (
      <Link
        to={`/nutritionist/clients/${client.id}/diet`}
        className="px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded-lg transition-colors"
      >
        Diet
      </Link>
    );
  }

  // Master coach — both links
  return (
    <div className="flex items-center gap-2">
      <Link
        to={`/coach/clients/${client.id}/workout`}
        className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
      >
        Workout
      </Link>
      <Link
        to={`/coach/clients/${client.id}/diet`}
        className="px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded-lg transition-colors"
      >
        Diet
      </Link>
    </div>
  );
}

export function ClientListView({ clients, role, isLoading }: ClientListViewProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (clients.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
          <svg className="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-700">No clients assigned</p>
        <p className="text-xs text-gray-400 mt-1">A super admin assigns clients to coaching staff.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {clients.map((client) => (
        <div
          key={client.id}
          className="flex items-center justify-between px-5 py-4 bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all"
        >
          {/* Client info */}
          <div className="flex items-center gap-4 min-w-0">
            {/* Avatar placeholder */}
            <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center text-slate-600 text-sm font-semibold">
              {client.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">{client.full_name}</p>
              <p className="text-xs text-gray-500 truncate">{client.email}</p>
            </div>
          </div>

          {/* Right side: badges + actions */}
          <div className="flex items-center gap-3 flex-shrink-0 ml-4">
            <div className="hidden sm:flex items-center gap-1.5">
              <StatusBadge active={client.is_active} />
              <PlanBadge label="Workout" hasData={client.has_active_workout} />
              <PlanBadge label="Diet" hasData={client.has_active_diet} />
            </div>
            <ActionLinks client={client} role={role} />
          </div>
        </div>
      ))}
    </div>
  );
}
