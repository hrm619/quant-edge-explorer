import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Lightbulb } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";

interface PlanCardProps {
  text: string;
  isStreaming?: boolean;
}

export function PlanCard({ text, isStreaming = false }: PlanCardProps) {
  const [open, setOpen] = useState(isStreaming);

  // Auto-expand while streaming, auto-collapse when done
  useEffect(() => {
    if (isStreaming) setOpen(true);
  }, [isStreaming]);

  useEffect(() => {
    if (!isStreaming && open) {
      const timer = setTimeout(() => setOpen(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [isStreaming, open]);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div className="my-2 border border-amber-200 rounded bg-amber-50/50 overflow-hidden">
        <CollapsibleTrigger asChild>
          <button className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-50">
            <Lightbulb className="h-3.5 w-3.5" />
            <span className="uppercase tracking-wider">Research Plan</span>
            <span className="ml-auto">
              {open ? (
                <ChevronDown className="h-3.5 w-3.5" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5" />
              )}
            </span>
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="px-3 pb-2 text-sm text-amber-900 prose prose-sm prose-amber max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}
