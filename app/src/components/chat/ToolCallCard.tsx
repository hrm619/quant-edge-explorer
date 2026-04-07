import { useState } from "react";
import {
  Database,
  Search,
  BarChart3,
  ChevronDown,
  ChevronRight,
  Check,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { toolDisplayName, toolSummary, formatDuration, cn } from "@/lib/utils";
import type { ToolCallResponse } from "@/lib/types";

function toolIcon(name: string) {
  switch (name) {
    case "query_sql":
      return Database;
    case "search_knowledge_base":
      return Search;
    case "generate_chart":
      return BarChart3;
    default:
      return Database;
  }
}

interface ToolCallCardProps {
  toolCall: ToolCallResponse;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [open, setOpen] = useState(false);
  const Icon = toolIcon(toolCall.tool_name);
  const isError = toolCall.status === "error";

  // Parse row_count from tool_result if available
  let rowCount: number | undefined;
  if (toolCall.tool_result) {
    try {
      const parsed = JSON.parse(toolCall.tool_result);
      rowCount = parsed.row_count;
    } catch {
      // ignore
    }
  }

  const summary = toolSummary(
    toolCall.tool_name,
    toolCall.tool_input,
    toolCall.status,
    rowCount
  );

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="my-1 border border-surface-border rounded overflow-hidden">
        <CollapsibleTrigger asChild>
          <button className="w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-surface-muted">
            <Icon className="h-3.5 w-3.5 text-neutral-500 shrink-0" />
            <span className="font-medium text-neutral-700">
              {toolDisplayName(toolCall.tool_name)}
            </span>
            {isError ? (
              <Badge variant="destructive">
                <X className="h-3 w-3 mr-0.5" /> Error
              </Badge>
            ) : (
              <Badge variant="success">
                <Check className="h-3 w-3 mr-0.5" /> OK
              </Badge>
            )}
            {toolCall.duration_ms != null && (
              <span className="text-neutral-400">
                {formatDuration(toolCall.duration_ms)}
              </span>
            )}
            <span className="text-neutral-400 truncate ml-1">{summary}</span>
            <span className="ml-auto shrink-0">
              {open ? (
                <ChevronDown className="h-3.5 w-3.5 text-neutral-400" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 text-neutral-400" />
              )}
            </span>
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="border-t border-surface-border px-3 py-2">
            <p className="text-xs font-medium text-neutral-500 mb-1">Input</p>
            <pre className={cn(
              "text-xs font-mono bg-surface-muted rounded p-2 overflow-x-auto max-h-48",
              "text-neutral-700"
            )}>
              {JSON.stringify(toolCall.tool_input, null, 2)}
            </pre>
            {isError && toolCall.error_message && (
              <div className="mt-2">
                <p className="text-xs font-medium text-trust-untrusted mb-1">Error</p>
                <pre className="text-xs font-mono bg-red-50 text-trust-untrusted rounded p-2 overflow-x-auto">
                  {toolCall.error_message}
                </pre>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}
