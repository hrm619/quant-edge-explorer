import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { QualityFlagMenu } from "./QualityFlagMenu";

interface TableArtifactProps {
  artifactId: string;
  title: string | null;
  spec: Record<string, unknown>;
  qualityFlag: string;
}

const PAGE_SIZE = 50;

export function TableArtifact({ artifactId, title, spec, qualityFlag }: TableArtifactProps) {
  const columns = (spec.columns as string[]) ?? [];
  const rows = (spec.rows as Record<string, unknown>[]) ?? [];
  const [sorting, setSorting] = useState<SortingState>([]);
  const [showAll, setShowAll] = useState(rows.length <= PAGE_SIZE);

  const visibleRows = showAll ? rows : rows.slice(0, PAGE_SIZE);

  const columnHelper = createColumnHelper<Record<string, unknown>>();

  const tableColumns = useMemo(
    () =>
      columns.map((col) =>
        columnHelper.accessor((row) => row[col], {
          id: col,
          header: ({ column }) => (
            <button
              className="flex items-center gap-1 hover:text-neutral-900"
              onClick={() => column.toggleSorting()}
            >
              {col}
              <ArrowUpDown className="h-3 w-3" />
            </button>
          ),
          cell: (info) => {
            const val = info.getValue();
            const isNum = typeof val === "number";
            return (
              <span className={cn(isNum && "font-mono text-right tabular-nums")}>
                {val === null || val === undefined
                  ? ""
                  : isNum
                    ? val.toLocaleString()
                    : String(val)}
              </span>
            );
          },
        })
      ),
    [columns, columnHelper]
  );

  const table = useReactTable({
    data: visibleRows,
    columns: tableColumns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  function exportCsv() {
    const header = columns.join(",");
    const csvRows = rows.map((row) =>
      columns.map((col) => {
        const v = row[col];
        const s = v === null || v === undefined ? "" : String(v);
        return s.includes(",") ? `"${s}"` : s;
      }).join(",")
    );
    const csv = [header, ...csvRows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title ?? "table"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="my-2 border border-surface-border rounded overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-surface-muted border-b border-surface-border">
        <span className="text-xs font-medium text-neutral-600">
          {title ?? "Table"} ({spec.row_count as number ?? rows.length} rows)
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={exportCsv}
            className="p-1 rounded hover:bg-neutral-200 text-neutral-500"
            title="Export CSV"
          >
            <Download className="h-3.5 w-3.5" />
          </button>
          <QualityFlagMenu artifactId={artifactId} currentFlag={qualityFlag} />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b border-surface-border bg-white">
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-3 py-1.5 text-left text-xs font-medium text-neutral-500 sticky top-0 bg-white"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-surface-border last:border-0 hover:bg-surface-muted">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-1 text-sm whitespace-nowrap">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!showAll && rows.length > PAGE_SIZE && (
        <button
          onClick={() => setShowAll(true)}
          className="w-full py-1.5 text-xs text-neutral-500 hover:text-neutral-700 hover:bg-surface-muted border-t border-surface-border"
        >
          Show all {rows.length} rows
        </button>
      )}
    </div>
  );
}
