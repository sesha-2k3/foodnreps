import { CommentResponse } from "../../hooks/usePlanComments";

const ROLE_LABELS: Record<string, string> = {
  fitness_trainer: "Fitness Trainer",
  nutritionist: "Nutritionist",
  master_coach: "Master Coach",
  super_admin: "Super Admin",
  client: "Client",
};

const ROLE_COLOURS: Record<string, string> = {
  fitness_trainer: "bg-green-100 text-green-800",
  nutritionist: "bg-purple-100 text-purple-800",
  master_coach: "bg-orange-100 text-orange-800",
  super_admin: "bg-red-100 text-red-800",
  client: "bg-blue-100 text-blue-800",
};

interface CommentBubbleProps {
  comment: CommentResponse;
  currentUserId: string;
  currentUserRole: string;
  onDelete: (id: string) => void;
  isDeleting: boolean;
}

export function CommentBubble({
  comment,
  currentUserId,
  currentUserRole,
  onDelete,
  isDeleting,
}: CommentBubbleProps) {
  const isOwn = comment.author.id === currentUserId;
  const canDelete =
    !comment.is_deleted &&
    (isOwn || currentUserRole === "super_admin");

  return (
    <div className={`flex gap-3 ${isOwn ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div className="shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-600 uppercase">
        {comment.author.full_name.charAt(0)}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] ${isOwn ? "items-end" : "items-start"} flex flex-col gap-1`}>
        {/* Author + role */}
        {!comment.is_deleted && (
          <div className={`flex items-center gap-2 ${isOwn ? "flex-row-reverse" : ""}`}>
            <span className="text-xs font-semibold text-gray-700">
              {comment.author.full_name}
            </span>
            <span
              className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                ROLE_COLOURS[comment.author.role] ?? "bg-gray-100 text-gray-700"
              }`}
            >
              {ROLE_LABELS[comment.author.role] ?? comment.author.role}
            </span>
          </div>
        )}

        {/* Body */}
        <div
          className={`px-3 py-2 rounded-2xl text-sm leading-relaxed ${
            comment.is_deleted
              ? "bg-gray-100 text-gray-400 italic"
              : isOwn
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-900"
          }`}
        >
          {comment.body}
        </div>

        {/* Timestamp + edited + delete */}
        <div className={`flex items-center gap-2 ${isOwn ? "flex-row-reverse" : ""}`}>
          <time className="text-[10px] text-gray-400">
            {new Date(comment.created_at).toLocaleString()}
          </time>
          {comment.is_edited && !comment.is_deleted && (
            <span className="text-[10px] text-gray-400">(edited)</span>
          )}
          {canDelete && (
            <button
              onClick={() => onDelete(comment.id)}
              disabled={isDeleting}
              className="text-[10px] text-red-400 hover:text-red-600 disabled:opacity-50"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
