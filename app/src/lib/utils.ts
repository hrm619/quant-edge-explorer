import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import {
  isToday,
  isYesterday,
  isThisWeek,
  differenceInDays,
  formatDistanceToNow,
} from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelativeDate(iso: string): string {
  const date = new Date(iso);
  return formatDistanceToNow(date, { addSuffix: true });
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

type DateBucket =
  | "Today"
  | "Yesterday"
  | "This Week"
  | "Last Week"
  | "Older";

export function groupByDateBucket<T extends { updated_at: string }>(
  items: T[]
): Map<DateBucket, T[]> {
  const groups = new Map<DateBucket, T[]>();

  for (const item of items) {
    const date = new Date(item.updated_at);
    let bucket: DateBucket;

    if (isToday(date)) {
      bucket = "Today";
    } else if (isYesterday(date)) {
      bucket = "Yesterday";
    } else if (isThisWeek(date)) {
      bucket = "This Week";
    } else if (differenceInDays(new Date(), date) <= 14) {
      bucket = "Last Week";
    } else {
      bucket = "Older";
    }

    const existing = groups.get(bucket) ?? [];
    existing.push(item);
    groups.set(bucket, existing);
  }

  return groups;
}

export function toolDisplayName(toolName: string): string {
  switch (toolName) {
    case "query_sql":
      return "SQL Query";
    case "search_knowledge_base":
      return "Knowledge Base Search";
    case "generate_chart":
      return "Chart";
    default:
      return toolName;
  }
}

export function toolSummary(
  toolName: string,
  input: Record<string, unknown>,
  status?: string,
  rowCount?: number
): string {
  if (status === "error") return "Error";
  switch (toolName) {
    case "query_sql":
      return rowCount !== undefined ? `${rowCount} rows` : "Running...";
    case "search_knowledge_base": {
      const q = input.query as string | undefined;
      return q ? `"${q.slice(0, 60)}"` : "Searching...";
    }
    case "generate_chart": {
      const t = input.chart_type as string | undefined;
      return t ?? "Generating...";
    }
    default:
      return "";
  }
}
