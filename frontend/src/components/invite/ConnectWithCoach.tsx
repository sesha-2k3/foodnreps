/**
 * ConnectWithCoach — client-side invite acceptance + current coaches display.
 *
 * Shows:
 *   - Current coaching staff (trainer / nutritionist / coach) with badges
 *   - "Connect with a coach" form (code input + submit)
 *   - Success / conflict error feedback
 *
 * Place at: src/components/invite/ConnectWithCoach.tsx
 * Used by: pages/client/Dashboard.tsx
 */

import React, { useState } from 'react';
import { useClientCoaches, useConnectWithCoach } from '../../hooks/useInvites';
import type { CoachInfo } from '../../hooks/useInvites';

// ── Coach card ────────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  fitness_trainer: { label: 'Trainer',       color: 'text-blue-700',  bg: 'bg-blue-50'  },
  nutritionist:    { label: 'Nutritionist',   color: 'text-green-700', bg: 'bg-green-50' },
  master_coach:    { label: 'Master Coach',   color: 'text-purple-700',bg: 'bg-purple-50'},
};

function CoachCard({ coach }: { coach: CoachInfo }) {
  const style = ROLE_LABELS[coach.role] ?? { label: coach.role, color: 'text-gray-700', bg: 'bg-gray-50' };
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-white rounded-xl border border-gray-200">
      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center text-slate-600 text-sm font-semibold flex-shrink-0">
        {coach.full_name.charAt(0).toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-gray-900 truncate">{coach.full_name}</p>
        <p className="text-xs text-gray-500 truncate">{coach.email}</p>
      </div>
      <span className={`flex-shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full ${style.bg} ${style.color}`}>
        {style.label}
      </span>
    </div>
  );
}

function EmptyCoachSlot({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 rounded-xl border border-dashed border-gray-200">
      <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
        <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      </div>
      <p className="text-sm text-gray-400 italic">No {label} assigned</p>
    </div>
  );
}

// ── Connect form ──────────────────────────────────────────────────────────────

function ConnectForm() {
  const [code, setCode] = useState('');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const connect = useConnectWithCoach();

  // Auto-format: insert hyphen after 3 chars, uppercase
  function handleCodeChange(raw: string) {
    const clean = raw.toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (clean.length <= 3) {
      setCode(clean);
    } else {
      setCode(`${clean.slice(0, 3)}-${clean.slice(3, 6)}`);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSuccessMsg(null);
    await connect.mutateAsync(code);
    setSuccessMsg("Connected! Your coach will now appear above.");
    setCode('');
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="mt-4">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
        Enter an invite code
      </p>
      <div className="flex gap-2">
        <input
          type="text"
          value={code}
          onChange={(e) => handleCodeChange(e.target.value)}
          placeholder="ABC-123"
          maxLength={7}
          className="flex-1 px-3 py-2.5 text-sm font-mono tracking-widest border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase placeholder:normal-case placeholder:tracking-normal"
          disabled={connect.isPending}
        />
        <button
          type="submit"
          disabled={code.length < 7 || connect.isPending}
          className="px-4 py-2.5 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-40 transition-colors"
        >
          {connect.isPending ? '…' : 'Connect'}
        </button>
      </div>

      {connect.isError && (
        <p className="mt-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          {(connect.error as Error)?.message ?? 'Invalid or expired code. Please try again.'}
        </p>
      )}
      {successMsg && (
        <p className="mt-2 text-xs text-green-700 bg-green-50 px-3 py-2 rounded-lg">
          {successMsg}
        </p>
      )}
      <p className="mt-2 text-[11px] text-gray-400">
        Ask your trainer, nutritionist, or coach to generate a code for you.
      </p>
    </form>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function ConnectWithCoach() {
  const { data: coaches, isLoading } = useClientCoaches();

  const hasAnyCoach =
    coaches && (coaches.trainer || coaches.nutritionist || coaches.coach);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">Your coaching staff</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Connect with a trainer, nutritionist, or coach using their invite code.
        </p>
      </div>

      <div className="px-5 py-4 space-y-2">
        {isLoading ? (
          [1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-gray-100 rounded-xl animate-pulse" />
          ))
        ) : (
          <>
            {coaches?.trainer
              ? <CoachCard coach={coaches.trainer} />
              : <EmptyCoachSlot label="trainer" />
            }
            {coaches?.nutritionist
              ? <CoachCard coach={coaches.nutritionist} />
              : <EmptyCoachSlot label="nutritionist" />
            }
            {coaches?.coach
              ? <CoachCard coach={coaches.coach} />
              : <EmptyCoachSlot label="master coach" />
            }
          </>
        )}
      </div>

      <div className="px-5 pb-5">
        <ConnectForm />
      </div>
    </div>
  );
}
