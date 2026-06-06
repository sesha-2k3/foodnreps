import React from 'react';
import { ClientListView } from '../../components/shared/ClientListView';
import { InviteGenerator } from '../../components/invite/InviteGenerator';
import { useAssignedClients } from '../../hooks/useAssignedClients';

export function CoachClientList() {
  const { data: clients = [], isLoading } = useAssignedClients('coach');
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Your clients</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Manage workout and diet plans for your assigned clients.
        </p>
      </div>
      <InviteGenerator role="coach" />
      <ClientListView clients={clients} role="coach" isLoading={isLoading} />
    </div>
  );
}
export default CoachClientList;