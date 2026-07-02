import { useState, useRef, useEffect } from "react";

interface CommentInputProps {
  onSubmit: (body: string) => Promise<void>;
  isPending: boolean;
}

export function CommentInput({ onSubmit, isPending }: CommentInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  async function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || isPending) return;
    await onSubmit(trimmed);
    setValue("");
  }

  return (
    <div className="flex gap-2 items-end pt-3 border-t border-gray-100">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void handleSubmit();
          }
        }}
        placeholder="Add a comment… (Enter to send, Shift+Enter for new line)"
        className="flex-1 resize-none border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 max-h-32 overflow-y-auto"
        disabled={isPending}
      />
      <button
        onClick={handleSubmit}
        disabled={!value.trim() || isPending}
        className="shrink-0 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-40"
      >
        {isPending ? "…" : "Send"}
      </button>
    </div>
  );
}
