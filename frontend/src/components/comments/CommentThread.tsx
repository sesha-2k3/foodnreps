/**
 * CommentThread — mount below any plan view.
 *
 * Usage:
 *   <CommentThread planType="workout" planId={programme.id} />
 *   <CommentThread planType="diet"    planId={plan.id} />
 *
 * Reads currentUserId + currentUserRole from the auth token via useCurrentUser().
 * Hides CommentInput for clients (Phase 1: read-only for clients).
 */

import { useRef, useEffect } from "react";
import { CommentBubble } from "./CommentBubble";
import { CommentInput } from "./CommentInput";
import {
  usePlanComments,
  useAddComment,
  useDeleteComment,
  type PlanType,
} from "../../hooks/usePlanComments";
import { useCurrentUser } from "../../hooks/useCurrentUser";

interface CommentThreadProps {
  planType: PlanType;
  planId: string;
}

export function CommentThread({ planType, planId }: CommentThreadProps) {
  const currentUser = useCurrentUser();
  const { data: comments, isLoading, error } = usePlanComments(planType, planId);
  const addComment = useAddComment(planType, planId);
  const deleteComment = useDeleteComment(planType, planId);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when new comments arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [comments?.length]);

  if (!currentUser) return null;

  const canWrite = currentUser.role !== "client";

  return (
    <div className="mt-6 border-t border-gray-100 pt-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">
        Comments
        {comments && comments.length > 0 && (
          <span className="ml-2 text-xs font-normal text-gray-400">
            {comments.filter((c) => !c.is_deleted).length}
          </span>
        )}
      </h3>

      {isLoading && (
        <p className="text-sm text-gray-400 py-4 text-center">Loading comments…</p>
      )}

      {error && (
        <p className="text-sm text-red-400 py-4 text-center">Failed to load comments.</p>
      )}

      {comments && comments.length === 0 && (
        <p className="text-sm text-gray-400 italic py-4 text-center">
          No comments yet.
          {canWrite && " Be the first to leave a note for the team."}
        </p>
      )}

      {comments && comments.length > 0 && (
        <div className="space-y-4 max-h-96 overflow-y-auto pr-1 pb-2">
          {comments.map((comment) => (
            <CommentBubble
              key={comment.id}
              comment={comment}
              currentUserId={currentUser.id}
              currentUserRole={currentUser.role}
              onDelete={(id) => deleteComment.mutate(id)}
              isDeleting={deleteComment.isPending}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {canWrite && (
        <CommentInput
          onSubmit={(body) => addComment.mutateAsync(body)}
          isPending={addComment.isPending}
        />
      )}
    </div>
  );
}
