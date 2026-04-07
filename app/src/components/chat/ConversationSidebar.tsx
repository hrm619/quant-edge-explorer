import { useNavigate, useParams } from "react-router-dom";
import { Plus, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn, formatRelativeDate } from "@/lib/utils";
import type { ConversationSummary } from "@/lib/types";

interface ConversationSidebarProps {
  grouped: Map<string, ConversationSummary[]>;
  isLoading: boolean;
  onNewConversation: () => void;
}

const BUCKET_ORDER = ["Today", "Yesterday", "This Week", "Last Week", "Older"];

export function ConversationSidebar({
  grouped,
  isLoading,
  onNewConversation,
}: ConversationSidebarProps) {
  const navigate = useNavigate();
  const { conversationId } = useParams();

  function handleNew() {
    onNewConversation();
    navigate("/");
  }

  return (
    <div className="w-[280px] border-r border-surface-border flex flex-col bg-white shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-surface-border">
        <span className="text-sm font-semibold text-neutral-900">Explorer</span>
        <Button variant="ghost" size="sm" onClick={handleNew} title="New conversation">
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Conversation list */}
      <ScrollArea className="flex-1">
        <div className="py-2">
          {isLoading && (
            <p className="px-3 py-2 text-xs text-neutral-400">Loading...</p>
          )}

          {!isLoading && grouped.size === 0 && (
            <p className="px-3 py-4 text-xs text-neutral-400 text-center">
              No conversations yet
            </p>
          )}

          {BUCKET_ORDER.map((bucket) => {
            const items = grouped.get(bucket);
            if (!items || items.length === 0) return null;

            return (
              <div key={bucket} className="mb-2">
                <p className="px-3 py-1 text-xs font-medium text-neutral-400 uppercase tracking-wider">
                  {bucket}
                </p>
                {items.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => navigate(`/c/${conv.id}`)}
                    className={cn(
                      "w-full text-left px-3 py-1.5 text-sm hover:bg-surface-muted transition-colors duration-100",
                      conversationId === conv.id && "bg-surface-muted"
                    )}
                  >
                    <div className="flex items-center gap-1">
                      {conv.starred === 1 && (
                        <Star className="h-3 w-3 text-accent shrink-0 fill-accent" />
                      )}
                      <span className={cn(
                        "truncate",
                        conv.title ? "text-neutral-800" : "text-neutral-400 italic"
                      )}>
                        {conv.title ?? "Untitled"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-neutral-400">
                        {formatRelativeDate(conv.updated_at)}
                      </span>
                      <span className="text-xs text-neutral-300">
                        {conv.message_count} msg{conv.message_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
