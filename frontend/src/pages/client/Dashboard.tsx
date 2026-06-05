/**
 * Client Dashboard — welcome page and navigation hub.
 *
 * Shows the client's name, quick links to workout and diet views,
 * and handles the "no programme" state with a prompt to check
 * the personal plan section.
 *
 * Design choice — no data fetched here:
 *   The dashboard does not prefetch workout or diet data. Those views
 *   own their own queries. Prefetching here would add latency to the
 *   dashboard render (it must wait for the prefetch before displaying)
 *   and would waste the cache if the client navigates to neither view.
 *   TanStack Query's staleTime handles re-use: the data fetched in
 *   WorkoutView is available for 5 minutes before refetching.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useCurrentUser } from '../../hooks/useCurrentUser';

function NavCard({
  to,
  title,
  description,
  icon,
  accent,
}: {
  to: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  accent: string;
}) {
  return (
    <Link
      to={to}
      className="group flex items-start gap-4 p-5 bg-white rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all"
    >
      <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${accent}`}>
        {icon}
      </div>
      <div>
        <h3 className="text-sm font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
          {title}
        </h3>
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      </div>
      <svg
        className="ml-auto flex-shrink-0 w-4 h-4 text-gray-300 group-hover:text-gray-400 mt-0.5 transition-colors"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </Link>
  );
}

export function ClientDashboard() {
  const user = useCurrentUser();

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Welcome header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back
        </h1>
        <p className="text-sm text-gray-500 mt-1">Here's your training dashboard.</p>
      </div>

      {/* Assigned plans */}
      <section className="mb-6">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Your programme
        </h2>
        <div className="space-y-3">
          <NavCard
            to="/client/workout"
            title="Workout programme"
            description="View your training plan and log your sessions"
            accent="bg-blue-50 text-blue-600"
            icon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12h4l3-9 4 18 3-9h4" />
              </svg>
            }
          />
          <NavCard
            to="/client/diet"
            title="Diet plan"
            description="View your nutrition targets and macros"
            accent="bg-green-50 text-green-600"
            icon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            }
          />
        </div>
      </section>

      {/* Personal plans */}
      <section>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Personal plans
        </h2>
        <div className="space-y-3">
          <NavCard
            to="/personal/workout"
            title="Personal workout"
            description="Self-managed training when you don't have a coach"
            accent="bg-slate-50 text-slate-600"
            icon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            }
          />
          <NavCard
            to="/personal/diet"
            title="Personal diet"
            description="Build and track your own nutrition plan"
            accent="bg-amber-50 text-amber-600"
            icon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            }
          />
        </div>
      </section>
    </div>
  );
}

export default ClientDashboard;
