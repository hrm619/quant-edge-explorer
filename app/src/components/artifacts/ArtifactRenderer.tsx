import { Suspense, lazy } from "react";
import { TableArtifact } from "./TableArtifact";
import { CitationArtifact } from "./CitationArtifact";

const LazyChartArtifact = lazy(() =>
  import("./ChartArtifact").then((m) => ({ default: m.ChartArtifact }))
);

interface ArtifactRendererProps {
  id: string;
  kind: string;
  title: string | null;
  spec: Record<string, unknown>;
  qualityFlag: string;
}

export function ArtifactRenderer({ id, kind, title, spec, qualityFlag }: ArtifactRendererProps) {
  switch (kind) {
    case "table":
      return (
        <TableArtifact
          artifactId={id}
          title={title}
          spec={spec}
          qualityFlag={qualityFlag}
        />
      );
    case "chart":
      return (
        <Suspense
          fallback={
            <div className="my-2 border border-surface-border rounded p-8 text-center text-xs text-neutral-400">
              Loading chart...
            </div>
          }
        >
          <LazyChartArtifact
            artifactId={id}
            title={title}
            spec={spec}
            qualityFlag={qualityFlag}
          />
        </Suspense>
      );
    case "citation_set":
      return <CitationArtifact title={title} spec={spec} />;
    default:
      return (
        <pre className="my-2 p-3 bg-surface-muted rounded text-xs font-mono overflow-x-auto">
          {JSON.stringify(spec, null, 2)}
        </pre>
      );
  }
}
