/**
 * Coach client workout view.
 *
 * Master coach owns both workout and diet domains. Unlike the trainer
 * view (which shows diet as read-only), the coach has a separate
 * /coach/clients/:id/diet route for full diet editing. This page is
 * workout-only — no tabs needed. Navigation to diet goes through the
 * client list link.
 *
 * Design choice — separate pages for coach workout/diet vs tabs for trainer:
 *   Trainer sees workout + read-only diet on one page (two contexts, one
 *   page) because diet is secondary context for the trainer.
 *   Coach has full ownership of both — separate pages keeps each domain
 *   focused and avoids a single page that tries to do too much.
 */

import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ProgrammeBuilder } from '../../components/programme/ProgrammeBuilder';
import { useCoachProgramme } from '../../hooks/useCoachProgramme';
import { CommentThread } from '../../components/comments/CommentThread';

export function CoachClientWorkout() {
  const { id: clientId = '' } = useParams<{ id: string }>();
  const { data: programme, isLoading } = useCoachProgramme('coach', clientId);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Breadcrumb / switch to diet */}
      <div className="flex items-center justify-between mb-6">
        <Link
          to="/coach/clients"
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Clients
        </Link>
        <Link
          to={`/coach/clients/${clientId}/diet`}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 rounded-lg transition-colors"
        >
          Switch to Diet
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </Link>
      </div>

      {isLoading
        ? <div className="h-48 bg-gray-100 rounded-xl animate-pulse" />
        : <>
            <ProgrammeBuilder
              clientId={clientId}
              clientName="Client"
              rolePrefix="coach"
              programme={programme ?? null}
            />
            {programme && (
              <CommentThread planType="workout" planId={programme.id} />
            )}
          </>
      }
    </div>
  );
}

export default CoachClientWorkout;