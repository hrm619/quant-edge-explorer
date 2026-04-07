import { useEffect, useRef } from "react";
import { MessageBubble } from "./MessageBubble";
import { PlanCard } from "./PlanCard";
import { StreamingIndicator } from "./StreamingIndicator";
import { ScrollArea } from "@/components/ui/scroll-area";
import type {
  MessageResponse,
  ArtifactDetail,
  Phase,
  StreamingArtifact,
} from "@/lib/types";

interface MessageListProps {
  messages: MessageResponse[];
  artifacts: Map<string, ArtifactDetail>;
  plan: string | null;
  phase: Phase;
  isStreaming: boolean;
  streamingText: string;
  currentToolName: string | null;
  streamingArtifacts: StreamingArtifact[];
}

// Synthetic message injected by the agent loop — filter from display
const SYNTHETIC_PROCEED = "Proceed with the research plan. Execute your queries and analysis now.";

export function MessageList({
  messages,
  artifacts,
  plan,
  phase,
  isStreaming,
  streamingText,
  currentToolName,
  streamingArtifacts,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);

  // Track whether user is near the bottom
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const viewport = container.querySelector("[data-radix-scroll-area-viewport]");
    if (!viewport) return;

    function handleScroll() {
      if (!viewport) return;
      const { scrollTop, scrollHeight, clientHeight } = viewport;
      isNearBottomRef.current = scrollHeight - scrollTop - clientHeight < 100;
    }

    viewport.addEventListener("scroll", handleScroll);
    return () => viewport.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-scroll when new content arrives, but only if user is near bottom
  useEffect(() => {
    if (isNearBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, streamingText, plan, phase, currentToolName]);

  // Build artifact spec map for inline rendering
  const artifactSpecs = new Map<string, Record<string, unknown>>();
  for (const [id, a] of artifacts) {
    if ("spec" in a && a.spec) {
      artifactSpecs.set(id, a.spec);
    }
  }

  // Build per-message artifact list
  function getArtifactsForMessage(msg: MessageResponse) {
    return [...artifacts.values()].filter((a) =>
      msg.tool_calls.some((tc) => tc.id === a.tool_call_id)
    );
  }

  // Filter messages for display
  const displayMessages = messages.filter((msg) => {
    // Hide synthetic "proceed" messages
    if (msg.role === "user" && msg.content.trim() === SYNTHETIC_PROCEED) return false;
    return true;
  });

  return (
    <ScrollArea className="flex-1" ref={scrollContainerRef}>
      <div className="max-w-3xl mx-auto px-4 py-6">
        {displayMessages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-[60vh] text-neutral-400">
            <p className="text-lg font-medium mb-2">Quant-Edge Explorer</p>
            <p className="text-sm">Ask a question about the data to get started.</p>
          </div>
        )}

        {displayMessages.map((msg) => {
          // Render planning-phase assistant messages as PlanCards
          if (msg.role === "assistant" && msg.phase === "planning") {
            return <PlanCard key={msg.id} text={msg.content} />;
          }

          const msgArtifacts = msg.role === "assistant" ? getArtifactsForMessage(msg) : undefined;

          return (
            <MessageBubble
              key={msg.id}
              role={msg.role as "user" | "assistant"}
              content={msg.content}
              toolCalls={msg.role === "assistant" ? msg.tool_calls : undefined}
              artifacts={msgArtifacts}
              artifactSpecs={artifactSpecs}
            />
          );
        })}

        {/* Streaming state */}
        {isStreaming && (
          <>
            {plan && <PlanCard text={plan} isStreaming />}

            {/* Streaming artifacts (before final reconciliation) */}
            {streamingArtifacts.map((sa) => (
              <div key={sa.id} className="my-2">
                <div className="text-xs text-neutral-400 mb-1">
                  {sa.kind === "table" ? "Table" : sa.kind === "chart" ? "Chart" : "Citations"}
                  {sa.title && `: ${sa.title}`}
                </div>
              </div>
            ))}

            {streamingText && (
              <MessageBubble role="assistant" content={streamingText} />
            )}

            <StreamingIndicator phase={phase} currentToolName={currentToolName} />
          </>
        )}

        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
