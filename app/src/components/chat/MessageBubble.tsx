import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { ToolCallCard } from "./ToolCallCard";
import { ArtifactRenderer } from "@/components/artifacts/ArtifactRenderer";
import type { ToolCallResponse, ArtifactSummary } from "@/lib/types";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCallResponse[];
  artifacts?: ArtifactSummary[];
  artifactSpecs?: Map<string, Record<string, unknown>>;
}

export function MessageBubble({
  role,
  content,
  toolCalls,
  artifacts,
  artifactSpecs,
}: MessageBubbleProps) {
  if (role === "user") {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[75%] rounded bg-surface-muted px-3 py-2 text-sm">
          {content}
        </div>
      </div>
    );
  }

  // Build a map of tool_call_id -> artifact for inline rendering
  const artifactByToolCall = new Map<string, ArtifactSummary>();
  if (artifacts) {
    for (const a of artifacts) {
      artifactByToolCall.set(a.tool_call_id, a);
    }
  }

  return (
    <div className="mb-3">
      {/* Assistant prose */}
      <div
        className={cn(
          "prose prose-sm max-w-none",
          "prose-headings:font-semibold prose-headings:text-neutral-900",
          "prose-p:text-neutral-800 prose-p:leading-relaxed",
          "prose-code:text-sm prose-code:font-mono prose-code:bg-surface-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded",
          "prose-pre:bg-surface-muted prose-pre:border prose-pre:border-surface-border prose-pre:rounded",
          "prose-table:text-sm prose-th:text-left prose-th:font-medium",
        )}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>

      {/* Tool calls + inline artifacts */}
      {toolCalls && toolCalls.length > 0 && (
        <div className="mt-2 space-y-1">
          {toolCalls.map((tc) => {
            const artifact = artifactByToolCall.get(tc.id);
            return (
              <div key={tc.id}>
                <ToolCallCard toolCall={tc} />
                {artifact && (
                  <ArtifactRenderer
                    id={artifact.id}
                    kind={artifact.kind}
                    title={artifact.title}
                    spec={artifactSpecs?.get(artifact.id) ?? {}}
                    qualityFlag={artifact.quality_flag}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
