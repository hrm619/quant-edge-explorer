import { QualityFlagMenu } from "./QualityFlagMenu";

// Lazy-load Plotly to avoid blocking initial page load (~1MB bundle)
import Plot from "react-plotly.js";

interface ChartArtifactProps {
  artifactId: string;
  title: string | null;
  spec: Record<string, unknown>;
  qualityFlag: string;
}

export function ChartArtifact({ artifactId, title, spec, qualityFlag }: ChartArtifactProps) {
  const data = (spec.data as Plotly.Data[]) ?? [];
  const layout = (spec.layout as Partial<Plotly.Layout>) ?? {};

  return (
    <div className="my-2 border border-surface-border rounded overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-surface-muted border-b border-surface-border">
        <span className="text-xs font-medium text-neutral-600">
          {title ?? "Chart"}
        </span>
        <QualityFlagMenu artifactId={artifactId} currentFlag={qualityFlag} />
      </div>

      <div className="p-2">
        <Plot
          data={data}
          layout={{
            ...layout,
            autosize: true,
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            margin: { t: 40, r: 20, b: 40, l: 60 },
          }}
          config={{
            responsive: true,
            displayModeBar: false,
          }}
          useResizeHandler
          className="w-full"
          style={{ width: "100%", minHeight: 350 }}
        />
      </div>
    </div>
  );
}
