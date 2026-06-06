/**
 * InviteGenerator — for coaching staff to generate and share invite codes.
 *
 * Shows:
 *   - "Generate invite code" button
 *   - The most recently generated code, large and copyable
 *   - List of all active (unused, unexpired) codes with revoke action
 *
 * Place at: src/components/invite/InviteGenerator.tsx
 * Used by: trainer/ClientList, nutritionist/ClientList, coach/ClientList
 */

import React, { useState } from 'react';
import { useActiveInvites, useGenerateInvite, useRevokeInvite } from '../../hooks/useInvites';
import type { CoachingRole } from '../../hooks/useAssignedClients';
import type { InviteResponse } from '../../hooks/useInvites';

interface InviteGeneratorProps {
  role: CoachingRole;
}

function ExpiryLabel({ expiresAt }: { expiresAt: string }) {
  const diff = new Date(expiresAt).getTime() - Date.now();
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
  if (days <= 0) return <span className="text-red-500 text-xs">Expired</span>;
  if (days === 1) return <span className="text-amber-600 text-xs">Expires tomorrow</span>;
  return <span className="text-gray-400 text-xs">Expires in {days} days</span>;
}

function CopyableCode({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    void navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="flex items-center gap-3 bg-gray-50 rounded-xl px-5 py-4 border border-gray-200">
      <span className="text-3xl font-mono font-bold tracking-widest text-gray-900 select-all">
        {code}
      </span>
      <button
        type="button"
        onClick={handleCopy}
        className={`ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
          copied
            ? 'bg-green-100 text-green-700'
            : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-100'
        }`}
      >
        {copied ? (
          <>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Copied!
          </>
        ) : (
          <>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Copy
          </>
        )}
      </button>
    </div>
  );
}

function ActiveInviteRow({
  invite,
  onRevoke,
  revoking,
}: {
  invite: InviteResponse;
  onRevoke: (id: string) => void;
  revoking: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-3">
        <span className="font-mono text-sm font-semibold text-gray-800 tracking-wider">
          {invite.code}
        </span>
        <ExpiryLabel expiresAt={invite.expires_at} />
      </div>
      <button
        type="button"
        onClick={() => onRevoke(invite.id)}
        disabled={revoking}
        className="text-xs text-red-500 hover:text-red-700 hover:bg-red-50 px-2.5 py-1 rounded-lg transition-colors disabled:opacity-40"
      >
        Revoke
      </button>
    </div>
  );
}

export function InviteGenerator({ role }: InviteGeneratorProps) {
  const { data: invites = [], isLoading } = useActiveInvites(role);
  const generate = useGenerateInvite(role);
  const revoke = useRevokeInvite(role);
  const [latestCode, setLatestCode] = useState<string | null>(null);

  async function handleGenerate() {
    const invite = await generate.mutateAsync();
    setLatestCode(invite.code);
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Invite a client</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Generate a code and share it with your client.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleGenerate()}
          disabled={generate.isPending}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
        >
          {generate.isPending ? (
            '…'
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Generate code
            </>
          )}
        </button>
      </div>

      {/* Latest generated code */}
      {latestCode && (
        <div className="px-5 py-4 bg-blue-50/50 border-b border-blue-100">
          <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider mb-2">
            Share this code with your client
          </p>
          <CopyableCode code={latestCode} />
          <p className="text-xs text-gray-500 mt-2">
            Valid for 7 days · Single use · Client enters it on their dashboard
          </p>
        </div>
      )}

      {/* Active invites list */}
      <div className="px-5 py-3">
        {generate.isError && (
          <p className="text-xs text-red-600 mb-3">
            {(generate.error as Error)?.message ?? 'Failed to generate code.'}
          </p>
        )}
        {isLoading ? (
          <div className="space-y-2 py-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : invites.length === 0 && !latestCode ? (
          <p className="text-xs text-gray-400 italic py-3 text-center">
            No active invite codes. Generate one above.
          </p>
        ) : invites.length > 0 ? (
          <div>
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Active codes ({invites.length})
            </p>
            {invites.map((invite) => (
              <ActiveInviteRow
                key={invite.id}
                invite={invite}
                onRevoke={(id) => void revoke.mutateAsync(id)}
                revoking={revoke.isPending}
              />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
