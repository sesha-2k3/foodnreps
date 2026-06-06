import React from 'react';
import { ClientListView } from '../../components/shared/ClientListView';
import { InviteGenerator } from '../../components/invite/InviteGenerator';
import { useAssignedClients } from '../../hooks/useAssignedClients';

export function NutritionistClientList() {
  const { data: clients = [], isLoading } = useAssignedClients('nutritionist');
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Your clients</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Manage diet plans for your assigned clients.
        </p>
      </div>
      <InviteGenerator role="nutritionist" />
      <ClientListView clients={clients} role="nutritionist" isLoading={isLoading} />
    </div>
  );
}
export default NutritionistClientList;