import { useState } from "react";
import { ChevronDown, ChevronRight, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface Citation {
  analyst?: string;
  title?: string;
  text?: string;
  trust_tier?: string;
  source_type?: string;
  distance?: number;
}

interface CitationArtifactProps {
  title: string | null;
  spec: Record<string, unknown>;
}

const COLLAPSED_LIMIT = 3;

export function CitationArtifact({ title, spec }: CitationArtifactProps) {
  const results = (spec.results as Citation[]) ?? [];
  const query = spec.query as string | undefined;
  const [expanded, setExpanded] = useState(results.length <= COLLAPSED_LIMIT);

  const visible = expanded ? results : results.slice(0, COLLAPSED_LIMIT);

  return (
    <div className="my-2 border border-surface-border rounded overflow-hidden">
      <div className="px-3 py-1.5 bg-surface-muted border-b border-surface-border">
        <span className="text-xs font-medium text-neutral-600">
          {title ?? (query ? `KB: "${query}"` : "Knowledge Base Results")}
          <span className="ml-1 text-neutral-400">({results.length})</span>
        </span>
      </div>

      <div className="divide-y divide-surface-border">
        {visible.map((cit, i) => (
          <div key={i} className="px-3 py-2">
            <div className="flex items-center gap-2 mb-0.5">
              <BookOpen className="h-3 w-3 text-neutral-400 shrink-0" />
              <span className="text-xs font-medium text-neutral-700 truncate">
                {cit.analyst ?? "Unknown"}
              </span>
              {cit.trust_tier && (
                <Badge variant={cit.trust_tier === "core" ? "success" : "default"}>
                  {cit.trust_tier}
                </Badge>
              )}
              {cit.source_type && (
                <span className="text-xs text-neutral-400">{cit.source_type}</span>
              )}
            </div>
            {cit.title && (
              <p className="text-xs font-medium text-neutral-600 mb-0.5">{cit.title}</p>
            )}
            {cit.text && (
              <p className="text-xs text-neutral-500 line-clamp-3">{cit.text}</p>
            )}
          </div>
        ))}
      </div>

      {results.length > COLLAPSED_LIMIT && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-center gap-1 py-1.5 text-xs text-neutral-500 hover:text-neutral-700 hover:bg-surface-muted border-t border-surface-border"
        >
          {expanded ? (
            <>
              <ChevronDown className="h-3 w-3" /> Show less
            </>
          ) : (
            <>
              <ChevronRight className="h-3 w-3" /> Show all {results.length} results
            </>
          )}
        </button>
      )}
    </div>
  );
}
