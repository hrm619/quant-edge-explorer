import type { Phase } from "@/lib/types";
import { toolDisplayName } from "@/lib/utils";

interface StreamingIndicatorProps {
  phase: Phase;
  currentToolName: string | null;
}

function statusText(phase: Phase, toolName: string | null): string {
  if (phase === "planning") return "Planning research approach...";
  if (toolName) return `Running ${toolDisplayName(toolName)}...`;
  return "Thinking...";
}

export function StreamingIndicator({ phase, currentToolName }: StreamingIndicatorProps) {
  return (
    <div className="flex items-center gap-2 px-4 py-2 text-xs text-neutral-500">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
      </span>
      {statusText(phase, currentToolName)}
    </div>
  );
}
